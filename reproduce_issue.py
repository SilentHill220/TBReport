
import pandas as pd
from task_analyzer import TaskAnalyzer
import os

# Create a mock config (not used by analyze_csv but needed if I were initializing fully)
# TaskAnalyzer doesn't take config in __init__, so it's fine.

def test_extraction():
    csv_path = 'data/manual_export.csv'
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    class MockConfig:
        def __init__(self):
            self.settings = {"dingtalk": {"enabled": False}}
            
    analyzer = TaskAnalyzer(MockConfig())
    
    # We want to see if it extracts 'parent_task' correctly.
    # Analyzing...
    df = analyzer.load_csv(csv_path)
    summary = analyzer.analyze_tasks(df)
    
    # Check specific task
    # From csv inspection, task '遗物获得、飞行动做优化' is at index 15. 
    # Let's find it in the summary['by_user'] or just return the raw task dict if we can access it.
    # analyze_csv returns a summary dict.
    
    found = False
    for user, data in summary['by_user'].items():
        for t in data['tasks']:
            if '遗物获得' in t['title']:
                print(f"Task Found: {t['title']}")
                print(f"Executor: {user}")
                print(f"Parent Task Extracted: '{t.get('parent_task')}'")
                found = True
    
    if not found:
        print("Task not found in summary!")

if __name__ == "__main__":
    test_extraction()
