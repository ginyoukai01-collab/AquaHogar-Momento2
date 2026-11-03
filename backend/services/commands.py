import json
import os
import threading
import time

import paho.mqtt.client as mqtt
from flask import current_app

from backend.db import execute, fetch_all
from backend.mqtt.topics import commands_topic

ALLOWED_ACTIONS = {"cerrar_valvula", "abrir_valvula", "reiniciar"}
TIMEOUT_SECONDS = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "30"))


def expire_stale_commands(household_id=None):
    params = [TIMEOUT_SECONDS]
    where_household = ""
    if household_id is not None:
        where_household = " AND household_id=%s"
        params.append(household_id)

    execute(
        f"""
        UPDATE comandos
        SET estado='fallido'
        WHERE estado='enviado'
          AND enviado_en <= NOW() - (%s * INTERVAL '1 second')
          {where_household}
        """,
        tuple(params),
    )


def list_commands(household_id, limit=20):
    expire_stale_commands(household_id)
    return fetch_all(
        """
        SELECT c.id, c.accion, c.estado, c.enviado_en, c.confirmado_en,
               u.name AS usuario_nombre
        FROM comandos c
        JOIN users u ON u.id=c.usuario_id
        WHERE c.household_id=%s
        ORDER BY c.enviado_en DESC
        LIMIT %s
        """,
        (household_id, limit),
    )


def send_command(household_id, user_id, action):
    if action not in ALLOWED_ACTIONS:
        raise ValueError("Comando no permitido")

    status = current_app.extensions.get("aquahogar_mqtt_status", {})
    client = current_app.extensions.get("aquahogar_mqtt")
    if not client or not status.get("connected"):
        raise ValueError("El backend MQTT no está conectado al broker")

    row = execute(
        """
        INSERT INTO comandos(household_id, usuario_id, accion, estado)
        VALUES (%s, %s, %s, 'enviado')
        RETURNING id, household_id, usuario_id, accion, estado, enviado_en
        """,
        (household_id, user_id, action),
        returning=True,
    )

    payload = {"id": int(row["id"]), "accion": action}
    info = client.publish(
        commands_topic(household_id),
        json.dumps(payload),
        qos=1,
        retain=False,
    )
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        execute(
            "UPDATE comandos SET estado='fallido' WHERE id=%s AND household_id=%s",
            (row["id"], household_id),
        )
        raise ValueError("No fue posible publicar el comando en MQTT")

    app = current_app._get_current_object()
    threading.Thread(
        target=_timeout_worker,
        args=(app, int(row["id"]), household_id),
        daemon=True,
    ).start()
    return row


def _timeout_worker(app, command_id, household_id):
    time.sleep(TIMEOUT_SECONDS)
    try:
        with app.app_context():
            execute(
                """
                UPDATE comandos
                SET estado='fallido'
                WHERE id=%s
                  AND household_id=%s
                  AND estado='enviado'
                  AND enviado_en <= NOW() - (%s * INTERVAL '1 second')
                """,
                (command_id, household_id, TIMEOUT_SECONDS),
            )
    except Exception as exc:
        print(f"[COMMANDS] no se pudo marcar timeout del comando {command_id}: {exc}", flush=True)
