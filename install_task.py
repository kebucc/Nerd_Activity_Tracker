import subprocess
import sys
import os

from config import BASE_DIR

TASK_NAME = "NerdActivityTracker"
PYTHONW = sys.executable.replace("python.exe", "pythonw.exe")
TRACKER_SCRIPT = os.path.join(BASE_DIR, "tracker.py")


def install():
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", f'"{PYTHONW}" "{TRACKER_SCRIPT}"',
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",
        "/F",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' created successfully.")
        print("The tracker will start automatically on login.")
    else:
        print(f"Error creating task: {result.stderr}")
        print("Try running this script as Administrator.")


def uninstall():
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' removed.")
    else:
        print(f"Error: {result.stderr}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()
