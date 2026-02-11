import os
import sqlite3
from datetime import datetime

from config import DATA_DIR, DB_PATH, MIN_SESSION_DURATION, _LEGACY_DB_PATH


def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    # Migrate legacy database name (mouse_activity.db -> data.db)
    try:
        if os.path.exists(_LEGACY_DB_PATH) and not os.path.exists(DB_PATH):
            os.rename(_LEGACY_DB_PATH, DB_PATH)
    except OSError:
        pass
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT NOT NULL DEFAULT 'mouse',
            start_time  TEXT NOT NULL,
            end_time    TEXT NOT NULL,
            duration    REAL NOT NULL
        )
    """)
    # Migration: add type column if the DB predates it
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN type TEXT NOT NULL DEFAULT 'mouse'")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_start
        ON sessions(start_time)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_type
        ON sessions(type)
    """)
    conn.commit()
    conn.close()


def save_session(start_time: datetime, end_time: datetime, session_type: str = "mouse"):
    duration = (end_time - start_time).total_seconds()
    if duration < MIN_SESSION_DURATION:
        return
    conn = _get_conn()
    conn.execute(
        "INSERT INTO sessions (type, start_time, end_time, duration) VALUES (?, ?, ?, ?)",
        (session_type, start_time.isoformat(), end_time.isoformat(), round(duration, 2)),
    )
    conn.commit()
    conn.close()


def get_sessions_for_date(date_str: str, session_type: str = None) -> list[dict]:
    conn = _get_conn()
    if session_type:
        rows = conn.execute(
            "SELECT session_id, type, start_time, end_time, duration "
            "FROM sessions WHERE date(start_time) = ? AND type = ? ORDER BY start_time",
            (date_str, session_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT session_id, type, start_time, end_time, duration "
            "FROM sessions WHERE date(start_time) = ? ORDER BY start_time",
            (date_str,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary_for_date(date_str: str, session_type: str = None) -> dict:
    conn = _get_conn()
    if session_type:
        row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) AS total_duration, "
            "       COUNT(*) AS session_count, "
            "       COALESCE(AVG(duration), 0) AS avg_duration "
            "FROM sessions WHERE date(start_time) = ? AND type = ?",
            (date_str, session_type),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) AS total_duration, "
            "       COUNT(*) AS session_count, "
            "       COALESCE(AVG(duration), 0) AS avg_duration "
            "FROM sessions WHERE date(start_time) = ?",
            (date_str,),
        ).fetchone()
    conn.close()
    return dict(row)


def get_sessions_for_range(start_date: str, end_date: str, session_type: str = None) -> list[dict]:
    conn = _get_conn()
    if session_type:
        rows = conn.execute(
            "SELECT session_id, type, start_time, end_time, duration "
            "FROM sessions WHERE date(start_time) >= ? AND date(start_time) <= ? AND type = ? "
            "ORDER BY start_time",
            (start_date, end_date, session_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT session_id, type, start_time, end_time, duration "
            "FROM sessions WHERE date(start_time) >= ? AND date(start_time) <= ? "
            "ORDER BY start_time",
            (start_date, end_date),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary_for_range(start_date: str, end_date: str, session_type: str = None) -> dict:
    conn = _get_conn()
    if session_type:
        row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) AS total_duration, "
            "       COUNT(*) AS session_count, "
            "       COALESCE(AVG(duration), 0) AS avg_duration "
            "FROM sessions WHERE date(start_time) >= ? AND date(start_time) <= ? AND type = ?",
            (start_date, end_date, session_type),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) AS total_duration, "
            "       COUNT(*) AS session_count, "
            "       COALESCE(AVG(duration), 0) AS avg_duration "
            "FROM sessions WHERE date(start_time) >= ? AND date(start_time) <= ?",
            (start_date, end_date),
        ).fetchone()
    conn.close()
    return dict(row)


def get_available_dates() -> list[str]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT date(start_time) AS d FROM sessions ORDER BY d DESC"
    ).fetchall()
    conn.close()
    return [r["d"] for r in rows]
