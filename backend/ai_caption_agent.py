import os
import json
import random
import urllib.request
from typing import Dict, Any

# Viral 100% English templates for 5-Minute Crafts & DIY hacks
VIRAL_ENG_CAPTIONS = [
    "WAIT FOR IT... 😱 You won't believe how easy this 5-Minute Craft secret is! Try this hack at home today and let us know how it goes! 🔥💡👇",
    "Did you know this genius life hack?! 🤯 Save time and money with this super easy DIY trick! Which one is your favorite? Drop a comment below! 👇✨",
    "Mind = Blown! 💥 Never do it the hard way again after watching this 5-minute hack! Share this Reel with a friend who needs this right now! ❤️🛠️",
    "The ultimate life hack you didn't know you needed! 😍 Watch till the very end for the surprising result! Don't forget to follow for daily DIY hacks! 🔥✨",
    "Genius 5-minute DIY idea that actually works! 💡 Try this simple household trick today! Drop a 🔥 emoji if you love creative hacks!"
]

VIRAL_HASHTAG_PACKS = [
    "#5MinuteCrafts #DIY #LifeHacks #ViralReels #Crafts #UsefulTips #Handmade #TrendingNow #ReelsFB #FYP #DailyHacks #Ideas",
    "#DIYHacks #5MinCrafts #LifeHack #ViralVideo #Crafting #CreativeIdeas #TipsAndTricks #ReelsViral #FacebookReels #Handcraft #SmartHacks",
    "#GeniusHacks #DIYProjects #5MinuteCraft #ViralReelsFB #HomeHacks #UsefulIdeas #LifeHacksDaily #CraftIdeas #FYPReels #TrendingReels"
]

DEFAULT_GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
DEFAULT_GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

def generate_viral_captions(groq_api_key: str = "", groq_model: str = "", gemini_api_key: str = "", thumbnail_path: str = "") -> Dict[str, str]:
    """
    Generates high-engagement 100% English Facebook Reels captions and viral hashtags.
    Prioritizes Groq API (Llama 3.3 70B), falls back to Gemini API or high-converting English copy templates.
    """
    api_key = groq_api_key.strip() if groq_api_key else DEFAULT_GROQ_KEY
    model = groq_model.strip() if groq_model else DEFAULT_GROQ_MODEL

    # 1. Try Groq API (Blazingly fast & smart Llama 3.3 70B)
    if api_key and len(api_key) > 10:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            prompt = (
                "You are an expert social media manager for a viral DIY & 5-Minute Crafts Facebook Page. "
                "Generate a JSON object with keys: 'title', 'caption_en', 'hashtags'. "
                "'title': short punchy 4-6 word uppercase title with emojis (e.g. 🔥 CRAZY 5-MIN DIY HACK 💡). "
                "'caption_en': exciting 100% English Facebook Reel caption with a strong hook, curiosity gap, and call to action. "
                "'hashtags': string of 12 top viral DIY & Lifehacks hashtags starting with #5MinuteCrafts. "
                "Do NOT include any non-English text. Return valid JSON only."
            )
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "response_format": {"type": "json_object"}
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"]
                parsed = json.loads(text)
                return {
                    "title": parsed.get("title", "🔥 GENIUS 5-MIN DIY HACK 💡"),
                    "caption_en": parsed.get("caption_en", random.choice(VIRAL_ENG_CAPTIONS)),
                    "caption_si": "",
                    "hashtags": parsed.get("hashtags", random.choice(VIRAL_HASHTAG_PACKS))
                }
        except Exception as e:
            print(f"Groq API fallback triggered: {e}")

    # 2. Try Gemini API if present
    if gemini_api_key and len(gemini_api_key.strip()) > 10:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key.strip()}"
            prompt = (
                "Generate a JSON object with keys: 'title', 'caption_en', 'hashtags' for a 5-Minute Crafts DIY hack Facebook Reel. "
                "100% English only. Return raw JSON."
            )
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.8}
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                text_clean = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text_clean)
                return {
                    "title": parsed.get("title", "🔥 GENIUS 5-MIN DIY HACK 💡"),
                    "caption_en": parsed.get("caption_en", random.choice(VIRAL_ENG_CAPTIONS)),
                    "caption_si": "",
                    "hashtags": parsed.get("hashtags", random.choice(VIRAL_HASHTAG_PACKS))
                }
        except Exception as e:
            print(f"Gemini API fallback triggered: {e}")

    # 3. Fast High-Converting English Templates Fallback
    return {
        "title": "🔥 GENIUS 5-MIN DIY HACK 💡",
        "caption_en": random.choice(VIRAL_ENG_CAPTIONS),
        "caption_si": "",
        "hashtags": random.choice(VIRAL_HASHTAG_PACKS)
    }
