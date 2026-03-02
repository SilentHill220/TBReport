import json
import os
from typing import Dict, List, Any
from datetime import datetime

class TaskManager:
    def __init__(self, state_file: str):
        self.state_file = state_file

    def load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_file):
            return {}
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load state file: {e}")
            return {}

    def save_state(self, tasks: Dict[str, Any]):
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "tasks": tasks
            }
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("Task state saved.")
        except Exception as e:
            print(f"Failed to save state: {e}")

    def detect_changes(self, old_tasks: Dict[str, Any], new_tasks: Dict[str, Any]) -> List[str]:
        changes = []
        
        # Check for new or changed tasks
        for task_id, new_task in new_tasks.items():
            old_task = old_tasks.get(task_id)
            
            if not old_task:
                # New task
                # Only report if it's NOT done ? Or report all new?
                # Usually "New Task Assigned" is interesting.
                if new_task['status'] not in ['已完成', '关闭', 'Done', 'Closed', 'Completed']:
                    changes.append(f"🆕 新增任务: {new_task['title']} ({new_task['executor']})")
                continue

            # Task exists, check for changes
            
            # Helper to check if done
            is_done_old = old_task['status'] in ['已完成', '关闭', '已关闭', 'Done', 'Closed', 'Completed']
            is_done_new = new_task['status'] in ['已完成', '关闭', '已关闭', 'Done', 'Closed', 'Completed']
            
            # If both are done, skip all checks (we don't care about changes in archived tasks)
            if is_done_old and is_done_new:
                continue

            # 1. Status Change
            if old_task['status'] != new_task['status']:
                # If changed to Done
                if is_done_new:
                    changes.append(f"✅ 任务完成: {new_task['title']} ({new_task['executor']})")
                elif is_done_old:
                    changes.append(f"🔙 任务重开: {new_task['title']} ({new_task['status']})")
                else:
                    changes.append(f"🔄 状态变更: {new_task['title']} -> {new_task['status']}")

            # 2. Executor Change
            if old_task['executor'] != new_task['executor']:
                 changes.append(f"👤 执行者变更: {new_task['title']} ({old_task['executor']} -> {new_task['executor']})")

        return changes
