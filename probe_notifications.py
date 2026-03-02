import requests
import json
from config import Config

def probe_notifications():
    config = Config()
    
    # Use headers matching the user's successful request
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    
    cookies = {k: v for k, v in config.get('teambition.cookies', {}).items() if v}
    
    # 1. Try to get recent notifications
    # This endpoint is common for TB, and fits the "notifications" subdomain seen in user logs
    urls = [
        "https://www.teambition.com/api/users/me/notifications",
        "https://www.teambition.com/api/users/me/notifications?isRead=false", 
        "https://www.teambition.com/api/v2/teams/monitor/messages", # Sometimes system messages are here
        "https://notifications.teambition.com/api/notifications", # From user curl
        "https://www.teambition.com/api/activities" # Project activities
    ]
    
    for url in urls:
        print(f"\nProbing: {url}")
        try:
            resp = requests.get(url, headers=headers, cookies=cookies)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # Print structure preview
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
                    
                    results = data.get('result', [])
                    for note in results:
                        payload = note.get('payload', {})
                        if "已完成导出" in payload.get('summary', '') or "finished export" in payload.get('summary', ''):
                             actions = payload.get('actions', [])
                             for action in actions:
                                 url = action.get('fallbackUrl') or action.get('actionUrl')
                                 if url and url.startswith('http'):
                                     print(f"DOWNLOAD_URL={url}")
                                     return
                except Exception as e:
                    print(f"Error parse: {e}")
        except Exception as e:
            print(f"Error request: {e}")


if __name__ == "__main__":
    probe_notifications()
