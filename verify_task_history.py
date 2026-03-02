
import pandas as pd
from config import Config
from teambition_api import TeambitionAPI
from task_analyzer import TaskAnalyzer
import json
import sys
import os

def verify_history(search_term):
    config = Config()
    api = TeambitionAPI(config)
    analyzer = TaskAnalyzer(config)
    
    # 1. Load Tasks
    # If forced or no CSV found, fetch from API
    data_dir = './data'
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'tasks_' in f]
    files.sort(reverse=True)
    
    df = pd.DataFrame()
    if files:
        csv_path = os.path.join(data_dir, files[0])
        print(f"Loading local data from {csv_path}...")
        df = analyzer.load_csv(csv_path)
        
        # Check if target exists in local
        title_col = next((c for c in ['标题', 'name', 'title'] if c in df.columns), None)
        if title_col:
            found = df[df[title_col].astype(str).str.contains(search_term, na=False)]
            if found.empty:
                print("Not found in local CSV. Fetching fresh data from API...")
                csv_content = api.fetch_tasks()
                if csv_content:
                    from io import StringIO
                    df = pd.read_csv(StringIO(csv_content))
    else:
        print("No local CSV. Fetching fresh data from API...")
        csv_content = api.fetch_tasks()
        if csv_content:
            from io import StringIO
            df = pd.read_csv(StringIO(csv_content))
            
    if df.empty:
        print("Failed to load task data.")
        return
    
    # 2. Find task
    title_col = next((c for c in ['标题', 'name', 'title'] if c in df.columns), None)
    id_col = next((c for c in ['任务 ObjectId', '_id', 'id', 'taskId'] if c in df.columns), None)
    
    if not title_col or not id_col:
        print("Columns not found.")
        return

    # Filter
    found_tasks = df[df[title_col].astype(str).str.contains(search_term, na=False)]
    
    if found_tasks.empty:
        print(f"No task found matching '{search_term}'")
        return
        
    target_task = found_tasks.iloc[0]
    t_id = str(target_task[id_col])
    t_title = str(target_task[title_col])
    print(f"\nAnalyzing Task: [{t_title}] (ID: {t_id})")
    print(f"Current Executor (CSV): {target_task.get('执行者', 'Unknown')}")
    print(f"Current Status (CSV): {target_task.get('任务状态', 'Unknown')}")
    
    # 3. Fetch Activities
    print("\nFetching full activity log...")
    activities = api.fetch_tasks_activities([t_id])
    print(f"Fetched {len(activities)} activity records.")
    
    # 4. Show Relevant History
    print("\n--- 历史执行记录 (History) ---")
    completion_map = analyzer._process_completion_activities(activities)
    
    credits = completion_map.get(t_id, [])
    if not credits:
        print("No completion credits found in history.")
    else:
        for c in credits:
            print(f"  - User: {c['user']:<6} | Action: {c.get('type','unknown'):<20} | Time: {c['date']}")
            
    # 5. Show Raw Status Changes (Debug)
    print("\n--- 完整活动日志 (Full Log) ---")
    for act in activities:
        creator = act.get('creator', {}).get('name', 'Unknown')
        action = act.get('action', '')
        created_at = act.get('created', '')[:16].replace('T', ' ')
        title = act.get('title', 'No Title')
        
        print(f"  [{created_at}] {creator} | {action}")
        print(f"      -> {title}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_task_history.py <task_name_part>")
        # Default for test
        verify_history("天赋融合")
    else:
        verify_history(sys.argv[1])
