from flask import Flask, render_template, request, jsonify, send_from_directory
from main import fetch_and_analyze
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import json
import os
import atexit
import sys

# Determine path to data/config (Frozen vs Source)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
config = Config()

# Basic logging
logging.basicConfig(level=logging.INFO)

# --- Scheduler Setup ---
scheduler = BackgroundScheduler()

def run_scheduled_job():
    app.logger.info("Executing scheduled daily report...")
    try:
        # Run logic. Default to broadcasting to 'default' or all? 
        # Usually daily report goes to all or default.
        fetch_and_analyze(target_robot=None, mode='daily') 
    except Exception as e:
        app.logger.error(f"Scheduled job failed: {e}")

def run_interval_job():
    app.logger.info("Executing scheduled interval check...")
    try:
        fetch_and_analyze(target_robot=None, mode='interval')
    except Exception as e:
        app.logger.error(f"Interval job failed: {e}")

def init_scheduler():
    scheduler_conf = config.get('scheduler', {})
    if scheduler_conf.get('enabled'):
        t = scheduler_conf.get('time', '09:30')
        hour, minute = t.split(':')
        
        # Add Job
        scheduler.add_job(
            run_scheduled_job, 
            'cron', 
            hour=hour, 
            minute=minute, 
            id='daily_report',
            replace_existing=True
        )
        
        # Add Interval Job (every 30 mins)
        scheduler.add_job(
            run_interval_job,
            'interval',
            minutes=30,
            id='interval_check',
            replace_existing=True
        )
        
        if not scheduler.running:
            scheduler.start()
        app.logger.info(f"Scheduler started: Daily at {t}, Interval every 30m")
    else:
        if scheduler.running:
            scheduler.shutdown()
        app.logger.info("Scheduler disabled")

# Initialize on startup
init_scheduler()
atexit.register(lambda: scheduler.shutdown(wait=False))

@app.route('/')
def home():
    robots = config.get('dingtalk.robots', {})
    return render_template('index.html', robots=robots)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/images/<path:filename>')
def serve_image(filename):
    image_dir = os.path.join(BASE_DIR, 'image')
    return send_from_directory(image_dir, filename)

# --- Docs Routes ---
DOCS_DIR = os.path.join(BASE_DIR, 'data', 'docs')
ARCHIVES_INDEX_FILE = os.path.join(DOCS_DIR, '_archives_index.json')

# Ensure docs directory exists
os.makedirs(DOCS_DIR, exist_ok=True)

@app.route('/docs')
def docs_home():
    return render_template('docs.html')

