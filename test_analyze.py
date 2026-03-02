from task_analyzer import TaskAnalyzer
from config import Config
import pandas as pd
import os

def test():
    config = Config()
    analyzer = TaskAnalyzer(config)
    
    csv_path = "data/manual_export.csv"
    if not os.path.exists(csv_path):
        print("CSV not found")
        return
        
    print(f"Loading {csv_path}...")
    df = analyzer.load_csv(csv_path)
    
    if df.empty:
        print("DataFrame is empty")
        return
        
    print(f"Loaded {len(df)} rows. Columns: {df.columns.tolist()}")
    
    summary = analyzer.analyze_tasks(df)
    analyzer.print_summary(summary)

if __name__ == "__main__":
    test()
