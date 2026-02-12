import os
import sys
import time
import msvcrt
import threading
import subprocess
import webbrowser
from datetime import datetime

from pynput import mouse, keyboard
import pystray
from PIL import Image, ImageDraw

import config
import db


class InputTracker:
    def __init__(self, session_type):
        self.session_type = session_type
        self.last_event_time = None
        self.session_start = None
        self.lock = threading.Lock()

    def on_event(self):
        with self.lock:
            now = datetime.now()
            self.last_event_time = now
            if self.session_start is None:
                self.session_start = now

    def check_idle(self):
        with self.lock:
            if self.session_start and self.last_event_time:
                idle = (datetime.now() - self.last_event_time).total_seconds()
                if idle >= config.IDLE_THRESHOLD_SECONDS:
                    db.save_session(self.session_start, self.last_event_time, self.session_type)
                    self.session_start = None
                    self.last_event_time = None

    def flush(self):
        with self.lock:
            if self.session_start and self.last_event_time:
                db.save_session(self.session_start, self.last_event_time, self.session_type)
                self.session_start = None
                self.last_event_time = None


# Module-level references for cross-function access
_mouse_tracker = None
_keyboard_tracker = None
_mouse_listener = None
_keyboard_listener = None
_stop_event = threading.Event()
_dashboard_process = None


def create_tray_icon_image():
    settings = config.load_settings()
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 12, 30, 52], fill=settings["color_mouse"])
    draw.ellipse([34, 12, 60, 52], fill=settings["color_keyboard"])
    return img


def open_dashboard():
    global _dashboard_process

    # If dashboard is already running, just open the browser
    if _dashboard_process is not None and _dashboard_process.poll() is None:
        webbrowser.open(f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
        return

    # Launch dashboard as a background subprocess
    dashboard_script = os.path.join(config.BASE_DIR, "dashboard.py")
    pythonw = sys.executable
    if pythonw.endswith("python.exe"):
        pythonw = pythonw.replace("python.exe", "pythonw.exe")

    _dashboard_process = subprocess.Popen(
        [pythonw, dashboard_script],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # Give Flask time to start, then open browser
    time.sleep(1.5)
    webbrowser.open(f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")


def on_exit(icon, item):
    _mouse_tracker.flush()
    _keyboard_tracker.flush()
    _mouse_listener.stop()
    _keyboard_listener.stop()
    _stop_event.set()

    global _dashboard_process
    if _dashboard_process is not None and _dashboard_process.poll() is None:
        _dashboard_process.terminate()

    icon.stop()


def idle_check_loop():
    while not _stop_event.is_set():
        time.sleep(0.5)
        _mouse_tracker.check_idle()
        _keyboard_tracker.check_idle()


def main():
    global _mouse_tracker, _keyboard_tracker, _mouse_listener, _keyboard_listener

    # Prevent multiple instances via file lock
    os.makedirs(config.DATA_DIR, exist_ok=True)
    lock_path = os.path.join(config.DATA_DIR, ".tracker.lock")
    try:
        lock_fd = open(lock_path, "w")
        msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
    except (OSError, IOError):
        sys.exit(0)

    db.init_db()

    # Load saved settings
    settings = config.load_settings()
    config.set_idle_threshold(settings["idle_threshold"])

    _mouse_tracker = InputTracker("mouse")
    _keyboard_tracker = InputTracker("keyboard")

    _mouse_listener = mouse.Listener(
        on_move=lambda x, y: _mouse_tracker.on_event(),
        on_click=lambda x, y, button, pressed: _mouse_tracker.on_event(),
        on_scroll=lambda x, y, dx, dy: _mouse_tracker.on_event(),
    )
    _keyboard_listener = keyboard.Listener(
        on_press=lambda key: _keyboard_tracker.on_event()
    )
    _mouse_listener.daemon = True
    _keyboard_listener.daemon = True
    _mouse_listener.start()
    _keyboard_listener.start()

    # Idle check in a daemon thread
    threading.Thread(target=idle_check_loop, daemon=True).start()

    # System tray icon
    icon_image = create_tray_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", lambda: open_dashboard()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit),
    )

    icon = pystray.Icon(
        name="NerdActivityTracker",
        icon=icon_image,
        title="Nerd Activity Tracker",
        menu=menu,
    )

    # Blocks until icon.stop() is called
    icon.run()


if __name__ == "__main__":
    main()
