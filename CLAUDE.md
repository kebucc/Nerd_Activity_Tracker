# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nerd Activity Tracker is a Windows-only Python application that monitors mouse and keyboard input throughout the day and visualizes activity via a web dashboard.

**Stack:** Python 3.10+ / Flask / SQLite / vanilla JavaScript (no frontend framework)

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the tracker (system tray icon + background tracking)
python tracker.py
# Or without console window:
pythonw tracker.py

# Run the web dashboard standalone (Flask server at http://127.0.0.1:5000)
python dashboard.py

# Auto-start tracker on Windows login (run as Administrator)
python install_task.py

# Remove auto-start
python install_task.py --uninstall
```

## Architecture

The tracker runs as a system tray application (`pystray`) and launches the Flask dashboard as a subprocess on demand.

**tracker.py** — Main entry point. Runs `pystray` icon loop on the main thread. Spawns `pynput` mouse/keyboard listeners and an idle-check loop as daemon threads. The tray menu provides: change idle threshold (tkinter dialog), open dashboard (starts Flask subprocess + browser), and exit. Uses a file lock (`.tracker.lock`) to prevent multiple instances.

**dashboard.py** — Flask server that reads from SQLite. Serves HTML pages via Jinja2 and exposes JSON API endpoints. Runs on `127.0.0.1:5000` (no auth, localhost only). Shows separate stats for mouse/keyboard plus cumulative combined stats.

**config.py** — All tunable parameters: idle threshold (modifiable at runtime via `get/set_idle_threshold()`), minimum session duration, Flask host/port, database path. Legacy DB path for automatic migration.

**db.py** — Shared data layer. Handles table creation, session writes, queries. Uses WAL mode. Automatically migrates old `mouse_activity.db` to `data.db` on startup.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Redirects to today's date |
| `GET /day/<YYYY-MM-DD>` | Dashboard page for a specific date |
| `GET /api/sessions/<date>` | Sessions JSON (optional `?type=mouse\|keyboard`) |
| `GET /api/summary/<date>` | Aggregated stats JSON (optional `?type=` filter) |
| `GET /api/dates` | List of dates with recorded data |

## Database

Single SQLite file at `data/data.db` (auto-created on first run).

**Table `sessions`:** `session_id` (INTEGER PK), `type` (TEXT: `mouse` or `keyboard`), `start_time` (TEXT ISO 8601), `end_time` (TEXT ISO 8601), `duration` (REAL seconds). Indexed on `start_time` and `type`.

## Frontend

- **templates/base.html** — Shared layout with header and asset includes
- **templates/index.html** — Dashboard page: date nav, mouse/keyboard/cumulative sections (each with stats cards + 24h timeline), session detail table
- **static/style.css** — Dark theme; green (#4CAF50) for mouse, blue (#42A5F5) for keyboard, light gray (#E0E0E0) for cumulative
- **static/dashboard.js** — Fetches API data, renders 24-hour timeline bars, populates session table, handles date navigation

## Dependencies

- `pynput` — Global mouse/keyboard input monitoring
- `flask` — Web framework for dashboard
- `pystray` — System tray icon
- `Pillow` — Icon image generation (used by pystray)
