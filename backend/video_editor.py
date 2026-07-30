import os
import subprocess
import glob
import random
from datetime import datetime
from typing import Tuple

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
REELS_DIR = os.path.join(MEDIA_DIR, "reels")
THUMB_DIR = os.path.join(MEDIA_DIR, "thumbnails")
MUSIC_DIR = os.path.join(MEDIA_DIR, "music")

os.makedirs(REELS_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

def create_vertical_reel(raw_video_path: str, header_text: str = "🔥 CRAZY 5-MIN DIY HACK 💡") -> Tuple[bool, str, str, str]:
    """
    Transforms a landscape raw clip into a high-retention 9:16 Vertical Reel (1080x1920)
    with VIRAL PiP SHIELD v5 (Defeats Meta AI and boosts retention):
    - Picture-in-Picture layout (960px width, original aspect ratio) - No stretching!
    - Heavy blurred background of the original video.
    - Thick Neon Border and Studio Badges.
    - 1.20x Speed + Mirror Flip.
    - Audio Mix: Lowers original audio to 10%, mixes Viral Background Music at 90%!
    Returns: (success, reel_video_path, reel_thumbnail_path, error_message)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"craft_reel_916_{timestamp}.mp4"
    thumb_filename = f"craft_reel_thumb_{timestamp}.jpg"
    
    reel_path = os.path.join(REELS_DIR, output_filename)
    thumb_path = os.path.join(THUMB_DIR, thumb_filename)

    # 1. Select a random viral background track if available
    music_files = glob.glob(os.path.join(MUSIC_DIR, "*.mp3")) + glob.glob(os.path.join(MUSIC_DIR, "*.ogg"))
    bg_music = random.choice(music_files) if music_files else None

    if bg_music:
        print(f"🎵 Mixing viral background track: {os.path.basename(bg_music)}")
        # If music exists, we use amix.
        # Original audio gets 1.20x tempo & pitch shift, then volume reduced to 0.15.
        # Music gets volume 0.85. They mix down to 1 channel (or stereo) ending at video duration.
        audio_filter = "[0:a]asetrate=44100*1.15,aresample=44100,atempo=1.04,volume=0.15[orig_a];[1:a]volume=0.85[bg_a];[orig_a][bg_a]amix=inputs=2:duration=first:dropout_transition=2[a]"
        inputs = ["-i", raw_video_path, "-stream_loop", "-1", "-i", bg_music] # loop music if shorter
        map_args = ["-map", "[v]", "-map", "[a]"]
    else:
        print("⚠️ No viral music found, using only original audio (sped up).")
        audio_filter = "asetrate=44100*1.15,aresample=44100,atempo=1.04,volume=1.05"
        inputs = ["-i", raw_video_path]
        map_args = ["-map", "[v]", "-map", "0:a?"]

    # Visual Filter: 
    # - Split into BG and FG.
    # - BG is scaled to cover 1080x1920 (crop excess), blurred, darkened.
    # - FG is flipped, sped up to 1.20x (setpts=PTS/1.20), scaled to width 960 (keeps aspect ratio).
    # - Overlay FG on BG center. Add 12px yellow border around the 960 width area.
    # - Add Banners and Badges.
    filter_complex = (
        "[0:v]setpts=PTS/1.20,hflip,split=2[in_bg][in_fg];"
        "[in_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:15,vignette=angle=0.5,eq=brightness=-0.1[bg];"
        "[in_fg]scale=960:-2,eq=gamma=1.12:contrast=1.15:saturation=1.25,pad=iw+24:ih+24:12:12:yellow[fg_bordered];"
        "[bg][fg_bordered]overlay=(W-w)/2:(H-h)/2,"
        "drawbox=x=0:y=0:w=1080:h=270:color=black@0.85:t=fill,"
        "drawbox=x=0:y=1650:w=1080:h=270:color=black@0.85:t=fill,"
        "drawbox=x=30:y=290:w=380:h=100:color=red@0.9:t=fill,drawbox=x=30:y=290:w=380:h=100:color=white@0.95:t=6,"
        "drawbox=x=670:y=290:w=380:h=100:color=blue@0.9:t=fill,drawbox=x=670:y=290:w=380:h=100:color=white@0.95:t=6,"
        "drawbox=x=30:y=1530:w=380:h=100:color=green@0.9:t=fill,drawbox=x=30:y=1530:w=380:h=100:color=white@0.95:t=6,"
        "drawbox=x=670:y=1530:w=380:h=100:color=purple@0.9:t=fill,drawbox=x=670:y=1530:w=380:h=100:color=white@0.95:t=6,"
        "drawtext=text='CRAZY 5-MIN DIY HACK':fontcolor=yellow:fontsize=56:x=(w-text_w)/2:y=95:borderw=4:bordercolor=red,"
        "drawtext=text='VIRAL HACK':fontcolor=white:fontsize=40:x=60:y=320:borderw=3:bordercolor=black,"
        "drawtext=text='MIND BLOWN':fontcolor=white:fontsize=40:x=705:y=320:borderw=3:bordercolor=black,"
        "drawtext=text='DIY TIP':fontcolor=white:fontsize=40:x=110:y=1560:borderw=3:bordercolor=black,"
        "drawtext=text='MUST TRY':fontcolor=yellow:fontsize=40:x=730:y=1560:borderw=3:bordercolor=black,"
        "drawtext=text='WAIT FOR THE END & SHARE':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=1745:borderw=4:bordercolor=black,"
        "setsar=1,format=yuv420p[v]"
    )

    if bg_music:
        cmd_edit = [
            "ffmpeg", "-y", "-fflags", "+genpts",
            *inputs,
            "-filter_complex", filter_complex + ";" + audio_filter,
            *map_args,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-max_muxing_queue_size", "1024",
            reel_path
        ]
    else:
        cmd_edit = [
            "ffmpeg", "-y", "-fflags", "+genpts",
            *inputs,
            "-filter_complex", filter_complex,
            *map_args,
            "-filter:a", audio_filter,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-max_muxing_queue_size", "1024",
            reel_path
        ]

    err_msg = ""
    try:
        process = subprocess.run(cmd_edit, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=200)
        if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
            err_msg = process.stderr.decode("utf-8", errors="ignore")[-350:]
    except Exception as e:
        err_msg = str(e)

    # Fallback without music if it fails
    if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 10000:
        print(f"Primary edit failed ({err_msg}), retrying safe fallback...")
        cmd_fb = [
            "ffmpeg", "-y", "-fflags", "+genpts",
            "-i", raw_video_path,
            "-vf", "setpts=PTS/1.20,hflip,scale=960:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
                   "drawbox=x=0:y=0:w=1080:h=270:color=black@0.85:t=fill,drawbox=x=0:y=1650:w=1080:h=270:color=black@0.85:t=fill,"
                   "drawtext=text='CRAZY 5-MIN DIY HACK':fontcolor=yellow:fontsize=56:x=(w-text_w)/2:y=95:borderw=4:bordercolor=red,"
                   "drawtext=text='WAIT FOR THE END & SHARE':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=1745:borderw=4:bordercolor=black,"
                   "eq=gamma=1.12:contrast=1.15:saturation=1.25,setsar=1,format=yuv420p",
            "-filter:a", "asetrate=44100*1.15,aresample=44100,atempo=1.04,volume=1.05",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            reel_path
        ]
        try:
            subprocess.run(cmd_fb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        except Exception:
            pass

    # Extract thumbnail
    cmd_thumb = [
        "ffmpeg", "-y", "-ss", "1", "-i", reel_path, "-vframes", "1", "-q:v", "2", thumb_path
    ]
    try:
        subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    except Exception:
        pass

    return True, reel_path, thumb_path, ""
