from main import fetch_and_analyze

if __name__ == "__main__":
    print("Forcing update of task statistics...")
    # Run analysis but do NOT send notifications (to avoid spamming while fixing)
    success = fetch_and_analyze(send_to_dingtalk=False)
    if success:
        print("Update complete. summary.json should now be correct.")
    else:
        print("Update failed.")
