from datetime import datetime
import psycopg
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort

from backend.db import fetch_one, fetch_all, execute
from backend.security import login_required, validate_csrf
from backend.validation import clean_text, positive_float, parse_datetime
from backend.services.analytics import summarize_readings
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

            elif action == "update_sensor":
                if session.get("role") != "admin":
                    abort(403)
                code = clean_text(request.form.get("code"), 80).upper()
                name = clean_text(request.form.get("sensor_name"), 100)
                active = request.form.get("active") == "on"
                if not code:
                    raise ValueError("El código del sensor es obligatorio.")
                execute(
                    """
                    UPDATE sensors
                    SET code=%s, name=%s, active=%s
                    WHERE household_id=%s
                    """,
                    (code, name or "Caudalímetro principal", active, household_id),
                )
                flash("Caudalímetro principal actualizado.", "success")
            else:
                raise ValueError("Operación de gestión no reconocida.")

        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")
        except psycopg.errors.UniqueViolation:
            flash("El código de sensor ya está en uso.", "error")
        return redirect(url_for("main.management"))

    household = fetch_one(
        """
        SELECT id, name, daily_goal_liters, anomaly_threshold_percent,
               leak_flow_threshold_l_min, leak_duration_minutes
        FROM households WHERE id=%s
        """,
        (household_id,),
    )
    sensor = fetch_one(
        """
        SELECT id, code, name, sensor_type, installation_point, active, installed_at, created_at
        FROM sensors WHERE household_id=%s
        """,
        (household_id,),
    )
    alerts = fetch_all(
        """
        SELECT id, alert_type, severity, title, message, status, created_at
        FROM alerts WHERE household_id=%s ORDER BY created_at DESC LIMIT 30
        """,
        (household_id,),
    )
    return render_template("gestion.html", household=household, sensor=sensor, alerts=alerts)


@main_bp.route("/lecturas/nueva", methods=["GET", "POST"])
@login_required
def new_reading():
    household_id = session["household_id"]
    sensor = fetch_one(
        """
        SELECT id, code, name, installation_point, active
        FROM sensors WHERE household_id=%s
        """,
        (household_id,),
    )

    if request.method == "POST":
        validate_csrf()
        try:
            if not sensor or not sensor["active"]:
                raise ValueError("El caudalímetro principal no está activo.")
            recorded_at = parse_datetime(request.form.get("date"), request.form.get("time"))
            flow = positive_float(request.form.get("flow"), "Flujo", 500)
            volume = positive_float(request.form.get("volume"), "Volumen", 10000)
            create_reading(
                household_id=household_id,
                sensor_id=sensor["id"],
                recorded_at=recorded_at,
                flow_l_min=flow,
                volume_liters=volume,
                source="manual",
                created_by_user_id=session["user_id"],
            )
            flash("Lectura del caudalímetro principal registrada correctamente.", "success")
            return redirect(url_for("main.dashboard"))
        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")
            return render_template("reading_form.html", sensor=sensor, now=datetime.now()), 400
        except Exception:
            flash("No fue posible guardar la lectura. Verifica los datos e intenta nuevamente.", "error")
            return render_template("reading_form.html", sensor=sensor, now=datetime.now()), 500

    return render_template("reading_form.html", sensor=sensor, now=datetime.now())


@main_bp.get("/reportes")
@login_required
def reports():
    context = _dashboard_context(session["household_id"], limit=500)
    return render_template("reports.html", **context)


@main_bp.get("/historial")
@login_required
def history():
    rows = _readings(session["household_id"], 500)
    return render_template("history.html", readings=rows)


def _readings(household_id, limit=180):
    return fetch_all(
        """
        SELECT r.id, r.recorded_at, r.flow_l_min, r.volume_liters, r.source,
               s.code AS sensor_code, s.name AS sensor_name, s.installation_point
        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s
        ORDER BY r.recorded_at DESC
        LIMIT %s
        """,
        (household_id, limit),
    )


def _dashboard_context(household_id, limit=180):
    household = fetch_one(
        """
        SELECT id, name, daily_goal_liters, anomaly_threshold_percent,
               leak_flow_threshold_l_min, leak_duration_minutes
        FROM households WHERE id=%s
        """,
        (household_id,),
    )
    sensor = fetch_one(
        "SELECT id, code, name, installation_point, active FROM sensors WHERE household_id=%s",
        (household_id,),
    )
    readings_desc = _readings(household_id, limit)
    readings = list(reversed(readings_desc))
    summary = summarize_readings(readings, household["daily_goal_liters"])
    alerts = fetch_all(
        """
        SELECT id, alert_type, severity, title, message, status, created_at
        FROM alerts WHERE household_id=%s ORDER BY created_at DESC LIMIT 8
        """,
        (household_id,),
    )
    return {
        "household": household,
        "sensor": sensor,
        "readings": readings_desc[:12],
        "summary": summary,
        "alerts": alerts,
    }
