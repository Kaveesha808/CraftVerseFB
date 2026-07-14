import os
import json
import urllib.request
import urllib.parse
from typing import Tuple, Dict, Any

def verify_fb_token(page_id: str, access_token: str) -> Tuple[bool, str]:
    """
    Verifies Facebook Page ID and Access Token against Graph API.
    Returns: (is_valid, page_name_or_error)
    """
    if not page_id or not access_token:
        return False, "Page ID or Access Token is missing"
    
    url = f"https://graph.facebook.com/v19.0/{page_id}?fields=name,id&access_token={urllib.parse.quote(access_token)}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data.get("name", f"Page {page_id}")
    except Exception as e:
        return False, f"Verification failed: {str(e)}"

def upload_reel_to_fb_page(
    video_path: str,
    page_id: str,
    access_token: str,
    caption_en: str,
    caption_si: str,
    hashtags: str
) -> Tuple[bool, str, str, str]:
    """
    Uploads a 9:16 Reel to Facebook Page via Facebook Graph API.
    Returns: (success, fb_video_id, fb_post_url, error_message)
    """
    if not page_id or not access_token:
        return False, "", "", "Facebook Page ID or Access Token not configured in Settings."

    if not os.path.exists(video_path):
        return False, "", "", f"Video file not found at {video_path}"

    full_description = f"{caption_si}\n\n{caption_en}\n\n{hashtags}"

    # We use Graph API /v19.0/{page_id}/videos endpoint which publishes vertical reels directly to Page Video/Reels feed
    # Note: For actual binary upload without heavy requests module, we can use requests or multipart request,
    # or if requests is available we use it. Let's try requests first, fallback to mock simulation if offline/dev token.
    try:
        import requests
        url = f"https://graph.facebook.com/v19.0/{page_id}/videos"
        payload = {
            "access_token": access_token,
            "description": full_description
        }
        with open(video_path, "rb") as f:
            files = {"source": f}
            response = requests.post(url, data=payload, files=files, timeout=120)
        
        data = response.json()
        if "id" in data:
            video_id = data["id"]
            post_url = f"https://www.facebook.com/{page_id}/videos/{video_id}"
            return True, video_id, post_url, ""
        else:
            err_msg = data.get("error", {}).get("message", json.dumps(data))
            return False, "", "", f"FB API Error: {err_msg}"
    except ImportError:
        return False, "", "", "Python requests library not installed. Please install requests."
    except Exception as e:
        return False, "", "", f"Upload exception: {str(e)}"
