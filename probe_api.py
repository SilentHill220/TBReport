import requests
import json
import time
from config import Config

def probe():
    config = Config()
    project_id = config.get('teambition.project_id')
    export_url = config.get('teambition.api_url')
    cookies = {k: v for k, v in config.get('teambition.cookies', {}).items() if v}
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # 1. Start Export
    print(f"Starting export for project {project_id}...")
    payload = {
        'tql': config.get('export.tql'),
        'fileType': config.get('export.fileType'),
        'resourceType': config.get('export.resourceType'),
        'scope': config.get('export.scope'),
        'projectId': project_id,
        'fields': config.get('export.fields'),
        'timezone': config.get('export.timezone'),
        'joinParentSubtask': config.get('export.joinParentSubtask')
    }
    
    resp = requests.post(export_url, headers=headers, cookies=cookies, json=payload)
    print(f"Export Status: {resp.status_code}")
    print(f"Export Headers: {dict(resp.headers)}")
    print(f"Export Response: {resp.text}")
    
    try:
        data = resp.json()
        job_id = data.get('result', {}).get('jobId')
    except:
        print("Failed to parse JSON")
        return

    if not job_id:
        print("No job ID found")
        return
        
    print(f"Got Job ID: {job_id}")
    
    # 2. Probe Status Endpoints
    # Potential patterns
    endpoints_to_try = [
        # Check Project related
        f"https://www.teambition.com/api/project/{project_id}/task/export/{job_id}",
        f"https://www.teambition.com/api/project/{project_id}/task/export/download/{job_id}",
        f"https://www.teambition.com/api/project/{project_id}/jobs/{job_id}",
        
        # Check Global
        f"https://www.teambition.com/api/jobs/{job_id}",
        f"https://www.teambition.com/api/v2/jobs/{job_id}",
        f"https://www.teambition.com/api/works/{job_id}",
        
        # Check Task related
        f"https://www.teambition.com/api/task/export/{job_id}",
        f"https://www.teambition.com/api/task/export/{job_id}/download",
    ]
    
    for url in endpoints_to_try:
        print(f"\nProbing: {url}")
        try:
            r = requests.get(url, headers=headers, cookies=cookies)
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                print(f"Response: {r.text[:500]}...") # Print first 500 chars
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    probe()
