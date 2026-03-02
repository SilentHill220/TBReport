import requests
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import Config

class TeambitionAPI:
    def __init__(self, config: Config):
        self.config = config
        self.api_url = config.get('teambition.api_url')
        self.cookies = config.get('teambition.cookies', {})
        self.export_config = config.get_export_config()





    def fetch_tasks_activities(self, task_ids: List[str], max_workers: int = 20) -> List[Dict]:
        """
        Fetch activities for specific tasks in parallel.
        Returns flattened list of all activities.
        """
        import concurrent.futures
        
        all_activities = []
        if not task_ids:
            return []
            
        print(f"正在获取 {len(task_ids)} 个任务的动态 (并发数 {max_workers})...")
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        }
        cookies = {k: v for k, v in self.config.get('teambition.cookies', {}).items() if v}

        def fetch_single(t_id):
            url = f"https://www.teambition.com/api/tasks/{t_id}/activities"
            params = {'count': 50} 
            try:
                r = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                # print(f"Error fetching task {t_id}: {e}")
                pass
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {executor.submit(fetch_single, t_id): t_id for t_id in task_ids}
            completed_count = 0
            for future in concurrent.futures.as_completed(future_to_id):
                completed_count += 1
                if completed_count % 20 == 0:
                    print(f"  进度: {completed_count}/{len(task_ids)}...")
                data = future.result()
                if data:
                    all_activities.extend(data)
                    
        print(f"动态获取完成，共 {len(all_activities)} 条记录")
        return all_activities

    def fetch_tasks(self) -> Optional[str]:
        headers = {
            'accept': 'application/json',
            'accept-language': 'en,zh;q=0.9,zh-CN;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://www.teambition.com',
            'referer': f'https://www.teambition.com/project/{self.export_config.get("projectId")}/tasks',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'x-request-id': self._generate_request_id(),
            'x-timezone': str(self.export_config.get('timezone', 8))
        }

        cookies = {k: v for k, v in self.cookies.items() if v}

        payload = {
            'tql': self.export_config.get('tql'),
            'fileType': self.export_config.get('fileType'),
            'resourceType': self.export_config.get('resourceType'),
            'scope': self.export_config.get('scope'),
            'projectId': self.export_config.get('projectId'),
            'fields': self.export_config.get('fields'),
            'timezone': self.export_config.get('timezone'),
            'joinParentSubtask': self.export_config.get('joinParentSubtask')
        }

        try:
            # 1. Trigger Export
            print("正在触发任务导出...")
            response = requests.post(
                self.api_url,
                headers=headers,
                cookies=cookies,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            job_id = data.get('result', {}).get('jobId')
            if not job_id:
                print("未获取到 Job ID")
                return None
            
            print(f"导出任务已创建，Job ID: {job_id}")
            
            # 2. Poll Notifications for Download URL
            return self._poll_download_url(job_id, headers, cookies)

        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return None

    def _poll_download_url(self, job_id: str, headers: Dict, cookies: Dict) -> Optional[str]:
        import time
        import urllib.request
        import ssl
        
        print("正在等待导出完成通知...")
        notification_url = "https://notifications.teambition.com/api/notifications"
        max_retries = 30 # Wait up to 60s
        
        for i in range(max_retries):
            time.sleep(2)
            try:
                resp = requests.get(notification_url, headers=headers, cookies=cookies)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get('result', [])
                    
                    # Look for the export completion notification
                    # We look for notifications that contain "export" or "download" in payload
                    # Ideally we match against the Project ID or time, but for now we look for the most recent system msg
                    for note in results:
                        payload = note.get('payload', {})
                        # Check if it's the right type of notification (system message about export)
                        if "已完成导出" in payload.get('summary', '') or "finished export" in payload.get('summary', ''):
                             # Extract URL
                             actions = payload.get('actions', [])
                             download_url = None
                             
                             for action in actions:
                                 if action.get('fallbackUrl'):
                                     download_url = action.get('fallbackUrl')
                                     break
                                 if action.get('actionUrl') and action.get('actionUrl').startswith('http'):
                                     download_url = action.get('actionUrl')
                                     break
                             
                             if download_url:
                                 print(f"获取到下载地址: {download_url[:50]}...")
                                 return self._download_file(download_url)
                                 
            except Exception as e:
                print(f"轮询通知失败: {e}")
                
        print("等待导出超时")
        return None

    def _download_file(self, url: str) -> Optional[str]:
        import urllib.request
        import ssl
        
        try:
            print("正在下载 CSV 文件...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            context = ssl._create_unverified_context()
            
            with urllib.request.urlopen(req, context=context) as response:
                return response.read().decode('utf-8-sig') # Decode bytes to string for compatibility
        except Exception as e:
            print(f"下载文件失败: {e}")
            return None

    def _generate_request_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

    def save_csv(self, csv_content: str, output_dir: str = None) -> Optional[str]:
        if output_dir is None:
            output_dir = self.config.get('output.csv_dir', './data')
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"tasks_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write(csv_content)
            print(f"CSV 文件已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"保存 CSV 文件失败: {e}")
            return None
