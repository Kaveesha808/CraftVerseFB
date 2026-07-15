import os
import subprocess
from datetime import datetime
from typing import Tuple

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
REELS_DIR = os.path.join(MEDIA_DIR, "reels")
THUMB_DIR = os.path.join(MEDIA_DIR, "thumbnails")

os.makedirs(REELS_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

def create_vertical_reel(raw_video_path: str, header_text: str = "🔥 CRAZY 5-MIN DIY HACK 💡") -> Tuple[bool, str, str, str]:
    """
    Transforms a landscape raw clip into a high-retention 9:16 Vertical Reel (1080x1920)
    with built-in ANTI-COPYRIGHT BYPASS SHIELD:
    - 1.15x Speed Boost (setpts + atempo): Prevents audio/video duration match while making pacing punchier!
    - Horizontal Mirror Flip (hflip): Bypasses visual frame hash algorithms while looking 100% natural for hands/DIY!
    - Color/Contrast Boost (eq=contrast=1.06:saturation=1.12): Modifies pixel histograms to bypass perceptual hash scrapers!
    - Blurred ambient vertical background canvas + centered crisp action.
    Returns: (success, reel_video_path, reel_thumbnail_path, error_message)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"craft_reel_916_{timestamp}.mp4"
    thumb_filename = f"craft_reel_thumb_{timestamp}.jpg"
    
    reel_path = os.path.join(REELS_DIR, output_filename)
    thumb_path = os.path.join(THUMB_DIR, thumb_filename)

    # 1. Primary Attempt: Anti-Copyright Mirror Flip + 1.15x Speed + Color Boost + 9:16 Canvas Overlay
    filter_complex = (
        "[0:v]setpts=PTS/1.15,hflip,split=2[in_bg][in_fg];"
        "[in_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
        "[in_fg]scale=1080:1920:force_original_aspect_ratio=decrease,eq=contrast=1.06:brightness=0.02:saturation=1.12[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v]"
    )

    cmd_edit = [
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-i", raw_video_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-filter:a", "atempo=1.15,volume=1.05",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-max_muxing_queue_size", "1024",
        reel_path
    ]

    err_msg = ""
    try:
        process = subprocess.run(cmd_edit, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
            err_msg = process.stderr.decode("utf-8", errors="ignore")[-350:]
    except Exception as e:
        err_msg = str(e)

    # 2. Fallback Attempt: Universal pad filter with Anti-Copyright Shield
    if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
        print(f"Primary vertical edit failed ({err_msg}), using robust fallback vertical pad with Anti-Copyright Shield...")
        cmd_fallback = [
            "ffmpeg", "-y",
            "-fflags", "+genpts",
            "-i", raw_video_path,
            "-vf", "setpts=PTS/1.15,hflip,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,eq=contrast=1.06:brightness=0.02:saturation=1.12,setsar=1,format=yuv420p",
            "-filter:a", "atempo=1.15,volume=1.05",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-max_muxing_queue_size", "1024",
            reel_path
        ]
        try:
            process_fb = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
                err_msg = process_fb.stderr.decode("utf-8", errors="ignore")[-350:]
        except Exception as e:
            err_msg = str(e)

    # 3. Ultimate Fallback (No-Audio safe fallback with Anti-Copyright Shield)
    if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
        print(f"Fallback editor failed ({err_msg}), using safe video-only vertical pad...")
        cmd_ultimate = [
            "ffmpeg", "-y",
            "-fflags", "+genpts",
            "-i", raw_video_path,
            "-vf", "setpts=PTS/1.15,hflip,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,eq=contrast=1.06:brightness=0.02:saturation=1.12,setsar=1,format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
            "-pix_fmt", "yuv420p",
            "-an",
            reel_path
        ]
        try:
            process_ult = subprocess.run(cmd_ultimate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
                err_ult = process_ult.stderr.decode("utf-8", errors="ignore")[-350:]
                return False, "", "", f"Reel conversion failed completely: {err_ult}"
        except Exception as e:
            return False, "", "", f"Ultimate fallback error: {str(e)}"

    # Generate 9:16 vertical thumbnail
    cmd_thumb = [
        "ffmpeg", "-y",
        "-ss", "1",
        "-i", reel_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]
    try:
        subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if not os.path.exists(thumb_path):
            cmd_thumb_fb = ["ffmpeg", "-y", "-i", reel_path, "-vframes", "1", "-q:v", "2", thumb_path]
            subprocess.run(cmd_thumb_fb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    except Exception:
        pass

    return True, reel_path, thumb_path, ""
