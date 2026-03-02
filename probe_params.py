import requests
import json
from config import Config

def probe():
    config = Config()
    project_id = config.get('teambition.project_id')
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    cookies = {k: v for k, v in config.get('teambition.cookies', {}).items() if v}
    
    # Valid endpoint from previous successful probe
    # url = f"https://www.teambition.com/api/projects/{project_id}/activities"
    
    # Load CSV to find a DONE task
    import pandas as pd
    import os
    
    data_dir = './data'
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if not files:
        print("No CSV found")
        return
    files.sort(reverse=True)
    csv_path = os.path.join(data_dir, files[0])
    print(f"Loading {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Find columns
    status_col = next((c for c in ['任务状态', 'status', '状态'] if c in df.columns), None)
    id_col = next((c for c in ['任务 ObjectId', '_id', 'id', 'taskId'] if c in df.columns), None)
    title_col = next((c for c in ['标题', 'name', 'title'] if c in df.columns), None)
    
    if not status_col or not id_col:
        print(f"Missing required columns. Found: {df.columns.tolist()}")
        return

    # Find a done task
    done_df = df[df[status_col].isin(['制作完成', '已完成', 'Done', 'Completed'])]
    
    if done_df.empty:
        print("No DONE tasks found in CSV")
        return
        
    target_task = done_df.iloc[0]
    t_id = str(target_task[id_col])
    t_title = str(target_task[title_col]) if title_col else "Unknown"
    
    print(f"Target Task: {t_title} (ID: {t_id})")
    
    scenarios = [
        {'name': f'Activities for {t_title}',
         'url': f'https://www.teambition.com/api/tasks/{t_id}/activities',
         'params': {'count': 50}
        }
    ]
    
    for scen in scenarios:
        print(f"\n--- Scenario: {scen['name']} ---")
        u = scen.get('url')
        try:
            r = requests.get(u, headers=headers, cookies=cookies, params=scen['params'])
            if r.status_code == 200:
                data = r.json()
                print(f"Got {len(data)} items")
                if data:
                    print(f"First Item Date: {data[0].get('created')}")
                    print(f"Last Item Date: {data[-1].get('created')}")
                    
                    found_update = False
                    for act in data:
                        if 'status' in act.get('action', '').lower():
                            print(f"  FOUND: {act['action']} at {act['created']}")
                            content = act.get('content',{})
                            if 'newStatus' in content:
                                print(f"         -> {content['newStatus'].get('name')}")
                            found_update = True
                            
                    if not found_update:
                        print("  No status updates found.")
            else:
                 print(f"Failed: {r.status_code}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    probe()
