import json
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app

from backend.db import execute, fetch_one
from backend.realtime import publish_event
from backend.services.readings import create_reading
from backend.services.anomaly_model import evaluate_latest_window
from backend.validation import nonnegative_float
from backend.mqtt.topics import parse_topic


def _parse_datetime(value):
    if not value:
        return datetime.now(ZoneInfo(current_app.config.get("APP_TIMEZONE", "America/Bogota")))
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError("recorded_at no tiene un formato ISO válido") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(current_app.config.get("APP_TIMEZONE", "America/Bogota")))
    return parsed


def handle_message(topic, payload):
    household_id, message_type = parse_topic(topic)
    try:
        data = json.loads(payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Mensaje MQTT con JSON inválido") from exc

    if not isinstance(data, dict):
        raise ValueError("El mensaje MQTT debe ser un objeto JSON")

    if message_type == "lecturas":
        return handle_reading(household_id, data)
    if message_type == "estado":
        return handle_state(household_id, data)
    return None


def handle_reading(household_id, data):
    sensor = fetch_one(
        """
        SELECT id, household_id, active
        FROM sensors
        WHERE household_id=%s AND installation_point='acometida_principal'
        """,
        (household_id,),
    )
    if not sensor or not sensor["active"]:
        raise ValueError("No existe un caudalímetro principal activo para el hogar del tópico")

    flow = nonnegative_float(data.get("caudal_lpm"), "caudal_lpm", 60)
    volume = nonnegative_float(data.get("volumen_l"), "volumen_l", 10000)
    recorded_at = _parse_datetime(data.get("recorded_at"))

    reading = create_reading(
        household_id=household_id,
        sensor_id=sensor["id"],
        recorded_at=recorded_at,
        flow_l_min=flow,
        volume_liters=volume,
        source="iot",
        created_by_user_id=None,
        origin_mqtt=True,
    )

    # El modelo es complementario a las reglas. Un error de ML nunca debe
    # impedir que una lectura válida quede persistida.
    try:
        ml_result = evaluate_latest_window(household_id, reading)
        if ml_result.get("evaluated"):
            current_app.logger.info(
                "[ML] hogar=%s anomalía=%s score=%.4f",
                household_id,
                ml_result.get("anomaly"),
                ml_result.get("score", 0.0),
            )
    except Exception:
        current_app.logger.exception("[ML] fallo evaluando hogar=%s", household_id)

    return reading


def handle_state(household_id, data):
    sensor = fetch_one(
        "SELECT id FROM sensors WHERE household_id=%s",
        (household_id,),
    )
    if not sensor:
        raise ValueError("El hogar del tópico no tiene sensor registrado")

    online = data.get("en_linea")
    valve = data.get("valvula")
    if online is not None and not isinstance(online, bool):
        raise ValueError("en_linea debe ser booleano")
    if valve is not None and valve not in {"abierta", "cerrada"}:
        raise ValueError("valvula debe ser 'abierta' o 'cerrada'")

    execute(
        """
        UPDATE sensors
        SET en_linea=COALESCE(%s, en_linea),
            ultima_conexion=NOW(),
            estado_valvula=COALESCE(%s, estado_valvula)
        WHERE household_id=%s
        """,
        (online, valve, household_id),
    )

    command_id = data.get("ack")
    if command_id is not None:
        try:
            command_id = int(command_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("ack debe contener un identificador de comando entero") from exc
        execute(
            """
            UPDATE comandos
            SET estado='confirmado', confirmado_en=NOW()
            WHERE id=%s AND household_id=%s AND estado='enviado'
            """,
            (command_id, household_id),
        )

    event = {
        "tipo": "estado",
        "en_linea": online,
        "valvula": valve,
        "ack": command_id,
        "recorded_at": data.get("recorded_at"),
    }
    publish_event(household_id, event)
    return {"household_id": household_id, "en_linea": online, "valvula": valve, "ack": command_id}
