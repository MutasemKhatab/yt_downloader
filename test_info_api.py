import requests
import json
import sys

def test_video_info():
    url = 'http://localhost:5000/info'
    video_url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.youtube.com/watch?v=Rd7yyutb-DI'
    
    data = {'url': video_url}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        info = response.json()
        formats = info.get('formats', [])
        
        print(f"Video title: {info.get('title')}")
        print(f"Uploader: {info.get('uploader')}")
        print(f"Total formats found: {len(formats)}")
        print("\nFormat details:")
        
        for i, fmt in enumerate(formats):
            print(f"{i+1}. ID: {fmt['format_id']}, Res: {fmt['resolution']}, Ext: {fmt['ext']}, Note: {fmt.get('format_note', 'N/A')}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    test_video_info()
