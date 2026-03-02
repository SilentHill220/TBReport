import requests
import json
import hmac
import hashlib
import base64
import urllib.parse
import time
import os
from typing import Dict, Any, List, Optional, Tuple


class ImgBBUploader:
    """Upload images to ImgBB and get public URLs for DingTalk messages."""
    
    API_URL = "https://api.imgbb.com/1/upload"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def upload_image(self, image_path: str, name: str = None) -> Optional[str]:
        """
        Upload an image file to ImgBB.
        :param image_path: Local path to the image file
        :param name: Optional name for the image
        :return: Public URL of the uploaded image, or None if failed
        """
        if not self.api_key:
            print("ImgBB API key not configured")
            return None
        
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return None
        
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                'key': self.api_key,
                'image': image_data,
            }
            if name:
                payload['name'] = name
            
            response = requests.post(self.API_URL, data=payload)
            result = response.json()
            
            if result.get('success'):
                url = result['data']['url']
                print(f"ImgBB upload success: {url}")
                return url
            else:
                print(f"ImgBB upload failed: {result.get('error', {}).get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"ImgBB upload error: {e}")
            return None
    
    def upload_base64(self, base64_data: str, name: str = None) -> Optional[str]:
        """
        Upload a base64-encoded image to ImgBB.
        :param base64_data: Base64-encoded image data
        :param name: Optional name for the image
        :return: Public URL of the uploaded image, or None if failed
        """
        if not self.api_key:
            print("ImgBB API key not configured")
            return None
        
        try:
            payload = {
                'key': self.api_key,
                'image': base64_data,
            }
            if name:
                payload['name'] = name
            
            response = requests.post(self.API_URL, data=payload)
            result = response.json()
            
            if result.get('success'):
                url = result['data']['url']
                print(f"ImgBB upload success: {url}")
                return url
            else:
                print(f"ImgBB upload failed: {result.get('error', {}).get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"ImgBB upload error: {e}")
            return None

class DingTalkSender:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.webhook = webhook_url # Renamed from webhook_url to webhook

    def get_sign(self, secret: str):
        if not secret:
            return None, None
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def send_markdown(
        self, 
        title: str, 
        text: str, 
        is_at_all: bool = False, 
        at_mobiles: list = None,
        secret: str = None
    ) -> Optional[Dict]:
        """
        Send a markdown message to DingTalk.
        :param at_mobiles: List of mobile numbers to mention
        """
        if not self.webhook:
            print("DingTalk webhook not configured")
            return None
            
        timestamp, sign = self.get_sign(secret)
        
        url = f"{self.webhook}&timestamp={timestamp}&sign={sign}" if sign else self.webhook
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            },
            "at": {
                "atMobiles": at_mobiles if at_mobiles else [],
                "isAtAll": is_at_all
            }
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers)
            print(f"DingTalk Response: {resp.text}")
            return resp.json()
        except Exception as e:
            print(f"Failed to send DingTalk message: {e}")
            return None

    def send_image_link(
        self,
        title: str,
        image_url: str,
        message_url: str = "",
        secret: str = None
    ) -> Optional[Dict]:
        """
        Send an image as a link card message to DingTalk.
        Note: DingTalk doesn't support pure image messages via webhook,
        so we use ActionCard format to display images.
        :param title: Title of the message
        :param image_url: Public URL of the image (e.g., from ImgBB)
        :param message_url: Optional click URL
        """
        if not self.webhook:
            print("DingTalk webhook not configured")
            return None
        
        timestamp, sign = self.get_sign(secret)
        url = f"{self.webhook}&timestamp={timestamp}&sign={sign}" if sign else self.webhook
        
        headers = {'Content-Type': 'application/json'}
        
        # Use markdown format with image
        markdown_text = f"![{title}]({image_url})"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text
            }
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers)
            print(f"DingTalk Image Response: {resp.text}")
            return resp.json()
        except Exception as e:
            print(f"Failed to send DingTalk image: {e}")
            return None

    def send_markdown_with_image(
        self,
        title: str,
        text: str,
        image_url: str,
        is_at_all: bool = False,
        at_mobiles: list = None,
        secret: str = None
    ) -> Optional[Dict]:
        """
        Send a markdown message with an embedded image to DingTalk.
        :param title: Message title
        :param text: Markdown text content
        :param image_url: Public URL of the image to embed
        :param at_mobiles: List of mobile numbers to mention
        """
        if not self.webhook:
            print("DingTalk webhook not configured")
            return None
        
        # Append image to markdown text
        text_with_image = f"{text}\n\n![图片]({image_url})"
        
        return self.send_markdown(
            title=title,
            text=text_with_image,
            is_at_all=is_at_all,
            at_mobiles=at_mobiles,
            secret=secret
        )

    def format_task_report(self, summary: Dict, user_roles: Dict[str, str] = None, user_mobiles: Dict[str, str] = None, dashboard_url: str = None, switches: Dict[str, bool] = None) -> Tuple[str, List[str]]:
        """
        Format task summary into Markdown table for DingTalk.
        Splits into "Urgent" and "Normal" tables.
        Include 'Role' column mapped from user_roles.
        Returns: (Markdown Report, List of mobile numbers to mention)
        """
        if not user_roles: user_roles = {}
        if not user_mobiles: user_mobiles = {}
        if not switches: switches = {}

        report_lines = []
        updated_at = summary.get('updated_at', '').split('T')[0]
        report_lines.append(f"## ⚔️ 工作室战报 ({updated_at})")
        
        # 1. Summary Tables (Urgent / Dev / Design)
        if switches.get('daily_summary', True):
            if dashboard_url:
                report_lines.append(f"\n> 🏰 [**进入英雄殿堂查看实时战绩**]({dashboard_url})\n")
        
            urgent_data = []
            dev_data = []     
            design_data = []  

            total_tasks = summary.get('total_tasks', 0)
            report_lines.append(f"📜 **今日战线总览**: 共有 {total_tasks} 项任务在推进中\n---")
            
            by_user = summary.get('by_user', {})
            for user, user_data in by_user.items():
                tasks = user_data.get('tasks', [])
                role = user_roles.get(user, '冒险者') 
                user_stats = user_data.get('stats', {})
                done_count = user_stats.get('done_count', 0)
                level = int((done_count * 10)**0.5) + 1
                
                # Simple Title mapping for DingTalk to match JS engine roughly
                hero_title = "见习英雄"
                if done_count > 20: hero_title = "任务收割者"
                elif done_count > 10: hero_title = "交付大师"
                elif user_stats.get('bug_done', 0) > 5: hero_title = "灭虫专家"
                elif user_stats.get('urgent_done', 0) > 2: hero_title = "消防先锋"

                user_tag = f"**{user}** (LV.{level} {hero_title})"

                for t in tasks:
                    status = t['status']
                    priority = t.get('priority', '')
                    
                    # Check attributes
                    is_urgent = any(p in priority for p in ['紧急', '非常紧急', 'Urgent', 'High'])
                    is_done = any(s in status for s in ['已完成', '已发布', 'Released', 'Done', '验收中', '待验收', '测完'])
                    
                    # Row content preparation
                    t_id = t.get('id')
                    base_url = "https://www.teambition.com/task/"
                    title_text = t['title'].replace('|', '\|')
                    if len(title_text) > 20: title_text = title_text[:20] + "..."
                    
                    title = f"[{title_text}]({base_url}{t_id})" if t_id else title_text
                    due = t['due'][:10] if t['due'] else '-'
                    
                    # Filter Logic
                    target_list = None
                    display_status = status
                    
                    if is_urgent and not is_done:
                        display_status = f"🔥 {status}"
                        target_list = urgent_data
                    elif not is_done:
                        if role in ['客户端', '服务端']: target_list = dev_data
                        else: target_list = design_data
                    
                    if target_list is not None:
                         target_list.append({
                             'role': role,
                             'user': user,
                             'tag': user_tag,
                             'row': f"| {user_tag} | {title} | {display_status} | {due} |"
                         })

            # Assemble Report
            if not urgent_data and not dev_data and not design_data:
                 report_lines.append("\n☀️ **今日风平浪静，英雄们正在整装待发。**")
            else:
                # Urgent Table
                if urgent_data:
                    report_lines.append("### 🔴 紧急突围任务")
                    report_lines.append("| 英雄单位 | 战事说明 | 当前态势 | 期限 |")
                    report_lines.append("| :--- | :--- | :--- | :--- |")
                    for item in urgent_data: report_lines.append(item['row'])
                    report_lines.append("\n")

                # Main Forces
                if dev_data:
                    report_lines.append("### ⚔️ 主力攻坚部队 (程序)")
                    report_lines.append("| 英雄单位 | 战事说明 | 当前态势 | 期限 |")
                    report_lines.append("| :--- | :--- | :--- | :--- |")
                    for item in dev_data: report_lines.append(item['row'])
                    report_lines.append("\n")

                if design_data:
                    report_lines.append("### 🛡️ 协同支撑编队 (策划/美术)")
                    report_lines.append("| 英雄单位 | 战事说明 | 当前态势 | 期限 |")
                    report_lines.append("| :--- | :--- | :--- | :--- |")
                    for item in design_data: report_lines.append(item['row'])
            
            report_content = "\n".join(report_lines)
        else:
            # If summary is disabled
            report_content = f"### Teambition 任务日报 ({updated_at})"

        # 2. Anomaly Alerts (Idle + Parallel)
        alert_text = ""
        at_mobiles_anomaly = []
        if switches.get('daily_anomaly', True):
            alert_text, at_mobiles_anomaly = self.generate_anomaly_alerts(summary, user_roles, user_mobiles)
        
        final_report = report_content + alert_text
        
        # Merge at_mobiles from both parts (currently report_content doesn't produce @mobs, only anomaly does)
        # But if we had logic in summary to @, we would merge here.
        
        return final_report, at_mobiles_anomaly

    def get_rpg_summary(self, summary: Dict) -> str:
        """Generate a punchy RPG-style summary text for DingTalk alerts."""
        updated_at = summary.get('updated_at', '').split('T')[0]
        total_tasks = summary.get('total_tasks', 0)
        
        # Calculate daily wins (only those completed on the same date)
        recent_wins = summary.get('recent_wins', [])
        daily_wins_list = [w for w in recent_wins if str(w.get('done_at', '')).startswith(updated_at)]
        daily_wins = len(daily_wins_list)
        total_recent = len(recent_wins)

        if daily_wins > 0:
            win_text = f"英雄们势如破竹！今日共斩获 **{daily_wins}** 项战果。"
        else:
            win_text = f"今日暂无新战果，英雄们正在积蓄力量 (近期共斩获 {total_recent} 项战果)。"

        lines = [
            f"## ⚔️ 工作室战报 | {updated_at}",
            f"> 📢 **重点战况**: {win_text}",
            f"\n📜 当前全线共有 {total_tasks} 个战点正在推进中...",
            "\n---"
        ]
        return "\n".join(lines)

    def generate_anomaly_alerts(self, summary: Dict, user_roles: Dict, user_mobiles: Dict) -> Tuple[str, List[str]]:
        """
        Check for Task Planning Anomalies for CLIENT developers:
        1. Idle (0 active tasks)
        2. Overloaded (>1 active tasks)
        
        Returns: (Alert Markdown Text, List of mobiles to @)
        """
        alert_lines = []
        at_mobiles = []
        
        # Define Leads
        lead_client = "庄鹏程"
        
        # Identify Client Devs only
        client_devs = [u for u, r in user_roles.items() if r == '客户端']
        
        # Helper to format mention
        def mention(name):
            mobile = user_mobiles.get(name, "")
            if mobile:
                at_mobiles.append(mobile)
                return f"@{mobile}"
            return f"@{name}"

        for dev in client_devs:
            if dev == lead_client: continue # Skip lead self-check

            user_data = summary.get('by_user', {}).get(dev, {})
            tasks = user_data.get('tasks', [])
            active_tasks = [t for t in tasks if t['status'] in ['进行中', 'In Progress', 'Doing']]
            count = len(active_tasks)
            
            if count == 0:
                # Idle
                msg = f"🌟 **{dev}** 暂无“进行中”的任务，记得维护 Teambition 状态哦 ~\n如有空闲请与 {mention(lead_client)} 同步后续安排。"
                alert_lines.append(msg)
            elif count > 1:
                # Overloaded / Parallel
                task_titles = [t['title'][:10]+"..." if len(t['title'])>10 else t['title'] for t in active_tasks]
                
                msg = f"💪 **{dev}** 当前有 {count} 个任务并行 ({', '.join(task_titles)})，项目组必须注意合理规划，\n请及时联系 {mention(lead_client)}处理。"
                alert_lines.append(msg)
                
        if alert_lines:
            return "\n\n### 🚫 任务规划异常提醒\n" + "\n\n".join(alert_lines), at_mobiles
        return "", []

    def format_diff_report(self, changes: List[str], summary_report: str) -> str:
        """
        Combine standard summary report with diff report
        """
        if not changes:
            return summary_report
            
        # Check explicit switch if we pass it here? 
        # For now, the caller controls this by checking the switch before calling or we add an arg.
        # But 'main.py' logic will control whether to add it.
        # Let's keep this as purely formatting.

            
        diff_section = ["\n### 📢 最近变动"]
        for change in changes:
            diff_section.append(f"- {change}")
            
        return "\n".join(diff_section) + "\n\n" + summary_report

    def send_parallel_task_alert(self, summary: Dict, user_roles: Dict, user_mobiles: Dict, secret: str = None) -> bool:
        """
        Check for users with >1 'In Progress' tasks and send an alert if found.
        Returns True if an alert was sent, False otherwise.
        """
        if not self.webhook:
            return False

        alert_lines = []
        at_mobiles_list = []

        # Helper to format mention
        def mention(name):
            mobile = user_mobiles.get(name, "")
            if mobile:
                at_mobiles_list.append(mobile)
                return f"@{mobile}"
            return f"@{name}"

        by_user = summary.get('by_user', {})
        
        for user_name, user_data in by_user.items():
            tasks = user_data.get('tasks', [])
            
            # Filter active tasks
            active_tasks = [t for t in tasks if t['status'] in ['进行中', 'In Progress', 'Doing']]
            
            # active_tasks > 1 AND Role is '客户端'
            role = user_roles.get(user_name, '')
            if len(active_tasks) > 1 and role == '客户端':
                # Found a user with multiple parallel tasks
                lines = [f"⚠️ **{user_name}** 有 {len(active_tasks)} 个并行任务:"]
                for t in active_tasks:
                    title = t['title']
                    if len(title) > 15: title = title[:15] + "..."
                    lines.append(f"- {title}")
                
                lines.append(f"请 {mention(user_name)} 确认进度。")
                alert_lines.append("\n".join(lines))

        if not alert_lines:
            return False

        # Send the alert
        title = "Teambition 任务规划异常提醒"
        text = "### 🚫 任务规划异常提醒 (并行任务)\n\n" + "\n\n---\n\n".join(alert_lines)
        
        # Deduplicate mobiles
        at_mobiles_list = list(set(at_mobiles_list))
        
        self.send_markdown(title, text, secret=secret, at_mobiles=at_mobiles_list)
        return True
