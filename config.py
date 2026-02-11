import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "data.db")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

# Legacy path for automatic migration
_LEGACY_DB_PATH = os.path.join(DATA_DIR, "mouse_activity.db")

# If input is idle for this many seconds, the session is closed
IDLE_THRESHOLD_SECONDS = 3

# Sessions shorter than this threshold (seconds) are discarded
MIN_SESSION_DURATION = 0.5

# Flask dashboard
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

# Default colors
COLOR_MOUSE = "#4CAF50"
COLOR_KEYBOARD = "#42A5F5"
COLOR_CUMULATIVE = "#E0E0E0"

_DEFAULT_SETTINGS = {
    "idle_threshold": IDLE_THRESHOLD_SECONDS,
    "color_mouse": COLOR_MOUSE,
    "color_keyboard": COLOR_KEYBOARD,
    "color_cumulative": COLOR_CUMULATIVE,
}


def load_settings():
    settings = dict(_DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r") as f:
            saved = json.load(f)
        settings.update(saved)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return settings


def save_settings(settings):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def get_idle_threshold():
    return IDLE_THRESHOLD_SECONDS


def set_idle_threshold(value):
    global IDLE_THRESHOLD_SECONDS
    IDLE_THRESHOLD_SECONDS = value
