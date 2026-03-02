import pandas as pd
import sys

csv_path = r"h:\projects\TBData\data\tasks_20260128_170606.csv"

try:
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print("Columns:", df.columns.tolist())
    
    if '迭代' in df.columns:
        print("\nUnique Iterations:")
        print(df['迭代'].unique())
        
    print("\nTasks due around Feb 12 (2026-02-05 to 2026-02-15):")
    if '截止时间' in df.columns:
        # Convert to datetime, handling errors
        df['截止时间'] = pd.to_datetime(df['截止时间'], errors='coerce')
        
        # Filter
        start_date = pd.Timestamp("2026-02-01")
        end_date = pd.Timestamp("2026-02-15")
        
        mask = (df['截止时间'] >= start_date) & (df['截止时间'] <= end_date)
        target_tasks = df[mask]
        
        print(f"Found {len(target_tasks)} tasks in this range.")
        for _, row in target_tasks.iterrows():
            print(f"- [{row['任务状态']}] {row['标题']} (Due: {row['截止时间']}, User: {row['执行者']})")

    # Also check for "Feb" or "2月" in iteration name if not explicitly found above
    print("\nSearching for '2月' in Iteration names:")
    if '迭代' in df.columns:
        feb_tasks = df[df['迭代'].astype(str).str.contains('2月', na=False)]
        print(f"Found {len(feb_tasks)} tasks with '2月' in iteration.")
        
        print("\nStatus Breakdown for '2月' tasks:")
        print(feb_tasks['任务状态'].value_counts())
        
        print("\nAssignee Breakdown for '2月' tasks:")
        print(feb_tasks['执行者'].value_counts())

        print("\nTask List:")
        for _, row in feb_tasks.iterrows():
            print(f"- [{row['任务状态']}] {row['标题']} (User: {row['执行者']}, Iteration: {row['迭代']})")

        
except Exception as e:
    print(f"Error: {e}")
