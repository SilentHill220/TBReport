
import pandas as pd
from config import Config
from teambition_api import TeambitionAPI
import json
import os

def debug_activities():
    print("Debugging Activity Structure...")
    config = Config()
    api = TeambitionAPI(config)
    
    # Load some tasks to get IDs
    data_dir = './data'
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if not files: return
    files.sort(reverse=True)
    csv_path = os.path.join(data_dir, files[0])
    df = pd.read_csv(csv_path)
    
    # Get IDs
    id_col = next((c for c in ['任务 ObjectId', '_id', 'id', 'taskId'] if c in df.columns), None)
    task_ids = df[id_col].dropna().astype(str).tolist()[:50] # Check first 50 tasks
    
    print("Fetching activities...")
    activities = api.fetch_tasks_activities(task_ids)
    
    print("\nLooking for Executor Changes...")
    found = 0
    for act in activities:
        action = act.get('action', '')
        if 'executor' in action and 'update' in action:
            print(f"\n--- Found Executor Update: {action} ---")
            print(json.dumps(act, indent=2, ensure_ascii=False))
            found += 1
            if found >= 3: break
            
    print("\nLooking for Status Changes...")
    found = 0
    for act in activities:
        action = act.get('action', '')
        if 'status' in action and 'update' in action:
            print(f"\n--- Found Status Update: {action} ---")
            print(json.dumps(act, indent=2, ensure_ascii=False))
            found += 1
            if found >= 3: break

if __name__ == "__main__":
    debug_activities()
