from datetime import datetime
import psycopg
from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

from backend.db import fetch_one, fetch_all, execute
from backend.realtime import subscribe, sse_stream
from backend.security import login_required, validate_csrf
from backend.validation import clean_text, positive_float, parse_datetime
from backend.services.analytics import summarize_readings
from backend.services.anomaly_model import model_status
from backend.services.commands import list_commands, send_command
from backend.services.readings import create_reading

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("index.html")


@main_bp.get("/dashboard")
@login_required
def dashboard():
    context = _dashboard_context(session["household_id"])
    return render_template("dashboard.html", **context)


@main_bp.get("/stream/<int:household_id>")
@login_required
def stream(household_id):
    if household_id != session.get("household_id"):
        abort(403)

    channel = subscribe(household_id)
    return Response(
        stream_with_context(sse_stream(household_id, channel)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@main_bp.route("/gestion", methods=["GET", "POST"])
@login_required
def management():
    household_id = session["household_id"]

    if request.method == "POST":
        validate_csrf()
        action = request.form.get("action")
        try:
            if action == "resolve_alert":
                alert_id = int(request.form.get("alert_id"))
                execute(
                    "UPDATE alerts SET status='resuelta', resolved_at=NOW() WHERE id=%s AND household_id=%s",
                    (alert_id, household_id),
                )
                flash("Alerta marcada como resuelta.", "success")

            elif action == "update_settings":
                if session.get("role") != "admin":
                    abort(403)
                daily_goal = positive_float(request.form.get("daily_goal"), "Meta diaria", 10000)
                anomaly_threshold = positive_float(request.form.get("anomaly_threshold"), "Umbral de anomalía", 200)
                leak_flow = positive_float(request.form.get("leak_flow_threshold"), "Flujo mínimo de fuga", 500)
                leak_minutes = int(request.form.get("leak_duration_minutes"))
                if leak_minutes < 5 or leak_minutes > 240:
                    raise ValueError("La ventana de fuga debe estar entre 5 y 240 minutos.")
                execute(
                    """
                    UPDATE households
                    SET daily_goal_liters=%s,
                        anomaly_threshold_percent=%s,
                        leak_flow_threshold_l_min=%s,
                        leak_duration_minutes=%s
                    WHERE id=%s
                    """,
                    (daily_goal, anomaly_threshold, leak_flow, leak_minutes, household_id),
                )
                flash("Parámetros de monitoreo actualizados.", "success")
