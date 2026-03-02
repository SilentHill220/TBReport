import urllib.request
import ssl

def download_file():
    # Cleaned URL from user input (raw string to assume what user gave is correct)
    url = "https://teambition-file.oss-cn-zhangjiakou.aliyuncs.com/export-file/2025-12-26/unknown/e357e483-49b4-4d36-9a89-cbd756d1e179/1766759285812.csv?OSSAccessKeyId=LTAI5tQEos3VHgeguezvjSfw&Expires=1766845686&Signature=7LWFGNHGW%2FptxYzl4CV9JeUBoj0%3D&response-content-disposition=attachment%3BfileName*%3DUTF-8%27%27%25E3%2580%2590%25E9%259A%2590%25E7%25A7%2598%25E4%25B9%258B%25E6%25BD%25AE-%25E9%25A1%25B9%25E7%259B%25AE%25E7%25A0%2594%25E5%258F%2591%25E3%2580%2591%25E4%25BB%25BB%25E5%258A%25A1%25E4%25BF%25A1%25E6%2581%25AF%25E8%25A1%25A8_20251226.csv"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Referer": "https://www.teambition.com/"
    }

    print(f"Downloading from {url[:50]}...")
    
    try:
        req = urllib.request.Request(url, headers=headers)
        # Create unverified context to avoid SSL errors just in case
        context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=context) as response:
            print(f"Status Code: {response.getcode()}")
            content = response.read()
            
            # Check for XML error signature manually since 200 OK might still be returned or urllib raises error on 4xx
            if b"<Error>" in content[:100]:
                print(f"Error content: {content.decode('utf-8')}")
            else:
                with open("data/manual_export.csv", "wb") as f:
                    f.write(content)
                print("Download successful: data/manual_export.csv")
                print(f"Content preview: {content[:100]}")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Download failed: {e}")

if __name__ == "__main__":
    download_file()
