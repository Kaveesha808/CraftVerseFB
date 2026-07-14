import sys
import os
import time
from datetime import datetime

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import stream_recorder as recorder
import video_editor as editor
import ai_caption_agent as ai_agent
import fb_uploader as fb
import content_detector as detector

def run_single_auto_reel_job():
    """
    Standalone runner designed for GitHub Actions / Cron Scheduled Tasks (3x per day).
    Captures live HLS -> Checks for Ads -> Converts 9:16 -> Groq AI Caption -> FB Upload.
    """
    print("=" * 60)
    print(f"🚀 Starting Standalone Auto Reel Job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    stream_url = os.environ.get("STREAM_URL", "https://soul-5mincrafteng-rakuten.amagi.tv/playlist.m3u8")
    clip_duration = int(os.environ.get("CLIP_DURATION", "45"))
    header_text = os.environ.get("HEADER_TEXT", "🔥 CRAZY 5-MIN DIY HACK 💡")
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    fb_token = os.environ.get("FB_ACCESS_TOKEN", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    max_attempts = 5
    success_capture = False
    raw_path, thumb_path = "", ""

    # Step 1 & 1.5: Capture and Ad Check Loop
    for attempt in range(1, max_attempts + 1):
        print(f"\n[Step 1] Capturing Live HLS Stream (Attempt {attempt}/{max_attempts})...")
        ok_rec, raw_path, thumb_path, err = recorder.record_hls_clip(stream_url, duration_seconds=clip_duration)
        if not ok_rec:
            print(f"⚠️ Capture attempt {attempt} failed: {err}. Retrying in 10s...")
            time.sleep(10)
            continue

        print("[Step 1.5] Running AI Smart Quality & Ad Check...")
        is_valid_craft, skip_reason = detector.is_valid_craft_clip(raw_path, thumb_path, gemini_api_key=gemini_key)
        if is_valid_craft:
            print("✅ Valid DIY Craft content detected!")
            success_capture = True
            break
        else:
            print(f"🛑 Ad/Break detected ({skip_reason}). Waiting 30s to catch real craft segment...")
            time.sleep(30)

    if not success_capture:
        print("❌ FATAL: Could not capture a valid DIY clip after multiple retries. Exiting.")
        sys.exit(1)

    # Step 2: Convert to 9:16 Vertical Reel
    print("\n[Step 2] Converting to 9:16 Vertical Reel ('Supiri Edit')...")
    ok_edit, reel_path, reel_thumb, err_edit = editor.create_vertical_reel(raw_path, header_text=header_text)
    if not ok_edit:
        print(f"❌ FATAL: Video conversion failed: {err_edit}")
        sys.exit(1)
    print(f"✅ Vertical Reel generated successfully: {reel_path}")

    # Step 3: AI Copywriter (Groq Llama 3.3 70B)
    print("\n[Step 3] Generating 100% English Viral Hook, Caption & Hashtags via Groq Llama 3.3 70B...")
    captions = ai_agent.generate_viral_captions(
        groq_api_key=groq_key,
        groq_model=groq_model,
        gemini_api_key=gemini_key,
        thumbnail_path=reel_thumb
    )
    print(f"📌 Title: {captions['title']}")
    print(f"📝 Caption: {captions['caption_en']}")
    print(f"🏷️ Hashtags: {captions['hashtags']}")

    # Step 4: Upload to Facebook Page
    if fb_page_id and fb_token:
        print(f"\n[Step 4] Uploading Reel to Facebook Page ID: {fb_page_id}...")
        ok_fb, fb_id, fb_url, fb_err = fb.upload_reel_to_fb_page(
            reel_path, fb_page_id, fb_token,
            captions["caption_en"], "", captions["hashtags"]
        )
        if ok_fb:
            print(f"🎉 SUCCESS! Published to Facebook Page! Reel ID: {fb_id}")
            print(f"🔗 FB Post URL: {fb_url}")
        else:
            print(f"❌ Facebook Upload Failed: {fb_err}")
            sys.exit(1)
    else:
        print("\n⚠️ Note: FB_PAGE_ID and/or FB_ACCESS_TOKEN not set. Skipping Facebook Auto-Upload.")
        print("To enable auto-upload in GitHub Actions, add FB_PAGE_ID and FB_ACCESS_TOKEN to your repository Secrets!")

    print("\n✅ Standalone Job Completed Successfully!")

if __name__ == "__main__":
    run_single_auto_reel_job()
