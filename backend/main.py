import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import database as db
import stream_recorder as recorder
import video_editor as editor
import ai_caption_agent as ai_agent
import fb_uploader as fb
import content_detector as detector

app = FastAPI(title="CraftReel AI Agent - 5-Minute Crafts FB Reels System")

# Ensure media directory exists
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# Mount media directory so frontend can play preview videos and thumbnails
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# --- Agent Background Thread State ---
AGENT_RUNNING = False
AGENT_TASK_THREAD = None

class SettingsModel(BaseModel):
    stream_url: str
    clip_duration: str
    header_text: str
    auto_upload: str
    fb_page_id: str
    fb_access_token: str
    gemini_api_key: Optional[str] = ""
    groq_api_key: Optional[str] = ""
    groq_model: Optional[str] = "llama-3.3-70b-versatile"
    daily_target_videos: Optional[str] = "3"
    agent_schedule_interval_minutes: str
    agent_enabled: str

class CaptionEditModel(BaseModel):
    caption_en: str
    caption_si: str
    hashtags: str

def execute_reels_pipeline_job(job_id: int):
    """
    Executes the full AI automated pipeline with Auto-Retry (Never stop on Ad/Break!):
    1. Capture HLS live stream
    1.5 Smart Check: Verify not an Ad or broken stream -> If Ad/Break, wait 20s and automatically retry!
    2. Convert to 9:16 Vertical Reel ("Supiri Edit")
    3. Generate AI viral 100% English caption & hashtags via Groq Llama 3.3 70B
    4. Auto-upload to FB Page if configured
    """
    try:
        settings = db.get_all_settings()
        stream_url = settings.get("stream_url", "https://soul-5mincrafteng-rakuten.amagi.tv/playlist.m3u8")
        duration = int(settings.get("clip_duration", "45"))
        header_text = settings.get("header_text", "🔥 CRAZY 5-MIN DIY HACK 💡")
        auto_upload = (settings.get("auto_upload", "false").lower() == "true")
        fb_page_id = settings.get("fb_page_id", "")
        fb_token = settings.get("fb_access_token", "")
        gemini_key = settings.get("gemini_api_key", "")
        groq_key = settings.get("groq_api_key", os.environ.get("GROQ_API_KEY", ""))
        groq_model = settings.get("groq_model", os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"))

        # Step 1 & 1.5: Capture Live Stream with Auto-Retry loop to avoid Ads / Commercial Breaks
        max_attempts = 4
        success = False
        raw_path, thumb_path = "", ""
        for attempt in range(1, max_attempts + 1):
            db.update_job(
                job_id, "running", 15 + (attempt * 5),
                f"Capturing Live Stream (Attempt {attempt}/{max_attempts})",
                f"Recording {duration}s from 5-Minute Crafts HLS feed..."
            )
            ok_rec, raw_path, thumb_path, err = recorder.record_hls_clip(stream_url, duration_seconds=duration)
            if not ok_rec:
                time.sleep(10)
                continue

            db.update_job(job_id, "running", 35, "AI Content Quality Check", "Checking clip for advertisements or stream breaks...")
            is_valid_craft, skip_reason = detector.is_valid_craft_clip(raw_path, thumb_path, gemini_api_key=gemini_key)
            if is_valid_craft:
                success = True
                break
            else:
                db.update_job(
                    job_id, "running", 35,
                    "Ad/Break Detected -> Retrying",
                    f"Attempt {attempt} caught Ad/Break ({skip_reason}). Waiting 25s for live DIY craft segment..."
                )
                time.sleep(25)

        if not success:
            db.update_job(job_id, "error", 0, "Recording Failed", "Could not capture a non-ad DIY stream segment after retries.")
            return

        # Step 2: Convert to 9:16 Vertical Reel ("Supiri Edit")
        db.update_job(job_id, "running", 55, "AI Video Editor", "Converting to 9:16 Vertical Reel with blurred split-screen & color grading...")
        success_edit, reel_path, reel_thumb, err_edit = editor.create_vertical_reel(raw_path, header_text=header_text)
        if not success_edit:
            db.update_job(job_id, "error", 0, "Video Edit Failed", f"FFmpeg Editor Error: {err_edit}")
            return

        # Step 3: AI Viral Caption & Hashtags (100% English via Groq Llama 3.3 70B)
        db.update_job(job_id, "running", 75, "AI Copywriter (Groq Llama 3.3 70B)", "Generating viral 100% English caption + #hashtags...")
        captions = ai_agent.generate_viral_captions(
            groq_api_key=groq_key,
            groq_model=groq_model,
            gemini_api_key=gemini_key,
            thumbnail_path=reel_thumb
        )

        # Save Reel to DB
        reel_id = db.create_reel(
            title=captions["title"],
            video_path=reel_path,
            thumbnail_path=reel_thumb,
            caption_en=captions["caption_en"],
            caption_si=captions["caption_si"],
            hashtags=captions["hashtags"],
            header_text=header_text
        )

        # Step 4: Facebook Page Auto-Upload (if enabled)
        fb_msg = "Reel generated & saved to queue!"
        if auto_upload and fb_page_id and fb_token:
            db.update_job(job_id, "running", 90, "Uploading to Facebook Page", "Publishing Reel to Facebook Page via Graph API...")
            fb_ok, fb_vid_id, fb_url, fb_err = fb.upload_reel_to_fb_page(
                reel_path, fb_page_id, fb_token,
                captions["caption_en"], captions["caption_si"], captions["hashtags"]
            )
            if fb_ok:
                db.update_reel_status(reel_id, "published", fb_video_id=fb_vid_id, fb_post_url=fb_url)
                fb_msg = f"Auto-uploaded successfully to Facebook Page! (ID: {fb_vid_id})"
            else:
                db.update_reel_status(reel_id, "ready")
                fb_msg = f"Reel ready. Auto-upload failed or pending: {fb_err}"

        db.update_job(
            job_id, "completed", 100, "Done",
            fb_msg,
            result_json=f'{{"reel_id": {reel_id}}}'
        )

    except Exception as exc:
        db.update_job(job_id, "error", 0, "Pipeline Error", f"Unexpected error: {str(exc)}")

def autonomous_agent_loop():
    """
    Background worker thread that triggers Reel generation at the scheduled interval when agent is enabled.
    """
    global AGENT_RUNNING
    while AGENT_RUNNING:
        try:
            settings = db.get_all_settings()
            enabled = (settings.get("agent_enabled", "false").lower() == "true")
            if enabled:
                # Check if a job is currently running
                latest = db.get_latest_job()
                if not latest or latest["status"] != "running":
                    job_id = db.create_job("agent_auto_reel", "Starting Autonomous Agent Cycle")
                    execute_reels_pipeline_job(job_id)
            
            interval_mins = int(settings.get("agent_schedule_interval_minutes", "60"))
            time.sleep(max(60, interval_mins * 60))
        except Exception:
            time.sleep(60)

# --- REST APIs ---

@app.get("/api/status")
def get_system_status():
    latest_job = db.get_latest_job()
    settings = db.get_all_settings()
    reels = db.get_reels(limit=5)
    return {
        "agent_enabled": (settings.get("agent_enabled", "false").lower() == "true"),
        "latest_job": latest_job,
        "recent_reels_count": len(db.get_reels(limit=1000)),
        "stream_url": settings.get("stream_url", "")
    }

@app.get("/api/settings")
def get_settings():
    return db.get_all_settings()

@app.post("/api/settings")
def save_settings(settings: SettingsModel):
    db.set_setting("stream_url", settings.stream_url)
    db.set_setting("clip_duration", settings.clip_duration)
    db.set_setting("header_text", settings.header_text)
    db.set_setting("auto_upload", settings.auto_upload)
    db.set_setting("fb_page_id", settings.fb_page_id)
    db.set_setting("fb_access_token", settings.fb_access_token)
    db.set_setting("gemini_api_key", settings.gemini_api_key or "")
    db.set_setting("groq_api_key", settings.groq_api_key or "")
    db.set_setting("groq_model", settings.groq_model or "")
    db.set_setting("daily_target_videos", settings.daily_target_videos or "3")
    db.set_setting("agent_schedule_interval_minutes", settings.agent_schedule_interval_minutes)
    db.set_setting("agent_enabled", settings.agent_enabled)
    return {"status": "success", "message": "Settings updated successfully"}

@app.post("/api/settings/test-fb")
def test_facebook_connection(payload: Dict[str, str]):
    page_id = payload.get("fb_page_id", "")
    token = payload.get("fb_access_token", "")
    ok, result = fb.verify_fb_token(page_id, token)
    return {"valid": ok, "message": result}

@app.get("/api/reels")
def list_reels():
    reels = db.get_reels(limit=50)
    # Enrich paths to relative media URL
    for r in reels:
        if r.get("video_path"):
            r["video_url"] = "/media/reels/" + os.path.basename(r["video_path"])
        if r.get("thumbnail_path"):
            r["thumb_url"] = "/media/thumbnails/" + os.path.basename(r["thumbnail_path"])
    return reels

@app.get("/api/reels/{reel_id}")
def get_reel_detail(reel_id: int):
    reel = db.get_reel(reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    if reel.get("video_path"):
        reel["video_url"] = "/media/reels/" + os.path.basename(reel["video_path"])
    if reel.get("thumbnail_path"):
        reel["thumb_url"] = "/media/thumbnails/" + os.path.basename(reel["thumbnail_path"])
    return reel

@app.put("/api/reels/{reel_id}")
def update_reel(reel_id: int, payload: CaptionEditModel):
    db.update_reel_captions(reel_id, payload.caption_en, payload.caption_si, payload.hashtags)
    return {"status": "success"}

@app.delete("/api/reels/{reel_id}")
def delete_reel_by_id(reel_id: int):
    reel = db.get_reel(reel_id)
    if reel:
        try:
            if reel.get("video_path") and os.path.exists(reel["video_path"]):
                os.remove(reel["video_path"])
            if reel.get("thumbnail_path") and os.path.exists(reel["thumbnail_path"]):
                os.remove(reel["thumbnail_path"])
        except Exception:
            pass
        db.delete_reel(reel_id)
    return {"status": "deleted"}

@app.post("/api/reels/generate-now")
def trigger_reel_generation(background_tasks: BackgroundTasks):
    latest = db.get_latest_job()
    if latest and latest["status"] == "running":
        return {"status": "busy", "message": "A Reel generation job is already in progress!"}
    
    job_id = db.create_job("manual_generate", "Starting Reel Generation Pipeline")
    background_tasks.add_task(execute_reels_pipeline_job, job_id)
    return {"status": "started", "job_id": job_id, "message": "Pipeline job initiated!"}

@app.post("/api/reels/{reel_id}/publish")
def publish_reel_now(reel_id: int):
    reel = db.get_reel(reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    settings = db.get_all_settings()
    page_id = settings.get("fb_page_id", "")
    token = settings.get("fb_access_token", "")
    
    ok, fb_vid_id, fb_url, err = fb.upload_reel_to_fb_page(
        reel["video_path"], page_id, token,
        reel["caption_en"], reel["caption_si"], reel["hashtags"]
    )
    if ok:
        db.update_reel_status(reel_id, "published", fb_video_id=fb_vid_id, fb_post_url=fb_url)
        return {"status": "success", "fb_video_id": fb_vid_id, "post_url": fb_url}
    else:
        return {"status": "error", "message": err}

@app.post("/api/agent/toggle")
def toggle_autonomous_agent():
    global AGENT_RUNNING, AGENT_TASK_THREAD
    settings = db.get_all_settings()
    current = (settings.get("agent_enabled", "false").lower() == "true")
    new_state = not current
    db.set_setting("agent_enabled", "true" if new_state else "false")
    
    if new_state and not AGENT_RUNNING:
        AGENT_RUNNING = True
        AGENT_TASK_THREAD = threading.Thread(target=autonomous_agent_loop, daemon=True)
        AGENT_TASK_THREAD.start()
    elif not new_state:
        AGENT_RUNNING = False
        
    return {"agent_enabled": new_state, "message": f"Autonomous agent {'ENABLED' if new_state else 'DISABLED'}."}

# Serve Frontend static application
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{filename}")
def serve_frontend_files(filename: str):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
