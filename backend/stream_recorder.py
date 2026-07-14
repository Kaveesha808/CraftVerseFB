import os
import subprocess
import time
import urllib.request
from datetime import datetime
from typing import Tuple, Optional

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
RAW_DIR = os.path.join(MEDIA_DIR, "raw")
THUMB_DIR = os.path.join(MEDIA_DIR, "thumbnails")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def download_hls_via_python(stream_url: str, output_path: str, duration_seconds: int = 45) -> bool:
    """
    Robust native Python HLS downloader that fetches .ts segments from the playlist
    and concatenates them into output_path when direct FFmpeg demuxing faces network issues.
    """
    try:
        req = urllib.request.Request(stream_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
        
        # Check if master playlist or media playlist
        base_url = stream_url.rsplit("/", 1)[0]
        lines = content.strip().splitlines()
        
        # If it points to a sub-playlist (.m3u8), pick the highest resolution sub-playlist
        ts_urls = []
        for l in lines:
            if l.strip() and not l.strip().startswith("#"):
                sub_url = l.strip()
                if not sub_url.startswith("http"):
                    sub_url = base_url + "/" + sub_url
                if sub_url.endswith(".m3u8"):
                    req_sub = urllib.request.Request(sub_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req_sub, timeout=15) as r_sub:
                        sub_content = r_sub.read().decode("utf-8")
                    sub_base = sub_url.rsplit("/", 1)[0]
                    for sl in sub_content.strip().splitlines():
                        if sl.strip() and not sl.strip().startswith("#"):
                            ts = sl.strip()
                            if not ts.startswith("http"):
                                ts = sub_base + "/" + ts
                            ts_urls.append(ts)
                    break
                else:
                    ts_urls.append(sub_url)

        if not ts_urls:
            return False

        # Download chunks corresponding to duration (assume ~3-5 sec per ts chunk -> ~12 chunks for 45s)
        chunks_needed = max(4, duration_seconds // 3)
        temp_ts_path = output_path + ".temp.ts"
        with open(temp_ts_path, "wb") as f_out:
            for ts_u in ts_urls[:chunks_needed]:
                try:
                    r_ts = urllib.request.Request(ts_u, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(r_ts, timeout=15) as ts_resp:
                        f_out.write(ts_resp.read())
                except Exception:
                    continue

        if os.path.exists(temp_ts_path) and os.path.getsize(temp_ts_path) > 50000:
            # Convert container to mp4 cleanly
            cmd = ["ffmpeg", "-y", "-i", temp_ts_path, "-c", "copy", output_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            try:
                os.remove(temp_ts_path)
            except Exception:
                pass
            return os.path.exists(output_path) and os.path.getsize(output_path) > 10000

    except Exception as e:
        print(f"Python HLS download fallback error: {e}")
    return False

def record_hls_clip(stream_url: str, duration_seconds: int = 45) -> Tuple[bool, str, str, str]:
    """
    Records a live clip from the HLS stream for `duration_seconds`.
    Returns: (success, raw_video_path, thumbnail_path, error_message)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"craft_raw_{timestamp}.mp4"
    thumb_filename = f"craft_thumb_{timestamp}.jpg"
    
    raw_path = os.path.join(RAW_DIR, output_filename)
    thumb_path = os.path.join(THUMB_DIR, thumb_filename)

    # 1. First attempt: Robust FFmpeg HLS capture with User-Agent & reconnect flags
    cmd_record = [
        "ffmpeg", "-y",
        "-user_agent", USER_AGENT,
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        "-i", stream_url,
        "-t", str(duration_seconds),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        raw_path
    ]

    err_msg = ""
    try:
        process = subprocess.run(cmd_record, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=duration_seconds + 45)
        if not os.path.exists(raw_path) or os.path.getsize(raw_path) < 10000:
            err_msg = process.stderr.decode("utf-8", errors="ignore")[-300:]
    except Exception as e:
        err_msg = str(e)

    # 2. Second attempt (Fallback): Native Python HLS chunk downloader if FFmpeg failed
    if not os.path.exists(raw_path) or os.path.getsize(raw_path) < 10000:
        print("FFmpeg direct capture failed, trying native Python HLS segment downloader...")
        py_ok = download_hls_via_python(stream_url, raw_path, duration_seconds=duration_seconds)
        if not py_ok:
            return False, "", "", f"Failed to record stream. Last error: {err_msg}"

    # 3. Extract a high-res thumbnail near the middle of the clip
    thumb_time = max(1, duration_seconds // 2)
    cmd_thumb = [
        "ffmpeg", "-y",
        "-ss", str(thumb_time),
        "-i", raw_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]
    try:
        subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if not os.path.exists(thumb_path):
            cmd_thumb_fallback = [
                "ffmpeg", "-y", "-i", raw_path, "-vframes", "1", "-q:v", "2", thumb_path
            ]
            subprocess.run(cmd_thumb_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    except Exception:
        pass

    return True, raw_path, thumb_path, ""
