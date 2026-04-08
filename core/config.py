"""
core/config.py — MotionAI settings
"""

import os

USER_NAME    = "Allen"
DEFAULT_CITY = "Pune"

# ─── LLM / GROQ ─────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
LLM_MODEL        = "llama-3.1-8b-instant"
LLM_MAX_TOKENS   = 512
LLM_TEMPERATURE  = 0.7
COUNSELLOR_MODEL = "llama-3.1-8b-instant"
COUNSELLOR_TEMP  = 0.85

# ─── Weather API ────────────────────────────────────────────────────────────
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "YOUR_WEATHER_API_KEY_HERE")

# ─── News API ───────────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "YOUR_NEWSAPI_KEY_HERE")

# ─── Voice / TTS (ElevenLabs) ───────────────────────────────────────────────
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_API_KEY_HERE")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "YOUR_ELEVENLABS_VOICE_ID_HERE")

USE_ELEVENLABS = (
    ELEVENLABS_API_KEY  not in ("", "YOUR_ELEVENLABS_API_KEY_HERE") and
    ELEVENLABS_VOICE_ID not in ("", "YOUR_ELEVENLABS_VOICE_ID_HERE")
)

# ─── General Settings ───────────────────────────────────────────────────────
WAKE_PHRASE = "hello"
MIC_INDEX   = 2

TTS_ENGINE = "pyttsx3"
TTS_RATE   = 175
TTS_VOLUME = 0.95

GESTURE_CAMERA_INDEX = 0
GESTURE_SENSITIVITY  = 0.7
GESTURE_SCROLL_SPEED = 20

# ─── App Paths ──────────────────────────────────────────────────────────────
APP_PATHS = {
    "chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vscode":      r"C:\Users\{username}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "whatsapp":    r"C:\Users\{username}\AppData\Local\WhatsApp\WhatsApp.exe",
    "notepad":     "notepad.exe",
    "calculator":  "calc.exe",
    "explorer":    "explorer.exe",
    "paint":       "mspaint.exe",
    "spotify":     r"C:\Users\{username}\AppData\Roaming\Spotify\Spotify.exe",
    "vlc":         r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "discord":     r"C:\Users\{username}\AppData\Roaming\discord\Discord.exe",
    "teams":       r"C:\Users\{username}\AppData\Local\Microsoft\Teams\current\Teams.exe",
    "zoom":        r"C:\Users\{username}\AppData\Roaming\Zoom\bin\Zoom.exe",
    "wordpad":     "wordpad.exe",
    "apple_music": r"C:\Users\{username}\AppData\Local\Microsoft\WindowsApps\AppleMusic.exe",
}

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR  = os.path.join(ASSETS_DIR, "icons")