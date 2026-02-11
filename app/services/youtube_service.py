import os
import requests

def get_video_transcript(video_id: str) -> str | None:
    # 1. This grabs the value you saved in the Render dashboard
    API_KEY = os.getenv("SUPADATA_API_KEY")
    
    # Safety check: if you forgot to set the key, the app won't crash secretly
    if not API_KEY:
        print("ERROR: SUPADATA_API_KEY is not set in environment variables.")
        return None

    url = f"https://api.supadata.ai/v1/transcript?url=https://www.youtube.com/watch?v={video_id}"
    headers = {"x-api-key": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            segments = data.get('content', [])
            
            # Combine all snippets into one clean block of text
            full_text = " ".join(s.get('text', '').replace("\n", " ").strip() for s in segments)
            return full_text
            
        print(f"API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
        
    return None
