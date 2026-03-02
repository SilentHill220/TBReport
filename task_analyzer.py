import pandas as pd
import json
import os
from typing import Dict, List, Any
from datetime import datetime
from config import Config

class TaskAnalyzer:
    def __init__(self, config: Config):
        self.config = config

    def load_csv(self, csv_path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            print(f"成功加载 CSV 文件: {csv_path}, 共 {len(df)} 条任务")
            return df
        except Exception as e:
            print(f"加载 CSV 文件失败: {e}")
            return pd.DataFrame()


    def analyze_tasks(self, df: pd.DataFrame, activities: List[Dict] = None) -> Dict[str, Any]:
        if df.empty:
            return {}

        summary = {
            'total_tasks': len(df),
            'updated_at': datetime.now().isoformat(),
            'by_user': {},
            'by_status': {},
            'by_priority': {}
        }
        
        # Pre-process activities to find who completed what
        completion_map = {} # task_id -> {user_name, done_at}
        if activities:
            completion_map = self._process_completion_activities(activities)
            print(f"从动态中解析出 {len(completion_map)} 个完成记录")

        user_col = self._find_column(df, ['执行者', 'executor', '执行人', 'owner', '负责人', 'assignee'])
        status_col = self._find_column(df, ['任务状态', 'status', '状态', 'isDone', 'is_done'])
        priority_col = self._find_column(df, ['priority', '优先级', 'importance'])
        title_col = self._find_column(df, ['标题', 'name', 'title', '任务名称', 'taskName'])
        created_col = self._find_column(df, ['created', 'createdDate', '创建时间', 'created_at'])
        due_col = self._find_column(df, ['dueDate', 'due', '截止时间', 'deadline'])
        overdue_col = self._find_column(df, ['已逾期', 'isOverdue', 'overdue'])
        parent_col = self._find_column(df, ['父任务', 'parentTask', 'parent'])
        parent_id_col = self._find_column(df, ['父任务 ObjectId', 'parentTaskId', 'parent_id'])
        done_at_col = self._find_column(df, ['完成时间', 'doneAt', 'completed_at', 'finished_at', 'finished', 'completed', '完成于'])
        # Also need ID column (Prioritize ObjectId for URLs)
        id_col = self._find_column(df, ['任务 ObjectId', '_id', 'id', 'taskId', '任务ID'])

        if status_col:
            status_counts = df[status_col].value_counts().to_dict()
            summary['by_status'] = status_counts
            
            # Calculate overall project progress (Studio XP)
            done_count = sum([count for status, count in status_counts.items() if str(status) in ['已完成', '关闭', '已关闭', 'Done', 'Closed']])
            summary['project_progress'] = {
                'done': int(done_count),
                'total': int(len(df)),
                'percent': round(done_count / len(df) * 100, 1) if len(df) > 0 else 0
            }

        # Identify "Recent Wins" (Tasks completed recently - we'll use CSV record as current "Finish" marker)
        summary['recent_wins'] = []
        
        if user_col:
            for user in df[user_col].unique():
                if pd.isna(user):
                    continue
                    
                user_tasks = df[df[user_col] == user]
                user_summary = {
                    'name': str(user),
                    'total_tasks': len(user_tasks),
                    'tasks': [],
                    'stats': {
                        'done_count': 0,
                        'bug_done': 0,
                        'urgent_done': 0,
                        'avg_age_done': 0,
                        'total_age_done': 0,
                        'active_pressure': 0
                    }
                }

                for _, task in user_tasks.iterrows():
                    # Calculate aging
                    age_days = 0
                    if created_col and pd.notna(task[created_col]):
                        try:
                            created_date = pd.to_datetime(task[created_col]).to_pydatetime()
                            if created_date.tzinfo:
                                created_date = created_date.replace(tzinfo=None)
                            age_days = (datetime.now() - created_date).days
                        except:
                            pass

                    t_title = str(task[title_col]) if title_col and pd.notna(task[title_col]) else '未命名任务'
                    t_status = str(task[status_col]) if status_col and pd.notna(task[status_col]) else '未知'
                    done_set = [
                        '已完成', '关闭', '已关闭', 'Done', 'Closed', 'Resolved', 
                        '已发布', 'Released', 'Finished', '已提交',
                        '待验收', '待测试', '待评审', '待发布',
                        '验收中', '评审中', '测完', '测试中',
                        '测试完成', '制作完成'
                    ]
                    if any(s in t_status for s in ['待处理', '待接收']):
                        is_done = False
                    else:
                        is_done = any(s in t_status for s in done_set) or \
                                  ('已' in t_status and '进行' not in t_status and '待' not in t_status) or \
                                  'Done' in t_status or \
                                  ('验收' in t_status and '中' in t_status)
                    
                    # identify if it's a bug or feature
                    is_bug = any(word in t_title.lower() for word in ['bug', '缺陷', '报错', '异常', '【bug】', '[bug]'])
                    t_prio = str(task[priority_col]) if priority_col and pd.notna(task[priority_col]) else '未设置'
                    is_urgent = any(word in t_prio for word in ['紧急', 'Urgent', '高', 'High'])


                    task_info = {
                        'id': str(task.get(id_col, task.get('_id', task.get('id', '')))),
                        'title': t_title,
                        'status': t_status,
                        'is_bug': is_bug,
                        'priority': t_prio,
                        'created': str(task[created_col]) if created_col and pd.notna(task[created_col]) else '',
                        'due': str(task[due_col]) if due_col and pd.notna(task[due_col]) else '',
                        'is_overdue': False,
                        'age_days': age_days,
                        'parent_task': str(task[parent_col]) if parent_col and pd.notna(task[parent_col]) else '',
                        'parent_id': str(task[parent_id_col]) if parent_id_col and pd.notna(task[parent_id_col]) else ''
                    }
                    
                    if is_done:
                        user_summary['stats']['done_count'] += 1
                        user_summary['stats']['total_age_done'] += age_days
                        if is_bug: user_summary['stats']['bug_done'] += 1
                        if is_urgent: user_summary['stats']['urgent_done'] += 1
                        
                        summary['recent_wins'].append({
                            'user': str(user),
                            'title': task_info['title'],
                            'id': task_info['id'],
                            'is_bug': is_bug,
                            'done_at': str(task[done_at_col]) if done_at_col and pd.notna(task[done_at_col]) else task_info['created']
                        })
                    else:
                        # Active pressure
                        p = 1
                        if '紧急' in t_prio or 'Urgent' in t_prio: p = 5
                        elif '高' in t_prio or 'High' in t_prio: p = 3
                        user_summary['stats']['active_pressure'] += p
                        
                        # Track strict active count separate from "pressure" score
                        user_summary['stats']['active_count'] = user_summary['stats'].get('active_count', 0) + 1

                    user_summary['tasks'].append(task_info)
                
                # --- PROCESS ACTIVITY CREDITS FOR THIS USER ---
                
                # Use a set of task IDs already credited via current ownership
                current_owned_done_ids = {t['id'] for t in user_summary['tasks'] if 
                   (any(s in t['status'] for s in ['已完成', '关闭', 'Done', 'Closed']) or '完成' in t['status'])
                }
                
                # Iterate all tasks in completion_map
                for t_id, credits_list in completion_map.items():
                    # credits_list is a list of {user, date, type, status}
                    
                    # 1. Check if this task is officially "Completed" in the current dataframe
                    t_row = df[df[id_col].astype(str) == t_id]
                    if t_row.empty: continue
                    
                    row = t_row.iloc[0]
                    t_stat = str(row[status_col]) if status_col and pd.notna(row[status_col]) else 'Unknown'
                    
                    is_task_completed = any(s in t_stat for s in [
                        '已完成', '关闭', 'Done', 'Closed', 'Resolved', 'Finished', 
                        '生产完成', '制作完成', '测试完成', '待验收', '待发布', '测试中'
                    ])
                    
                    if not is_task_completed:
                        continue

                    # 2. Check if this user is in the credits list
                    user_contribution = next((c for c in credits_list if c['user'] == str(user)), None)
                    
                    if user_contribution:
                         # Check if we already added this task to recent_wins for this user
                         already_added = any(
                             w['id'] == t_id and w['user'] == str(user) 
                             for w in summary['recent_wins']
                         )
                         if already_added:
                             continue
                             
                         t_tit = str(row[title_col]) if title_col and pd.notna(row[title_col]) else 'Unknown'
                         is_b = any(word in t_tit.lower() for word in ['bug', '缺陷', '报错', '异常'])
                         
                         # Add stats
                         user_summary['stats']['done_count'] += 1
                         if is_b: user_summary['stats']['bug_done'] += 1
                         
                         summary['recent_wins'].append({
                            'user': str(user),
                            'title': t_tit,
                            'id': t_id,
                            'is_bug': is_b,
                            'done_at': user_contribution['date'],
                            'source': 'activity_log',
                            'status_trigger': user_contribution['type']
                         })

                # Finalize stats
                if user_summary['stats']['done_count'] > 0:
                    user_summary['stats']['avg_age_done'] = round(user_summary['stats']['total_age_done'] / user_summary['stats']['done_count'], 1)

                summary['by_user'][str(user)] = user_summary
        
        # Sort and Filter recent wins
        if summary['recent_wins']:
            # Sort by done_at descending
            try:
                summary['recent_wins'].sort(key=lambda x: x.get('done_at', ''), reverse=True)
            except:
                pass
            
            # Filter by date - Restore 30-day limit for dashboard relevance, 
            # even if we want long term stats, 'Recent Wins' should be recent.
            now = datetime.now()
            filtered_wins = []
            for win in summary['recent_wins']:
                try:
                    d_str = win.get('done_at', '')
                    # Simple check if within last 60 days to be safe, or just keep top N?
                    # User complained about "Recent stats incorrect" - maybe too many old ones?
                    # Let's keep strict "Recent" = 30 days
                    if d_str:
                        # minimal parsing or try/except
                        pass
                    filtered_wins.append(win)
                except:
                    pass
            
            # Just limit to last 500 items to avoid overwhelming UI/Logs
            summary['recent_wins'] = summary['recent_wins'][:500]
        
        return summary

    def get_task_dict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert DataFrame to dictionary keyed by Task ID for state tracking
        """
        tasks = {}
        
        user_col = self._find_column(df, ['执行者', 'executor', '执行人', 'owner', '负责人', 'assignee'])
        status_col = self._find_column(df, ['任务状态', 'status', '状态', 'isDone', 'is_done'])
        priority_col = self._find_column(df, ['priority', '优先级', 'importance'])
        title_col = self._find_column(df, ['标题', 'name', 'title', '任务名称', 'taskName'])
        created_col = self._find_column(df, ['created', 'createdDate', '创建时间', 'created_at'])
        due_col = self._find_column(df, ['dueDate', 'due', '截止时间', 'deadline'])
        overdue_col = self._find_column(df, ['已逾期', 'isOverdue', 'overdue'])
        parent_col = self._find_column(df, ['父任务', 'parentTask', 'parent'])
        parent_id_col = self._find_column(df, ['父任务 ObjectId', 'parentTaskId', 'parent_id'])
        # Also need ID column (Prioritize ObjectId for URLs)
        id_col = self._find_column(df, ['任务 ObjectId', '_id', 'id', 'taskId', '任务ID'])
        
        for _, row in df.iterrows():
            # Use found ID col or fallback
            t_id = str(row.get(id_col, row.get('_id', row.get('id', ''))))
            if not t_id or t_id == 'nan':
                continue
            
            is_overdue = False
            if overdue_col and pd.notna(row[overdue_col]):
                # 'true', 'True', 'yes', '是' etc
                val = str(row[overdue_col]).lower()
                is_overdue = val in ['true', 'yes', '1', '是']
            
            parent_task = str(row[parent_col]) if parent_col and pd.notna(row[parent_col]) else ''
            parent_id = str(row[parent_id_col]) if parent_id_col and pd.notna(row[parent_id_col]) else ''

            tasks[t_id] = {
                'id': t_id,
                'title': str(row[title_col]) if title_col and pd.notna(row[title_col]) else '未命名',
                'executor': str(row[user_col]) if user_col and pd.notna(row[user_col]) else '未分配',
                'status': str(row[status_col]) if status_col and pd.notna(row[status_col]) else '未知',
                'due': str(row[due_col]) if due_col and pd.notna(row[due_col]) else '',
                'priority': str(row[priority_col]) if priority_col and pd.notna(row[priority_col]) else '',
                'is_overdue': is_overdue,
                'parent_task': parent_task,
                'parent_id': parent_id
            }
            
        return tasks

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> str:
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    def save_summary(self, summary: Dict[str, Any], output_path: str = None) -> bool:
        if output_path is None:
            output_path = self.config.get('output.summary_file', './data/summary.json')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"汇总数据已保存: {output_path}")
            return True
        except Exception as e:
            print(f"保存汇总数据失败: {e}")
            return False

    def print_summary(self, summary: Dict[str, Any]):
        print("\n" + "="*60)
        print(f"任务汇总报告 - {summary.get('updated_at', '')}")
        print("="*60)
        print(f"总任务数: {summary.get('total_tasks', 0)}")
        
        print("\n按状态统计:")
        for status, count in summary.get('by_status', {}).items():
            print(f"  {status}: {count}")
        
        print("\n按优先级统计:")
        for priority, count in summary.get('by_priority', {}).items():
            print(f"  {priority}: {count}")
        
        print("\n按人员统计:")
        for user_name, user_data in summary.get('by_user', {}).items():
            print(f"\n  {user_name}:")
            print(f"    总任务数: {user_data.get('total_tasks', 0)}")
            for task in user_data.get('tasks', []):
                print(f"    - [{task['status']}] {task['title']}")
                if task['due']:
                    print(f"      截止: {task['due']}")
        
        print("\n" + "="*60 + "\n")

    def _process_completion_activities(self, activities: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Parse activities to find who completed tasks.
        Returns: {task_id: [ {'user': user_name, 'date': iso_date, 'status': status_name}, ... ]}
        """
        credits = {}
        
        # Expanded completion statuses to include Testing/Pending Acceptance
        # As long as they moved it TO these states, they finished their part.
        done_statuses = [
            '生产完成', '制作完成', '已完成', 'Done', 'Completed', 'Finished',
            '测试中', 'Testing', '待测试', '待验收', '测试完成', 'Pending Acceptance'
        ]
        
        for act in activities:
            try:
                # Look for status updates
                # Structure: act['action'] == 'activity.task.update.status' (or similar)
                # content: {'oldStatus':..., 'newStatus':...}
                 
                action = act.get('action', '')
                content = act.get('content', {})
                
                # Check for explicit status change to 'Done' state
                is_status_change = 'status' in action or 'update' in action
                
                # We need to be careful. Sometimes content has 'task' object
                task_info = content.get('task', {})
                task_id = task_info.get('_id') or act.get('boundToObjectId') or act.get('_boundToObjectId')
                
                if not task_id:
                    continue
                
                # Determine if this was a completion event
                # Case 1: activity.task.status.update
                new_status = ""
                # print(f"check activity: {action} {content}") 
                
                if 'newStatus' in content:
                    new_status = content['newStatus'].get('name', '')
                elif 'taskflowstatus' in content:
                    # v2 activity format
                    val = content['taskflowstatus']
                    if isinstance(val, str):
                        new_status = val
                    elif isinstance(val, dict):
                        new_status = val.get('name', '')
                elif 'task' in content and 'status' in content['task']:
                     # creation or other update
                     pass
                
                # If the TARGET status is a DONE status
                # Case 2: Executor Change (activity.task.update.executor)
                # If they were an executor at some point, they contributed.
                if 'update.executor' in action:
                    # Old executor deserves credit too? AND New executor.
                    # Usually "content" has keys like "executor" (new)
                    # We want to catch the person who WAS executor? or the person who IS executor?
                    # Actually, if we just track "who was assigned", we can see it in:
                    # 1. "creator" of this action (usually the person assigning, might be themselves claiming)
                    # 2. content['executor'] (the new assignee)
                    
                    # We can credit the person who *triggered* the change (creator) ? 
                    # OR we explicitly look for "oldExecutor" vs "newExecutor".
                    # But simpler: If your name appears in an executor change event (Start or End), you were involved.
                    # Let's simple capture the `creator` of the event (Active User)
                    # AND if possible the target.
                    
                    # Taking a broad approach: track the creator of the event as a contributor
                    # (e.g. "Peng Siyuan changed executor to ...") -> Peng Siyuan was involved.
                    pass 

                # Universal Contributor Check:
                # If you touched the task status OR you were the executor in an update event
                
                user_name = None
                created_at = act.get('created')
                c_type = "unknown"
                
                # Check 1: Status Change (Pusher) - REMOVED
                # We do NOT credit simple status changes anymore. Only Executors (past or present) get credit.
                # if new_status and new_status in done_statuses:
                #      creator = act.get('creator', {}) or content.get('creator', {})
                #      user_name = creator.get('name')
                #      c_type = f"status_{new_status}"

                
                # Check 2: Executor Change
                # Logic: If you were the old executor, you handed it off -> you contributed.
                # If you are the new executor, you are now owning it -> will be credited if you finish it.
                if 'executor' in action or 'assign' in action:
                     # We want to credit the person who WAS the executor (oldExecutor).
                     # The person 'assigning' (creator) is usually a manager, unless they are assigning FROM themselves.
                     
                     # Check content for oldExecutor
                     old_ex = content.get('oldExecutor', {})
                     if isinstance(old_ex, dict):
                         user_name = old_ex.get('name')
                     elif isinstance(old_ex, str):
                         user_name = old_ex
                     
                     if not user_name:
                         # Sometimes the structure is flattened or different?
                         # If no oldExecutor, maybe look at who IS the executor now? No.
                         pass

                     if user_name:
                         c_type = "executor_handoff"
                
                if user_name:
                    if task_id not in credits:
                        credits[task_id] = []
                    
                    # Avoid adding same user multiple times for same task? 
                    # No, keep history, we dedup later in the stat calc if needed
                    # But for "Recent Wins" list we dedup.
                    credits[task_id].append({
                        'user': user_name,
                        'date': created_at,
                        'type': c_type
                    })
            except Exception as e:
                # print(f"Error parsing activity: {e}")
                pass
                
        return credits

