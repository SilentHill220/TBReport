import schedule
import time
from datetime import datetime
from typing import Callable, Optional
from config import Config

class TaskScheduler:
    def __init__(self, config: Config):
        self.config = config
        self.scheduler_config = config.get_scheduler_config()
        self.running = False

    def schedule_task(self, task_func: Callable, interval_minutes: int = None):
        if interval_minutes is None:
            interval_minutes = self.scheduler_config.get('interval_minutes', 30)
        
        schedule.every(interval_minutes).minutes.do(task_func)
        print(f"已设置定时任务，每 {interval_minutes} 分钟执行一次")

    def schedule_at_time(self, task_func: Callable, time_str: str):
        schedule.every().day.at(time_str).do(task_func)
        print(f"已设置定时任务，每天 {time_str} 执行")

    def start(self):
        self.running = True
        print("定时任务调度器已启动...")
        print("按 Ctrl+C 停止")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n定时任务调度器已停止")
            self.running = False

    def stop(self):
        self.running = False
        schedule.clear()

    def run_once(self, task_func: Callable):
        print(f"执行一次性任务: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        task_func()
