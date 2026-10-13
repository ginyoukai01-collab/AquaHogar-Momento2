from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, session

from backend.db import fetch_one, fetch_all
from backend.services.readings import create_reading
from backend.validation import positive_float

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    try:
        row = fetch_one("SELECT 1 AS ok")
        return jsonify({"status": "ok", "database": bool(row and row["ok"] == 1)})
    except Exception:
        return jsonify({"status": "degraded", "database": False}), 503


@api_bp.get("/lecturas")
def readings():
    if not session.get("user_id"):
        return jsonify({"error": "Autenticación requerida"}), 401
    household_id = request.args.get("household_id", type=int) or session.get("household_id")
    if household_id != session.get("household_id"):
        return jsonify({"error": "No autorizado para consultar este hogar"}), 403

    rows = fetch_all(
        """
        SELECT r.id, r.recorded_at, r.flow_l_min, r.volume_liters, r.source,
               s.code AS sensor_code, s.installation_point
        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s
        ORDER BY r.recorded_at DESC LIMIT 100
        """,
        (household_id,),
    )
    serializable = [dict(r, recorded_at=r["recorded_at"].isoformat()) for r in rows]
    return jsonify({"readings": serializable})


@api_bp.post("/iot/lecturas")
def iot_reading():
    expected = current_app.config.get("IOT_API_KEY")
    supplied = request.headers.get("X-AquaHogar-Key")
    if not expected:
        return jsonify({"error": "Integración IoT no configurada"}), 503
    if supplied != expected:
        return jsonify({"error": "No autorizado"}), 401

    body = request.get_json(silent=True) or {}
    try:
        sensor_code = str(body.get("sensor_code", "")).strip().upper()
        if not sensor_code:
            raise ValueError("sensor_code es obligatorio")

        sensor = fetch_one(
            """
            SELECT id, household_id
            FROM sensors
            WHERE code=%s AND active=TRUE AND installation_point='acometida_principal'
            """,
            (sensor_code,),
        )
        if not sensor:
            return jsonify({"error": "Caudalímetro principal no encontrado"}), 404

        recorded_at = datetime.fromisoformat(body.get("recorded_at")) if body.get("recorded_at") else datetime.now()
        flow = positive_float(body.get("flow_l_min"), "flow_l_min", 500)
        volume = positive_float(body.get("volume_liters"), "volume_liters", 10000)
        reading = create_reading(
            household_id=sensor["household_id"],
            sensor_id=sensor["id"],
            recorded_at=recorded_at,
            flow_l_min=flow,
            volume_liters=volume,
            source="iot",
            created_by_user_id=None,
        )
        return jsonify({"accepted": True, "reading_id": reading["id"]}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Error interno al registrar la lectura"}), 500
