from datetime import date

from flask import Flask, jsonify, redirect, render_template, request, url_for

import config
import db
from config import DASHBOARD_HOST, DASHBOARD_PORT

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


def _format_duration(seconds):
    seconds = round(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _build_summary(date_str, session_type=None):
    summary = db.get_summary_for_date(date_str, session_type)
    summary["total_duration_formatted"] = _format_duration(summary["total_duration"])
    summary["avg_duration_formatted"] = _format_duration(summary["avg_duration"])
    return summary


@app.route("/")
def index():
    today = date.today().isoformat()
    return redirect(url_for("show_day", date_str=today))


@app.route("/day/<date_str>")
def show_day(date_str):
    settings = config.load_settings()
    mouse_summary = _build_summary(date_str, "mouse")
    keyboard_summary = _build_summary(date_str, "keyboard")
    cumulative_summary = _build_summary(date_str)
    dates = db.get_available_dates()
    return render_template(
        "index.html",
        date_str=date_str,
        mouse_summary=mouse_summary,
        keyboard_summary=keyboard_summary,
        cumulative_summary=cumulative_summary,
        dates=dates,
        colors={
            "mouse": settings["color_mouse"],
            "keyboard": settings["color_keyboard"],
            "cumulative": settings["color_cumulative"],
        },
    )


@app.route("/api/sessions/<date_str>")
def api_sessions(date_str):
    session_type = request.args.get("type")
    return jsonify(db.get_sessions_for_date(date_str, session_type))


@app.route("/api/summary/<date_str>")
def api_summary(date_str):
    session_type = request.args.get("type")
    return jsonify(db.get_summary_for_date(date_str, session_type))


@app.route("/api/dates")
def api_dates():
    return jsonify(db.get_available_dates())


@app.route("/settings", methods=["GET"])
def settings_page():
    settings = config.load_settings()
    return render_template(
        "settings.html",
        settings=settings,
        colors={
            "mouse": settings["color_mouse"],
            "keyboard": settings["color_keyboard"],
            "cumulative": settings["color_cumulative"],
        },
    )


@app.route("/settings", methods=["POST"])
def settings_save():
    try:
        threshold = float(request.form.get("idle_threshold", 3))
        if threshold < 0.5:
            threshold = 0.5
    except ValueError:
        threshold = 3

    new_settings = {
        "idle_threshold": threshold,
        "color_mouse": request.form.get("color_mouse", "#4CAF50"),
        "color_keyboard": request.form.get("color_keyboard", "#42A5F5"),
        "color_cumulative": request.form.get("color_cumulative", "#E0E0E0"),
    }
    config.save_settings(new_settings)
    return redirect(url_for("index"))


if __name__ == "__main__":
    db.init_db()
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)
