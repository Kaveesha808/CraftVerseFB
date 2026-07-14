import os
import subprocess
import json
import urllib.request
from typing import Tuple

def is_valid_craft_clip(video_path: str, thumbnail_path: str = "", gemini_api_key: str = "") -> Tuple[bool, str]:
    """
    Analyzes a recorded live stream clip to ensure it is NOT an advertisement, commercial break,
    black screen, frozen stream slate, or offline bumper.
    
    Returns: (is_valid: bool, reason: str)
    """
    if not os.path.exists(video_path):
        return False, "Video file does not exist."

    # 1. Check for black screen / broken stream using ffmpeg blackdetect
    # If the clip has more than 5 seconds of black screen, it's likely broken or a commercial break slate.
    cmd_black = [
        "ffmpeg", "-i", video_path,
        "-vf", "blackdetect=d=3:pix_th=0.10",
        "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd_black, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        stderr_txt = proc.stderr.decode("utf-8", errors="ignore")
        if "black_start:" in stderr_txt and "black_duration:" in stderr_txt:
            # Check duration of black screen
            for line in stderr_txt.splitlines():
                if "black_duration:" in line:
                    parts = line.split("black_duration:")
                    if len(parts) > 1:
                        try:
                            dur = float(parts[1].split()[0])
                            if dur >= 4.0:
                                return False, f"Stream break / black screen detected ({dur:.1f}s black slate)"
                        except ValueError:
                            pass
    except Exception:
        pass

    # 2. Check for frozen/static screen (freezedetect)
    cmd_freeze = [
        "ffmpeg", "-i", video_path,
        "-vf", "freezedetect=n=-50dB:d=4",
        "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd_freeze, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        stderr_txt = proc.stderr.decode("utf-8", errors="ignore")
        if "freeze_start: " in stderr_txt and "freeze_duration: " in stderr_txt:
            return False, "Stream break / frozen static image detected"
    except Exception:
        pass

    # 3. If Gemini API Key is configured, use Gemini Vision to verify if it is an advertisement or actual craft DIY
    if gemini_api_key and len(gemini_api_key.strip()) > 10 and thumbnail_path and os.path.exists(thumbnail_path):
        try:
            import base64
            with open(thumbnail_path, "rb") as img_f:
                img_b64 = base64.b64encode(img_f.read()).decode("utf-8")
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key.strip()}"
            prompt = (
                "Look at this video frame from a live stream. Is this an advertisement, commercial break slate, "
                "or channel offline banner? Or is it an actual DIY / craft / household hack demonstration? "
                "Answer ONLY with JSON: {\"is_ad_or_break\": true/false, \"reason\": \"short explanation\"}"
            )
            payload = json.dumps({
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]
                }],
                "generationConfig": {"temperature": 0.2}
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                text_clean = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text_clean)
                if parsed.get("is_ad_or_break") is True:
                    return False, f"Advertisement / Break detected by AI: {parsed.get('reason', 'Commercial break')}"
        except Exception as e:
            print(f"AI Ad check fallback: {e}")

    # Clip passed quality & ad detection
    return True, "Valid DIY Craft Content"
