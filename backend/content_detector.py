import os
import subprocess
from typing import Tuple

def is_valid_craft_clip(video_path: str, thumbnail_path: str = "", gemini_api_key: str = "") -> Tuple[bool, str]:
    """
    Analyzes a recorded live stream clip across its ENTIRE duration (`0s to 45s`) to ensure it is NOT
    an advertisement, commercial break, black screen, frozen stream slate, or blue "WILL BE BACK SHORTLY" bumper.
    
    Returns: (is_valid: bool, reason: str)
    """
    if not os.path.exists(video_path):
        return False, "Video file does not exist."

    # 1. Check for black screen / broken stream using ffmpeg blackdetect
    cmd_black = [
        "ffmpeg", "-i", video_path,
        "-vf", "blackdetect=d=2.5:pix_th=0.10",
        "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd_black, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        stderr_txt = proc.stderr.decode("utf-8", errors="ignore")
        if "black_start:" in stderr_txt and "black_duration:" in stderr_txt:
            for line in stderr_txt.splitlines():
                if "black_duration:" in line:
                    parts = line.split("black_duration:")
                    if len(parts) > 1:
                        try:
                            dur = float(parts[1].split()[0])
                            if dur >= 3.0:
                                return False, f"Stream break / black screen detected ({dur:.1f}s black slate)"
                        except ValueError:
                            pass
    except Exception:
        pass

    # 2. Check for frozen/static screen across the clip (freezedetect)
    cmd_freeze = [
        "ffmpeg", "-i", video_path,
        "-vf", "freezedetect=n=-45dB:d=3",
        "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd_freeze, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        stderr_txt = proc.stderr.decode("utf-8", errors="ignore")
        if "freeze_start: " in stderr_txt and "freeze_duration: " in stderr_txt:
            return False, "Stream break / frozen static image detected"
    except Exception:
        pass

    # 3. Multi-Segment Luma/Chroma & Blue Slate Check ("WILL BE BACK SHORTLY" Bumper Detection across the full clip)
    # Check 4 time slices (at 3s, 14s, 26s, 36s) across the video so blue slates anywhere are caught immediately
    slices_to_check = [3, 14, 26, 36]
    for slice_sec in slices_to_check:
        cmd_signal = [
            "ffmpeg", "-ss", str(slice_sec),
            "-i", video_path,
            "-vf", "signalstat",
            "-vframes", "25",
            "-f", "null", "-"
        ]
        try:
            proc = subprocess.run(cmd_signal, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            stderr_txt = proc.stderr.decode("utf-8", errors="ignore")
            yvar_val = None
            uavg_val = None
            vavg_val = None
            for line in stderr_txt.splitlines():
                if "YVAR:" in line:
                    try:
                        yvar_val = float(line.split("YVAR:")[1].split()[0])
                    except ValueError:
                        pass
                if "UAVG:" in line:
                    try:
                        uavg_val = float(line.split("UAVG:")[1].split()[0])
                    except ValueError:
                        pass
                if "VAVG:" in line:
                    try:
                        vavg_val = float(line.split("VAVG:")[1].split()[0])
                    except ValueError:
                        pass

            # If Luma variance across frames is low (< 650), it is a graphic slate/bumper like "Will be back shortly"
            if yvar_val is not None and yvar_val < 650.0:
                return False, f"Bumper / Break slate detected at {slice_sec}s (WILL BE BACK SHORTLY or solid screen, variance={yvar_val:.1f})"
            
            # If dominant blue channel (`UAVG >> VAVG + 15` or high blue chroma) with moderate/low variance, it's Rakuten's blue break slate
            if uavg_val is not None and vavg_val is not None and (uavg_val - vavg_val) > 18.0 and (yvar_val is None or yvar_val < 1100.0):
                return False, f"Blue Bumper slate detected at {slice_sec}s (WILL BE BACK SHORTLY blue screen)"
        except Exception:
            pass

    # 4. Multi-Frame Local PIL Standard Deviation & Uniform Color Check
    # Extract multiple frames across the clip and check them locally
    try:
        from PIL import Image, ImageStat
        sample_times = [5, 18, 32]
        for st in sample_times:
            temp_img = f"{video_path}_sample_{st}.jpg"
            cmd_sample = ["ffmpeg", "-y", "-ss", str(st), "-i", video_path, "-vframes", "1", "-q:v", "3", temp_img]
            subprocess.run(cmd_sample, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if os.path.exists(temp_img):
                try:
                    img = Image.open(temp_img).convert("RGB")
                    stat = ImageStat.Stat(img)
                    stddev = stat.stddev
                    mean_rgb = stat.mean
                    # Cleanup sample image immediately
                    os.remove(temp_img)
                    # If RGB standard deviation across the image is small (< 36), it's a uniform/slate bumper
                    if max(stddev) < 36.0:
                        return False, f"Bumper / Break slate detected at {st}s (WILL BE BACK SHORTLY solid color screen)"
                    # Check for dominant blue slate (Blue mean >> Red/Green mean)
                    if mean_rgb[2] > (mean_rgb[0] + 25) and mean_rgb[2] > (mean_rgb[1] + 25) and max(stddev) < 55.0:
                        return False, f"Blue Bumper slate detected at {st}s (WILL BE BACK SHORTLY blue background)"
                except Exception:
                    if os.path.exists(temp_img):
                        try:
                            os.remove(temp_img)
                        except Exception:
                            pass
    except Exception:
        pass

    # 5. Check Thumbnail directly if PIL check passed
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            from PIL import Image, ImageStat
            img = Image.open(thumbnail_path).convert("RGB")
            stat = ImageStat.Stat(img)
            stddev = stat.stddev
            mean_rgb = stat.mean
            if max(stddev) < 36.0:
                return False, "Bumper / Break slate detected on thumbnail (WILL BE BACK SHORTLY solid color screen)"
            if mean_rgb[2] > (mean_rgb[0] + 25) and mean_rgb[2] > (mean_rgb[1] + 25) and max(stddev) < 55.0:
                return False, "Blue Bumper slate detected on thumbnail (WILL BE BACK SHORTLY blue background)"
        except Exception:
            pass

        # If Gemini API Key is configured, use Gemini Vision for deep visual check
        if gemini_api_key and len(gemini_api_key.strip()) > 10:
            try:
                import urllib.request
                import json
                import base64
                with open(thumbnail_path, "rb") as img_f:
                    img_b64 = base64.b64encode(img_f.read()).decode("utf-8")
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key.strip()}"
                prompt = (
                    "Look at this video frame from a live stream. Is this an advertisement, commercial break slate, "
                    "or channel offline banner like 'WILL BE BACK SHORTLY'? Or is it an actual DIY / craft / household hack demonstration? "
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
                pass

    # Clip passed quality, slate, & ad detection across all segments
    return True, "Valid DIY Craft Content"
