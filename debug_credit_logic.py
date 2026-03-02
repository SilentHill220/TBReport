
import pandas as pd
from config import Config
from teambition_api import TeambitionAPI
from task_analyzer import TaskAnalyzer
import os

def debug_han_credit():
    config = Config()
    analyzer = TaskAnalyzer(config)
    api = TeambitionAPI(config)
    
    # 1. Load Data
    data_dir = './data'
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'tasks_' in f]
    files.sort(reverse=True)
    if not files:
        print("No data found")
        return
        
    csv_path = os.path.join(data_dir, files[0])
    print(f"Loading {csv_path}...")
    df = analyzer.load_csv(csv_path)
    
    # 2. Find the Task
    target_title_part = "重构拆分"
    title_col = next((c for c in ['标题', 'name', 'title'] if c in df.columns), None)
    id_col = next((c for c in ['任务 ObjectId', '_id', 'id', 'taskId'] if c in df.columns), None)
    status_col = next((c for c in ['任务状态', 'status', 'TaskStatus', '状态'] if c in df.columns), None)
    
    task_row = df[df[title_col].astype(str).str.contains(target_title_part, na=False)]
    if task_row.empty:
        print("Task not found in local CSV! Fetching fresh data from API...")
        csv_content = api.fetch_tasks()
        if csv_content:
             from io import StringIO
             df = pd.read_csv(StringIO(csv_content))
             task_row = df[df[title_col].astype(str).str.contains(target_title_part, na=False)]
        
        if task_row.empty:
            print("Task STILL not found after fresh fetch!")
            return
        
    row = task_row.iloc[0]
    t_id = str(row[id_col])
    t_title = str(row[title_col])
    t_status = str(row[status_col])
    
    print(f"Target Task: {t_title} (ID: {t_id}) Status: {t_status}")
    
    # Check is_task_completed logic
    done_qs = [
        '已完成', '关闭', 'Done', 'Closed', 'Resolved', 'Finished', 
        '生产完成', '制作完成', '测试完成', '待验收', '待发布', '测试中'
    ]
    is_completed = any(s in t_status for s in done_qs)
    print(f"Is Task Completed (Logic Check): {is_completed}")
    
    # 3. Fetch Activities
    print("Fetching activities...")
    activities = api.fetch_tasks_activities([t_id])
    
    # 4. Process Completion Map
    print("Processing activities...")
    completion_map = analyzer._process_completion_activities(activities)
    
    if t_id not in completion_map:
        print("Task not found in completion map!")
    else:
        credits = completion_map[t_id]
        print(f"Credits found: {len(credits)}")
        han_found = False
        for c in credits:
            print(f"  - {c['user']} ({c.get('type')})")
            if '韩嵩洋' in c['user']:
                han_found = True
        
        if han_found:
            print("韩嵩洋 IS in the credits list.")
        else:
            print("韩嵩洋 is NOT in the credits list.")
            
    # 5. Simulate Analyze Tasks loop for Han
    user = "韩嵩洋"
    print(f"\nSimulating analyze_tasks logic for user: {user}")
    
    # Check if we find the task in the loop
    if t_id in completion_map:
        credits_list = completion_map[t_id]
        
        # 1. CSV Check
        print(f"  [Logic] Checking CSV row for ID {t_id}")
        t_row_check = df[df[id_col].astype(str) == t_id]
        if t_row_check.empty:
            print("  [Logic Fail] Task row not found in DF lookup")
        else:
            tr = t_row_check.iloc[0]
            ts = str(tr[status_col])
            print(f"  [Logic] Status in DF: {ts}")
            
            is_done_check = any(s in ts for s in done_qs)
            if not is_done_check:
                print("  [Logic Fail] Task considered NOT DONE by loop logic")
            else:
                print("  [Logic] Task considered DONE")
                
                # 2. User Check
                uc = next((c for c in credits_list if c['user'] == str(user)), None)
                if uc:
                    print(f"  [Logic] User contribution found: {uc}")
                    print("  [SUCCESS] Should be credited!")
                else:
                    print("  [Logic Fail] User contribution NOT found in list for string match.")

if __name__ == "__main__":
    debug_han_credit()
