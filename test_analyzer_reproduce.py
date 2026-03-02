import pandas as pd
from task_analyzer import TaskAnalyzer
from config import Config

def test_done_logic():
    # Mock Config
    config = Config()
    analyzer = TaskAnalyzer(config)
    
    # Create test data
    data = {
        '标题': ['Task 1', 'Task 2', 'Task 3', 'Task 4'],
        '执行者': ['User A', 'User A', 'User A', 'User A'],
        '任务状态': ['测试完成', '制作完成', '待处理', '已完成'],
        '任务 ObjectId': ['1', '2', '3', '4']
    }
    df = pd.DataFrame(data)
    
    print("Analyzing tasks with statuses: ", data['任务状态'])
    summary = analyzer.analyze_tasks(df)
    
    if 'User A' not in summary['by_user']:
        print("Error: User A not found in summary")
        return

    user_stats = summary['by_user']['User A']['stats']
    print(f"Done count: {user_stats['done_count']}")
    
    # Expect 3 done (Task 1, 2, 4). Task 3 is pending.
    expected_done = 3
    if user_stats['done_count'] == expected_done:
        print("SUCCESS: '测试完成' and '制作完成' are counted as done.")
    else:
        print(f"FAILURE: Expected {expected_done} done, got {user_stats['done_count']}.")

if __name__ == "__main__":
    test_done_logic()
