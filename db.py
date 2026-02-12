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


def _merge_intervals(sessions):
    """Merge overlapping sessions into non-overlapping intervals."""
    if not sessions:
        return []
    merged = []
    cur_start = sessions[0]["start_time"]
    cur_end = sessions[0]["end_time"]
    for s in sessions[1:]:
        if s["start_time"] <= cur_end:
            if s["end_time"] > cur_end:
                cur_end = s["end_time"]
        else:
            merged.append((cur_start, cur_end))
            cur_start = s["start_time"]
            cur_end = s["end_time"]
    merged.append((cur_start, cur_end))
    return merged


def _merged_summary(sessions):
    """Compute summary stats from merged (non-overlapping) intervals."""
    intervals = _merge_intervals(sessions)
    if not intervals:
        return {"total_duration": 0, "session_count": 0, "avg_duration": 0}
    total = 0.0
    for start_iso, end_iso in intervals:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        total += (end - start).total_seconds()
    count = len(intervals)
    return {
        "total_duration": round(total, 2),
        "session_count": count,
        "avg_duration": round(total / count, 2),
    }


def get_merged_summary_for_date(date_str: str) -> dict:
    sessions = get_sessions_for_date(date_str)
    return _merged_summary(sessions)


def get_merged_summary_for_range(start_date: str, end_date: str) -> dict:
    sessions = get_sessions_for_range(start_date, end_date)
    return _merged_summary(sessions)


def get_merged_daily_totals(start_date: str, end_date: str) -> dict:
    """Return {date: merged_total_seconds} for each date in the range."""
    sessions = get_sessions_for_range(start_date, end_date)
    by_date: dict[str, list] = {}
    for s in sessions:
        d = s["start_time"].split("T")[0]
        by_date.setdefault(d, []).append(s)
    result = {}
    for d, day_sessions in by_date.items():
        intervals = _merge_intervals(day_sessions)
        total = sum(
            (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
            for start, end in intervals
        )
        result[d] = round(total, 2)
    return result


def get_available_dates() -> list[str]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT date(start_time) AS d FROM sessions ORDER BY d DESC"
    ).fetchall()
    conn.close()
    return [r["d"] for r in rows]
