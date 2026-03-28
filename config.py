import os
from dotenv import load_dotenv
from pathlib import Path

LOOP_INTERVAL        = 10  # seconds between actions
MAX_LOOPS            = 99999
SUMMARY_EVERY        = 20  # summarize every N steps
RECENT_ACTIONS_KEEP  = 10  # how many recent actions to always include verbatim
LOOP_DETECT_WINDOW   = 5   # how many similar clicks before nudging model
MAX_CONSECUTIVE_WAIT = 3   # auto Escape after this many waits in a row

load_dotenv()

STEAMDECK_HOST = os.getenv("STEAMDECK_HOST")
STEAMDECK_USER = os.getenv("STEAMDECK_USER")
STEAMDECK_PASSWORD = os.getenv("STEAMDECK_PASSWORD")

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
REMOTE_SCREENSHOT_PATH = "/tmp/bg3_screenshot.png"
LOCAL_SCREENSHOT_PATH  = LOG_DIR / "latest.jpg"
OVERLAY_REMOTE_PATH    = "/tmp/bg3_overlay.txt"
STATE_FILE = LOG_DIR / "state.json"
FEEDBACK_FILE = Path("feedback.txt")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ACTION_MODEL  = "gemini-3-flash-preview"
SUMMARY_MODEL = "gemini-3-flash-preview"