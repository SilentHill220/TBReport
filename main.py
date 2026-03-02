import sys
import os
import argparse

# Fix Windows console encoding for Unicode (e.g. emoji in task titles)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from config import Config
from teambition_api import TeambitionAPI
from task_analyzer import TaskAnalyzer
from scheduler import TaskScheduler
from dingtalk_sender import DingTalkSender, ImgBBUploader
from task_manager import TaskManager

# Try to import table renderer (uses matplotlib, no external dependencies)
try:
    from table_renderer import TableImageRenderer
    HAS_TABLE_RENDERER = True
    print("[Info] table_renderer loaded successfully (matplotlib mode)")
except ImportError as e:
    HAS_TABLE_RENDERER = False
    print(f"[Warning] table_renderer not available: {e}. Will use markdown text instead.")

def fetch_and_analyze(target_robot=None, send_to_dingtalk=True, mode='daily'):
    config = Config()
    api = TeambitionAPI(config)
    analyzer = TaskAnalyzer(config)
    task_manager = TaskManager(config.get('output.state_file', './data/task_state.json'))

    print(f"\n{'='*60}")
    print(f"开始获取 Teambition 任务数据 - {config.get('teambition.project_id')}")
    print(f"{'='*60}\n")

    csv_content = api.fetch_tasks()
    
    if csv_content:
        csv_path = api.save_csv(csv_content)
        if csv_path:
            df = analyzer.load_csv(csv_path)
            if not df.empty:
                # Fetch activities to credit users for reassigned tasks
                # We only care about tasks that are NOT in "To Do" state (i.e. have been worked on)
                # Filter for tasks that are "Done" or "In Progress" or "Testing"
                # To be safe and simple, we fetch for all tasks that have an ID.
                # Find ID column first
                id_col = next((c for c in ['任务 ObjectId', '_id', 'id', 'taskId', '任务ID'] if c in df.columns), None)
                activities = []
                
                if id_col:
                    task_ids = df[id_col].dropna().astype(str).tolist()
                    # Filter out empty strings
                    task_ids = [t for t in task_ids if t and t != 'nan']
                    
                    if len(task_ids) > 0:
                        print(f"准备获取 {len(task_ids)} 个任务的动态以校准贡献统计...")
                        try:
                            activities = api.fetch_tasks_activities(task_ids)
                        except Exception as e:
                            print(f"[Warning] 获取任务动态失败: {e}")
                
                summary = analyzer.analyze_tasks(df, activities)
                analyzer.save_summary(summary)
                analyzer.print_summary(summary)
                
                # State Tracking & Diffing
                current_tasks_dict = analyzer.get_task_dict(df)
                old_state = task_manager.load_state()
                prev_tasks = old_state.get('tasks', {})
                
                changes = task_manager.detect_changes(prev_tasks, current_tasks_dict)
                if changes:
                    print("\n[变动检测] 发现以下变动:")
                    for c in changes:
                        print(f"  - {c}")
                else:
                    print("\n[变动检测] 无变动")
                
                # Save new state
                task_manager.save_state(current_tasks_dict)
                
                # Cleanup CSV
                if csv_path and os.path.exists(csv_path):
                    try:
                        os.remove(csv_path)
                        print(f"\n[清理] 已删除 CSV 文件: {csv_path}")
                    except Exception as e:
                        print(f"\n[清理] 删除文件失败: {e}")

                # Send DingTalk Notification
                dingtalk_config = config.get('dingtalk', {})
                if dingtalk_config.get('enabled') and send_to_dingtalk:
                    print("\n正在发送钉钉通知...")
                    
                    dingtalk_switches = dingtalk_config.get('switches', {})
                    user_roles = config.get('user_roles', {})
                    user_mobiles = config.get('user_mobiles', {})
                    
                    # Support multiple robots
                    robots = dingtalk_config.get('robots', {})
                    # Backward compatibility or direct webhook
                    if not robots and dingtalk_config.get('webhook'):
                        robots = {
                            'default': {
                                'webhook': dingtalk_config.get('webhook'),
                                'secret': dingtalk_config.get('secret')
                            }
                        }
                    
                    if not robots:
                        print("未配置 DingTalk 机器人")
                    else:
                        # Prepare report content once
                        temp_sender = DingTalkSender("") # Helper to format
                        # format_task_report now returns (report_content, at_mobiles_list)
                        dashboard_url = config.get('dashboard_url')
                        
                        if mode == 'interval':
                            # In interval mode, we only check for parallel tasks and alert independently
                            # We do NOT send the full report
                            
                            if not dingtalk_switches.get('interval_alert', True):
                                print("Interval Alert disabled by switch.")
                                return True

                            print("Running in Interval Mode: Checking for parallel tasks...")
                            for name, bot_cfg in robots.items():
                                if target_robot and name != target_robot: continue
                                
                                webhook = bot_cfg.get('webhook')
                                secret = bot_cfg.get('secret')
                                if not webhook: continue
                                
                                sender = DingTalkSender(webhook)
                                sent = sender.send_parallel_task_alert(
                                    summary, user_roles, user_mobiles, secret=secret
                                )
                                if sent:
                                    print(f"Parallel Task Alert sent to {name}")
                                else:
                                    print("No parallel tasks detected or alert not needed.")
                        else:
                            # Daily / Full Mode
                            
                            # Try to render as image first
                            image_url = None
                            task_list = []
                            imgbb_key = config.get('imgbb.api_key')
                            
                            if HAS_TABLE_RENDERER and imgbb_key:
                                print("[图片模式] 正在生成报表图片...")
                                try:
                                    renderer = TableImageRenderer(config.get('output.csv_dir', './data'))
                                    image_path, task_list = renderer.render_task_report(
                                        summary, 
                                        user_roles, 
                                        dashboard_url=dashboard_url,
                                        switches=dingtalk_switches
                                    )
                                    
                                    if image_path:
                                        print(f"[图片模式] 上传到 ImgBB...")
                                        uploader = ImgBBUploader(imgbb_key)
                                        image_url = uploader.upload_image(image_path)
                                        
                                        if image_url:
                                            print(f"[图片模式] 上传成功: {image_url}")
                                        else:
                                            print("[图片模式] 上传失败，回退到 Markdown 模式")
                                    else:
                                        print("[图片模式] 渲染失败，回退到 Markdown 模式")
                                except Exception as e:
                                    print(f"[图片模式] 错误: {e}，回退到 Markdown 模式")
                            else:
                                if not HAS_TABLE_RENDERER:
                                    print("[通知] 未安装 imgkit，使用 Markdown 模式")
                                if not imgbb_key:
                                    print("[通知] 未配置 ImgBB API Key，使用 Markdown 模式")
                            
                            # Prepare markdown report as fallback or for text content
                            report, at_mobiles_list = temp_sender.format_task_report(
                                summary, 
                                user_roles, 
                                user_mobiles, 
                                dashboard_url=dashboard_url,
                                switches=dingtalk_switches
                            )
                            
                            # Only add diff if enabled
                            if dingtalk_switches.get('daily_diff', True):
                                final_report = temp_sender.format_diff_report(changes, report)
                            else:
                                final_report = report
                            
                            for name, bot_cfg in robots.items():
                                # Filter by target_robot if specified
                                if target_robot and name != target_robot:
                                    continue
                                    
                                webhook = bot_cfg.get('webhook')
                                secret = bot_cfg.get('secret')
                                if not webhook:
                                    continue
                                    
                                print(f"Sending to robot: {name}")
                                sender = DingTalkSender(webhook)
                                
                                # Send image if available, otherwise markdown
                                if image_url:
                                    # RPG Style summary from DingTalkSender
                                    rpg_summary = temp_sender.get_rpg_summary(summary)
                                    
                                    # Construction of the RPG Battle Report
                                    brief_text = f"{rpg_summary}\n\n"
                                    brief_text += f"![任务报表]({image_url})\n\n"
                                    
                                    # Add task jump buttons (just numbers)
                                    if task_list:
                                        brief_text += "**🔗 快速跳转:**\n"
                                        buttons = []
                                        # Use target task list or summary's recent wins as fallback? 
                                        # renderer provides task_list which matches the image.
                                        for i, task in enumerate(task_list[:20], 1): 
                                            task_id = task.get('task_id')
                                            if task_id:
                                                task_url = f"https://www.teambition.com/task/{task_id}"
                                                buttons.append(f"[[{i:02}]]({task_url})")
                                        
                                        for j in range(0, len(buttons), 5):
                                            brief_text += " ".join(buttons[j:j+5]) + "\n"
                                        brief_text += "\n"
                                    
                                    if dashboard_url:
                                        brief_text += f"👉 [**进入指挥部(看板)查看全局态势**]({dashboard_url})\n"
                                    
                                    # Add anomaly alerts if any
                                    if dingtalk_switches.get('daily_anomaly', True):
                                        alert_text, alert_mobiles = temp_sender.generate_anomaly_alerts(
                                            summary, user_roles, user_mobiles
                                        )
                                        if alert_text:
                                            brief_text += "\n---\n" + alert_text
                                            at_mobiles_list.extend(alert_mobiles)
                                    
                                    sender.send_markdown(f"⚔️ 工作室今日战报 | {summary.get('updated_at', '').split('T')[0]}", brief_text, secret=secret, at_mobiles=at_mobiles_list)
                                else:
                                    # Fallback to full markdown report
                                    sender.send_markdown("Teambition 任务日报", final_report, secret=secret, at_mobiles=at_mobiles_list)
                    
                return True
                    
                return True
    
    print("获取或分析任务数据失败")
    return False

def main():
    parser = argparse.ArgumentParser(description='Teambition 任务数据获取和汇总工具')
    parser.add_argument('--once', action='store_true', help='只执行一次，不启动定时任务')
    parser.add_argument('--interval', type=int, default=30, help='定时任务间隔（分钟），默认30分钟')
    parser.add_argument('--config', type=str, default='config.json', help='配置文件路径')
    parser.add_argument('--robot', type=str, help='指定发送的机器人名称 (如 test 或 default)')
    
    args = parser.parse_args()

    config = Config(args.config)
    scheduler_config = config.get_scheduler_config()

    if args.once or not scheduler_config.get('enabled', False):
        fetch_and_analyze(args.robot)
    else:
        scheduler = TaskScheduler(config)
        
        interval = args.interval if args.interval != 30 else scheduler_config.get('interval_minutes', 30)
        scheduler.schedule_task(fetch_and_analyze, interval)
        
        scheduler.start()

if __name__ == '__main__':
    main()
