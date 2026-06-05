"""
Smart Room Monitor ─ config.py
All tunable settings live here. Edit once, works everywhere.
"""
import os

# ── Groq API ──────────────────────────────────────────────────────────────
# Set your key via environment variable:  export GROQ_API_KEY="gsk_..."
# Or paste it directly here (not recommended for shared code).
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
# Alternatives: "llama-3.2-90b-vision-preview"  (slower, more accurate)
# Check https://console.groq.com/docs/vision for the current model list.

# ── Timing (seconds) ──────────────────────────────────────────────────────
DETECTION_INTERVAL = 10   # How often to send a frame to the Groq API
HOMEWORK_REMINDER  = 30   # Fire the homework reminder after this many seconds
AUDIO_COOLDOWN     = 30   # Minimum gap between the same audio event re-firing

# ── Audio file paths ──────────────────────────────────────────────────────
# Place your MP3 files in the  audio/  folder next to this file,
# named exactly as shown below (or change these paths to match yours).
_AUDIO_DIR     = os.path.join(os.path.dirname(__file__), "audio")
AUDIO_WELCOME    = os.path.join(_AUDIO_DIR, "welcome.mp3")
AUDIO_WARNING    = os.path.join(_AUDIO_DIR, "warning.mp3")
AUDIO_CLEAN_ROOM = os.path.join(_AUDIO_DIR, "clean_room.mp3")
AUDIO_HOMEWORK   = os.path.join(_AUDIO_DIR, "homework.mp3")

# ── Webcam ────────────────────────────────────────────────────────────────
CAMERA_INDEX  = 0           # 0 = default laptop webcam
CAMERA_WIDTH  = 1280
CAMERA_HEIGHT = 720