@app.route('/api/docs/<path:doc_name>', methods=['GET'])
def get_doc(doc_name):
    """Get a specific document"""
    try:
        doc_path = os.path.join(DOCS_DIR, f'{doc_name}.json')
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        app.logger.error(f"Doc read error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/archives', methods=['GET', 'POST'])
def handle_archives():
    """Get or update archives index (local docs, external links, credentials)"""
    if request.method == 'GET':
        try:
            # Load archives index
            if os.path.exists(ARCHIVES_INDEX_FILE):
                with open(ARCHIVES_INDEX_FILE, 'r', encoding='utf-8') as f:
                    archives = json.load(f)
            else:
                # Default structure
                archives = {
                    "local_docs": [
                        {"id": "readme", "title": "项目说明", "icon": "📖", "category": "project"},
                        {"id": "architecture", "title": "架构设计", "icon": "🏗️", "category": "project"},
                        {"id": "api-reference", "title": "API 参考", "icon": "🔌", "category": "project"},
                        {"id": "code-style", "title": "代码风格", "icon": "✨", "category": "specs"},
                        {"id": "git-workflow", "title": "Git 工作流", "icon": "🔀", "category": "specs"},
                        {"id": "naming-convention", "title": "命名规范", "icon": "🏷️", "category": "specs"}
                    ],
                    "external_links": [],
                    "credentials": {}
                }
            
            # Load credentials from config (separate for security)
            archives['credentials'] = config.get('archives_credentials', {})
            
            # Add external help docs if configured
            help_docs_path = config.get('help_docs_path')
            if help_docs_path and os.path.exists(help_docs_path):
                archives['help_docs_path'] = help_docs_path
                # Parse index.md to get document structure
                index_path = os.path.join(help_docs_path, 'index.md')
                if os.path.exists(index_path):
                    archives['help_docs_available'] = True
            
            return jsonify(archives)
        except Exception as e:
            app.logger.error(f"Archives read error: {e}")
            return jsonify({'error': str(e)}), 500
    
    if request.method == 'POST':
        try:
            data = request.json
            
            # Separate credentials from archives data
            credentials = data.pop('credentials', None)
            
            # Save archives index (without credentials)
            with open(ARCHIVES_INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Save credentials to config if provided
            if credentials is not None:
                c = config.load()
                c['archives_credentials'] = credentials
                config.save(c)
            
            return jsonify({'success': True})
        except Exception as e:
            app.logger.error(f"Archives save error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

# External Help Docs API
@app.route('/api/help-docs/index')
def get_help_docs_index():
    """Get the help docs index structure from index.md"""
    help_docs_path = config.get('help_docs_path')
    app.logger.info(f"Accessing Help Docs at: {help_docs_path}")
    if not help_docs_path or not os.path.exists(help_docs_path):
        app.logger.error(f"Help docs path missing or invalid: {help_docs_path}")
        return jsonify({'error': 'Help docs path not configured'}), 404
    
    index_path = os.path.join(help_docs_path, 'index.md')
    if not os.path.exists(index_path):
        return jsonify({'error': 'index.md not found'}), 404
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content, 'path': help_docs_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/help-docs/<path:doc_name>')
def get_help_doc(doc_name):
    """Get a specific help document"""
    help_docs_path = config.get('help_docs_path')
    if not help_docs_path or not os.path.exists(help_docs_path):
        return jsonify({'error': 'Help docs path not configured'}), 404
    
    # Security: ensure doc_name doesn't escape the directory
    doc_path = os.path.normpath(os.path.join(help_docs_path, doc_name))
    if not doc_path.startswith(os.path.normpath(help_docs_path)):
        return jsonify({'error': 'Invalid path'}), 403
    
    if not os.path.exists(doc_path):
        return jsonify({'error': 'Document not found'}), 404
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title from first heading
        title = doc_name
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        return jsonify({
            'title': title,
            'content': content,
            'filename': doc_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/help-docs/images/<path:image_name>')
def get_help_doc_image(image_name):
    """Serve images from help docs directory"""
    help_docs_path = config.get('help_docs_path')
    if not help_docs_path:
        return '', 404
    
    images_path = os.path.join(help_docs_path, 'images')
    return send_from_directory(images_path, image_name)

# --- Wiki Routes ---
WIKI_DIR = os.path.join(BASE_DIR, 'data', 'wiki')
WIKI_ASSETS_DIR = os.path.join(WIKI_DIR, 'assets')
ALIASES_FILE = os.path.join(WIKI_DIR, 'group_aliases.json')

# Ensure assets directory exists
os.makedirs(WIKI_ASSETS_DIR, exist_ok=True)

@app.route('/api/wiki/group-aliases', methods=['GET', 'POST'])
def handle_group_aliases():
    """Get or update talent group aliases"""
    if request.method == 'GET':
        if os.path.exists(ALIASES_FILE):
            try:
                with open(ALIASES_FILE, 'r', encoding='utf-8') as f:
                    return jsonify(json.load(f))
            except Exception as e:
                app.logger.error(f"Read aliases error: {e}")
                return jsonify({'error': str(e)}), 500
        return jsonify({})

    if request.method == 'POST':
        try:
            data = request.json
            with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return jsonify({'success': True})
        except Exception as e:
            app.logger.error(f"Save aliases error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wiki-settings', methods=['GET', 'POST'])
def handle_wiki_settings():
    """Get or update wiki display settings (hidden categories etc.)"""
    if request.method == 'GET':
        wiki_settings = config.get('wiki', {})
        return jsonify({
            'hidden_categories': wiki_settings.get('hidden_categories', [])
        })
    
    if request.method == 'POST':
        try:
            data = request.json
            c = config.load()
            wiki_conf = c.get('wiki', {})
            wiki_conf['hidden_categories'] = data.get('hidden_categories', [])
            c['wiki'] = wiki_conf
            config.save(c)
            return jsonify({'success': True})
        except Exception as e:
            app.logger.error(f"Wiki settings save error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wiki')
def wiki_home():
    return render_template('wiki.html')

@app.route('/wiki/<path:page_name>')
def wiki_page(page_name):
    return render_template('wiki.html', page=page_name)

@app.route('/wiki/assets/<path:filename>')
def wiki_asset(filename):
    """Serve wiki asset files"""
    return send_from_directory(WIKI_ASSETS_DIR, filename)

@app.route('/api/wiki/upload', methods=['POST'])
def upload_wiki_image():
    """Upload image for wiki entries"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Validate file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({'success': False, 'message': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400
        
        # Generate unique filename
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        safe_name = f"{timestamp}_{unique_id}.{ext}"
        
        # Save file
        filepath = os.path.join(WIKI_ASSETS_DIR, safe_name)
        file.save(filepath)
        
        # Return the URL path
        url = f"/wiki/assets/{safe_name}"
        return jsonify({'success': True, 'url': url, 'filename': safe_name})
    except Exception as e:
        app.logger.error(f"Wiki image upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/wiki/assets', methods=['GET'])
def list_wiki_assets():
    """List all wiki asset files"""
    try:
        if not os.path.exists(WIKI_ASSETS_DIR):
            return jsonify({'assets': []})
        
        files = []
        for f in os.listdir(WIKI_ASSETS_DIR):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                path = os.path.join(WIKI_ASSETS_DIR, f)
                stats = os.stat(path)
                files.append({
                    'filename': f,
                    'url': f'/wiki/assets/{f}',
                    'updated_at': stats.st_mtime
                })
        
        # Sort by updated_at desc
        files.sort(key=lambda x: x['updated_at'], reverse=True)
        return jsonify({'assets': files})
    except Exception as e:
        app.logger.error(f"List assets error: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/wiki', methods=['GET'])
def get_wiki_index():
    """Get wiki index and all page metadata"""
    try:
        index_path = os.path.join(WIKI_DIR, '_index.json')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"categories": [], "featured": [], "recent_updates": []}
        
        # Load all page data including type
        pages = {}
        for filename in os.listdir(WIKI_DIR):
            if filename.endswith('.json') and not filename.startswith('_'):
                page_id = filename[:-5]
                page_path = os.path.join(WIKI_DIR, filename)
                try:
                    with open(page_path, 'r', encoding='utf-8') as f:
                        page_data = json.load(f)
                    pages[page_id] = {
                        'title': page_data.get('title', page_id),
                        'type': page_data.get('type', ''),
                        'category': page_data.get('category', ''),
                        'updated_at': page_data.get('updated_at', ''),
                        'tags': page_data.get('tags', []),
                        'subtitle': page_data.get('subtitle', ''),
                        'icon': page_data.get('icon', ''),
                        'talent_meta': page_data.get('talent_meta', {}),
                        'infobox': page_data.get('infobox', {})
                    }
                except:
                    pass
        
        return jsonify({'index': index, 'pages': pages})
    except Exception as e:
        app.logger.error(f"Wiki index error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wiki/_schema', methods=['GET'])
def get_wiki_schema():
    """Get wiki entry type schema"""
    try:
        schema_path = os.path.join(WIKI_DIR, '_schema.json')
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Schema not found'}), 404
    except Exception as e:
        app.logger.error(f"Schema read error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wiki/<path:page_name>', methods=['GET'])
def get_wiki_page(page_name):
    """Get a specific wiki page"""
    try:
        page_path = os.path.join(WIKI_DIR, f'{page_name}.json')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Page not found'}), 404
    except Exception as e:
        app.logger.error(f"Wiki page read error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wiki/<path:page_name>', methods=['POST'])
def save_wiki_page(page_name):
    """Save/update a wiki page"""
    try:
        data = request.json
        from datetime import datetime
        
        page_path = os.path.join(WIKI_DIR, f'{page_name}.json')
        
        # Load existing or create new
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                page_data = json.load(f)
            page_data['updated_at'] = datetime.now().isoformat()
        else:
            page_data = {
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        
        # Update all fields from request
        page_data['title'] = data.get('title', page_name)
        page_data['type'] = data.get('type', '')
        page_data['subtitle'] = data.get('subtitle', '')
        page_data['icon'] = data.get('icon', '')
        page_data['tags'] = data.get('tags', [])
        page_data['infobox'] = data.get('infobox', {})
        page_data['sections'] = data.get('sections', {})
        
        # Legacy content field (for compatibility)
        if 'content' in data:
            page_data['content'] = data.get('content', '')
        
        # New fields for images and related entries
        page_data['cover_image'] = data.get('cover_image', '')
        page_data['images'] = data.get('images', [])
        page_data['related'] = data.get('related', [])
        
        # Save page
        with open(page_path, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        
        # Update index based on type
        update_wiki_index(page_name, page_data.get('type', ''))
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Wiki page save error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/wiki/<path:page_name>', methods=['DELETE'])
def delete_wiki_page(page_name):
    """Delete a wiki page"""
    try:
        page_path = os.path.join(WIKI_DIR, f'{page_name}.json')
        if os.path.exists(page_path):
            os.remove(page_path)
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Page not found'}), 404
    except Exception as e:
        app.logger.error(f"Wiki page delete error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/wiki/verify', methods=['POST'])
def verify_wiki_token():
    """Verify edit token"""
    data = request.json
    required_token = config.get('web_token')
    provided_token = data.get('token', '')
    
    if str(provided_token) == str(required_token):
        return jsonify({'success': True})
    return jsonify({'success': False})

def update_wiki_index(page_name, entry_type):
    """Update the wiki index with a new/updated page, organized by type"""
    try:
        index_path = os.path.join(WIKI_DIR, '_index.json')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"categories": [], "featured": [], "recent_updates": []}
        
        # Type to category mapping
        type_categories = {
            'monster': {'name': '怪物图鉴', 'icon': '👹'},
            'item': {'name': '道具遗物', 'icon': '🗡️'},
            'character': {'name': '角色介绍', 'icon': '👤'},
            'lore': {'name': '世界设定', 'icon': '🌊'}
        }
        
        cat_info = type_categories.get(entry_type, {'name': '其他', 'icon': '📁'})
        category_name = cat_info['name']
        
        # Remove page from all categories first
        for cat in index.get('categories', []):
            if page_name in cat.get('pages', []):
                cat['pages'].remove(page_name)
        
        # Add to the correct category
        cat_found = False
        for cat in index.get('categories', []):
            if cat.get('name') == category_name:
                if page_name not in cat.get('pages', []):
                    cat['pages'].append(page_name)
                cat_found = True
                break
        
        if not cat_found and entry_type:
            index['categories'].append({
                'name': category_name,
                'icon': cat_info['icon'],
                'pages': [page_name]
            })
        
        # Update recent
        recent = index.get('recent_updates', [])
        if page_name in recent:
            recent.remove(page_name)
        recent.insert(0, page_name)
        index['recent_updates'] = recent[:10]
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception as e:
        app.logger.error(f"Wiki index update error: {e}")

@app.route('/api/summary')
def get_summary():
    summary_path = config.get('output.summary_file', './data/summary.json')
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['user_roles'] = config.get('user_roles', {})
            data['user_mobiles'] = config.get('user_mobiles', {})
            data['teams'] = config.get('teams', {})
            return jsonify(data)
        except Exception as e:
             app.logger.error(f"Error reading summary: {e}")
             return jsonify({'error': 'Failed to read data'}), 500
    else:
        return jsonify({'error': 'No data available. Please run report first.'}), 404

@app.route('/api/update', methods=['POST'])
def update_data():
    try:
        fetch_and_analyze(send_to_dingtalk=False)
        return jsonify({'status': 'success', 'message': 'Data updated successfully'})
    except Exception as e:
        app.logger.error(f"Update failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/schedule', methods=['GET', 'POST'])
def handle_schedule():
    if request.method == 'GET':
        return jsonify(config.get('scheduler', {}))
    
    if request.method == 'POST':
        data = request.json
        c = config.load() # Reload to be safe
        c['scheduler'] = {
            'enabled': data.get('enabled', False),
            'mode': 'daily',
            'time': data.get('time', '09:30')
        }
        config.save(c)
        # Re-init scheduler
        init_scheduler()
        return jsonify({'success': True})
    
@app.route('/api/switches', methods=['GET', 'POST'])
def handle_switches():
    if request.method == 'GET':
        dingtalk_switches = config.get('dingtalk.switches', {
            "daily_summary": True,
            "daily_anomaly": True,
            "daily_diff": True,
            "interval_alert": True
        })
        return jsonify(dingtalk_switches)
    
    if request.method == 'POST':
        data = request.json
        c = config.load()
        dt_conf = c.get('dingtalk', {})
        
        # Merge existing with new data
        current_switches = dt_conf.get('switches', {})
        current_switches.update(data)
        dt_conf['switches'] = current_switches
        
        c['dingtalk'] = dt_conf
        config.save(c)
        return jsonify({'success': True})

@app.route('/api/parse_curl', methods=['POST'])
def parse_curl():
    data = request.json
    curl_cmd = data.get('curl', '')
    if not curl_cmd:
        return jsonify({'success': False, 'message': 'Empty command'}), 400
    
    try:
        import re
        from urllib.parse import unquote

        # 1. Parse Cookies
        # Pattern: -H 'Cookie: ...' or -H "cookie: ..."
        # We need to be careful with quotes.
        cookie_pattern = re.compile(r"[-|--]H\s+['\"](?:C|c)ookie:\s+(.*?)['\"]")
        cookie_match = cookie_pattern.search(curl_cmd)
        
        new_cookies = {}
        if cookie_match:
            raw_cookies = cookie_match.group(1)
            # Split by ;
            for part in raw_cookies.split(';'):
                if '=' in part:
                    k, v = part.strip().split('=', 1)
                    new_cookies[k] = v
        else:
             # Try --cookie "..."
             cookie_pattern_2 = re.compile(r"--cookie\s+['\"](.*?)['\"]")
             match_2 = cookie_pattern_2.search(curl_cmd)
             if match_2:
                raw_cookies = match_2.group(1)
                for part in raw_cookies.split(';'):
                    if '=' in part:
                        k, v = part.strip().split('=', 1)
                        new_cookies[k] = v

        # 2. Parse Project ID (from URL)
        # Pattern: project/68e.../task
        project_pattern = re.compile(r"project/([a-zA-Z0-9]+)/task")
        project_match = project_pattern.search(curl_cmd)
        
        c = config.load()
        tb_conf = c.get('teambition', {})
        
        if project_match:
            tb_conf['project_id'] = project_match.group(1)
            # Also update API URL base if needed, but usually we just keep the base and swap ID?
            # Config has full URL: "https://.../api/project/<ID>/task/export"
            # Let's reconstruct it to be safe or parse the full URL from curl?
            # Regex for full URL
            url_pattern = re.compile(r"['\"](https?://.*?)['\"]")
            url_match = url_pattern.search(curl_cmd)
            if url_match:
                 tb_conf['api_url'] = url_match.group(1)

        if new_cookies:
            # Merge or Replace? Replaces old cookies to be safe (expired)
            # But preserve non-cookie keys if any? No, usually replace.
            tb_conf['cookies'] = new_cookies
            
        c['teambition'] = tb_conf
        config.save(c)
        
        return jsonify({
            'success': True, 
            'message': f"Config Updated! Project: {tb_conf.get('project_id')}, Cookies: {len(new_cookies)}"
        })

    except Exception as e:
        app.logger.error(f"Curl parse failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/run', methods=['POST'])
def run_report():
    data = request.get_json() or {}
    
    required_token = config.get('web_token')
    if required_token:
        provided_token = data.get('token')
        if str(provided_token) != str(required_token):
             return jsonify({'success': False, 'message': 'Verification code incorrect'}), 403

    robot = data.get('robot')
    
    app.logger.info(f"Received request to run report for robot: {robot}")
    
    try:
        result = fetch_and_analyze(target_robot=robot)
        
        if result:
            return jsonify({'success': True, 'message': 'Report executed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to generate report'}), 500
            
    except Exception as e:
        app.logger.error(f"Error executing report: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()

    port = args.port
    print(f"Starting Web Interface on http://localhost:{port}")
    
    # Ensure asset dirs exist to prevent 404s on empty dirs
    os.makedirs(WIKI_ASSETS_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'static', 'css'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'static', 'js'), exist_ok=True)
    
    app.run(host='0.0.0.0', port=port)
