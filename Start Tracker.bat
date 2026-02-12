@echo off
cd /d "%~dp0"
start "" pythonw tracker.py
@echo off
cd /d "d:\K-TUF-REPOSITORY\BkLAb\Nerd_Activity_Tracker"
start "" http://127.0.0.1:5000
python dashboard.py
