import requests
import json
from config import Config

def probe_activities():
    config = Config()
    project_id = config.get('teambition.project_id')
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    cookies = {k: v for k, v in config.get('teambition.cookies', {}).items() if v}

    print(f"Probing activities for project: {project_id}")

    # Potential endpoints
    endpoints = [
        f"https://www.teambition.com/api/projects/{project_id}/activities",
        f"https://www.teambition.com/api/v2/projects/{project_id}/activities",
        f"https://www.teambition.com/api/activities?_projectId={project_id}",
    ]

    for url in endpoints:
        print(f"\nRequesting: {url}")
        try:
            resp = requests.get(url, headers=headers, cookies=cookies)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Success! Found {len(data)} items/keys")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:300] + "...")
                return # Stop after first success
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    probe_activities()
