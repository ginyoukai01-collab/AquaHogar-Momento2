import json
import math
import os
import random
import ssl
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from backend.mqtt.topics import commands_topic, readings_topic, state_topic

load_dotenv()

HOST = (os.getenv("MQTT_HOST") or "").strip()
PORT = int(os.getenv("MQTT_PORT", "8883"))
USER = os.getenv("MQTT_USER") or ""
PASSWORD = os.getenv("MQTT_PASS") or ""
HOUSEHOLD_ID = int(os.getenv("MQTT_HOUSEHOLD_ID", "1"))
CLIENT_ID = os.getenv("MQTT_SIMULATOR_CLIENT_ID", f"aquahogar-simulador-{HOUSEHOLD_ID}")
INTERVAL_SECONDS = float(os.getenv("MQTT_SIMULATOR_INTERVAL_SECONDS", "1"))
STEP_MINUTES = int(os.getenv("MQTT_SIMULATOR_STEP_MINUTES", "10"))
LEAK_ENABLED = (os.getenv("MQTT_SIMULATOR_LEAK_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"})
LEAK_START_HOUR = int(os.getenv("MQTT_SIMULATOR_LEAK_START_HOUR", "3"))
LEAK_FLOW = float(os.getenv("MQTT_SIMULATOR_LEAK_FLOW_L_MIN", "2.0"))
TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Bogota"))

T_READINGS = readings_topic(HOUSEHOLD_ID)
T_STATE = state_topic(HOUSEHOLD_ID)
T_COMMANDS = commands_topic(HOUSEHOLD_ID)

if not HOST or not USER or not PASSWORD:
    raise SystemExit("Configura MQTT_HOST, MQTT_USER y MQTT_PASS antes de ejecutar el simulador.")

valve_state = "abierta"
simulated_time = datetime.now(TZ).replace(second=0, microsecond=0)


def realistic_flow(ts):
    hour = ts.hour + ts.minute / 60

    if 0 <= hour < 5:
        base = random.uniform(0.0, 0.08)
    elif 5 <= hour < 6:
        base = random.uniform(0.05, 0.6)
    elif 6 <= hour < 8:
        base = random.uniform(2.0, 8.5)
    elif 8 <= hour < 12:
        base = random.uniform(0.2, 3.0)
    elif 12 <= hour < 14:
        base = random.uniform(1.0, 5.0)
    elif 14 <= hour < 18:
        base = random.uniform(0.1, 2.2)
    elif 18 <= hour < 21:
        base = random.uniform(2.0, 7.0)
    elif 21 <= hour < 23:
        base = random.uniform(0.3, 2.5)
    else:
        base = random.uniform(0.0, 0.25)

    # Variación suave para evitar una señal completamente aleatoria.
    base += max(0.0, math.sin(ts.minute / 60 * math.pi)) * random.uniform(0.0, 0.25)

    if LEAK_ENABLED and ts.hour >= LEAK_START_HOUR and ts.hour < 5:
        base += LEAK_FLOW

    if valve_state == "cerrada":
        return 0.0

    return max(0.0, round(base, 3))


def publish_state(client, *, online=True, ack=None, action=None):
    payload = {
        "en_linea": bool(online),
        "valvula": valve_state,
        "recorded_at": datetime.now(TZ).isoformat(timespec="seconds"),
    }
    if ack is not None:
        payload["ack"] = ack
    if action:
        payload["accion"] = action
    client.publish(T_STATE, json.dumps(payload), qos=1, retain=True)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"No fue posible conectar al broker. Código: {reason_code}")
        return
    print(f"Conectado a MQTT TLS {HOST}:{PORT}")
    print(f"Lecturas: {T_READINGS}")
    print(f"Estado:   {T_STATE}")
    print(f"Comandos: {T_COMMANDS}")
    client.subscribe(T_COMMANDS, qos=1)
    publish_state(client, online=True)


def on_message(client, userdata, msg):
    global valve_state
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("Comando descartado: JSON inválido")
        return

    action = data.get("accion")
    command_id = data.get("id")

    if action == "cerrar_valvula":
        valve_state = "cerrada"
    elif action == "abrir_valvula":
        valve_state = "abierta"
    elif action == "reiniciar":
        valve_state = "abierta"
    else:
        print("Comando no reconocido:", data)
        return

    publish_state(client, online=True, ack=command_id, action=action)
    print(f"Comando confirmado: id={command_id} acción={action} válvula={valve_state}")


def build_client():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )
    client.username_pw_set(USER, PASSWORD)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.will_set(
        T_STATE,
        payload=json.dumps({"en_linea": False, "valvula": valve_state}),
        qos=1,
        retain=True,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    global simulated_time

    client = build_client()
    client.connect(HOST, PORT, keepalive=60)
    client.loop_start()

    print("Simulador AquaHogar MQTT iniciado. Ctrl+C para detener.")
    print(
        f"Tiempo simulado: +{STEP_MINUTES} min cada {INTERVAL_SECONDS}s reales | "
        f"fuga={'sí' if LEAK_ENABLED else 'no'}"
    )

    try:
        while True:
            flow = realistic_flow(simulated_time)
            volume = round(flow * (STEP_MINUTES / 60), 3)
            payload = {
                "caudal_lpm": flow,
                "volumen_l": volume,
                "recorded_at": simulated_time.isoformat(timespec="seconds"),
            }
            info = client.publish(T_READINGS, json.dumps(payload), qos=1, retain=False)
            info.wait_for_publish(timeout=5)
            print(simulated_time.isoformat(timespec="minutes"), payload)
            simulated_time += timedelta(minutes=STEP_MINUTES)
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Deteniendo simulador...")
    finally:
        publish_state(client, online=False)
        time.sleep(0.2)
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
