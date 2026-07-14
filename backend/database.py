import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "craftreel.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Reels table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            video_path TEXT,
            thumbnail_path TEXT,
            caption_en TEXT,
            caption_si TEXT,
            hashtags TEXT,
            header_text TEXT,
            status TEXT DEFAULT 'ready',
            fb_video_id TEXT,
            fb_post_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT,
            status TEXT,
            progress INTEGER DEFAULT 0,
            step_name TEXT,
            message TEXT,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Default settings
    default_settings = {
        "stream_url": "https://soul-5mincrafteng-rakuten.amagi.tv/playlist.m3u8",
        "clip_duration": "45",
        "header_text": "🔥 CRAZY 5-MIN DIY HACK 💡",
        "auto_upload": "false",
        "fb_page_id": "",
        "fb_access_token": "",
        "gemini_api_key": "",
        "groq_api_key": os.environ.get("GROQ_API_KEY", ""),
        "groq_model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "daily_target_videos": "3",
        "agent_schedule_interval_minutes": "60",
        "agent_enabled": "false"
    }

    for key, val in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

# --- Reels Operations ---
def create_reel(title: str, video_path: str, thumbnail_path: str, caption_en: str, caption_si: str, hashtags: str, header_text: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reels (title, video_path, thumbnail_path, caption_en, caption_si, hashtags, header_text, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ready')
    """, (title, video_path, thumbnail_path, caption_en, caption_si, hashtags, header_text))
    reel_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reel_id

def get_reels(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reels ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_reel(reel_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reels WHERE id = ?", (reel_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_reel_status(reel_id: int, status: str, fb_video_id: str = "", fb_post_url: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reels 
        SET status = ?, fb_video_id = COALESCE(NULLIF(?,''), fb_video_id), fb_post_url = COALESCE(NULLIF(?,''), fb_post_url)
        WHERE id = ?
    """, (status, fb_video_id, fb_post_url, reel_id))
    conn.commit()
    conn.close()

def update_reel_captions(reel_id: int, caption_en: str, caption_si: str, hashtags: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reels
        SET caption_en = ?, caption_si = ?, hashtags = ?
        WHERE id = ?
    """, (caption_en, caption_si, hashtags, reel_id))
    conn.commit()
    conn.close()

def delete_reel(reel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reels WHERE id = ?", (reel_id,))
    conn.commit()
    conn.close()

# --- Job Operations ---
def create_job(job_type: str, step_name: str = "Starting") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (job_type, status, progress, step_name, message)
        VALUES (?, 'running', 0, ?, 'Job initialized')
    """, (job_type, step_name))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

def update_job(job_id: int, status: str, progress: int, step_name: str, message: str, result_json: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs
        SET status = ?, progress = ?, step_name = ?, message = ?, result_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, progress, step_name, message, result_json, job_id))
    conn.commit()
    conn.close()

def get_latest_job() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Initialize db on module import
init_db()
