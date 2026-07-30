import os
import subprocess

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
MUSIC_DIR = os.path.join(MEDIA_DIR, "music")
os.makedirs(MUSIC_DIR, exist_ok=True)

def generate_viral_beats():
    print(f"Checking for Viral Background Music in {MUSIC_DIR}...")
    
    # We use FFmpeg to dynamically synthesize royalty-free ambient electronic / lo-fi beats!
    # This guarantees 100% copyright safety and works completely offline without 503 errors.
    
    tracks = [
        {
            "name": "viral_lofi_beat.mp3",
            "filter": "anoisesrc=d=45:c=brown:r=44100:a=0.5,aphaser=type=t:speed=1.5:decay=0.4,tremolo=f=5.0:d=0.7"
        },
        {
            "name": "viral_electronic_drone.mp3",
            "filter": "sine=f=80:d=45,aecho=0.8:0.9:1000|1500:0.3|0.2,aphaser=type=t:speed=0.5:decay=0.8"
        },
        {
            "name": "viral_phonk_bass.mp3",
            "filter": "sine=f=60:d=45,tremolo=f=8.0:d=0.9,aecho=0.8:0.8:500:0.5"
        }
    ]
    
    for track in tracks:
        filepath = os.path.join(MUSIC_DIR, track["name"])
        if not os.path.exists(filepath):
            print(f"Synthesizing viral track: {track['name']}...")
            try:
                cmd = [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", track["filter"],
                    "-c:a", "libmp3lame", "-b:a", "128k", filepath
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
                if os.path.exists(filepath):
                    print(f"Successfully generated {track['name']}!")
            except Exception as e:
                print(f"Failed to generate {track['name']}: {e}")
        else:
            print(f"Track {track['name']} already exists.")

if __name__ == "__main__":
    generate_viral_beats()
