import json
import os
import ssl
from datetime import datetime
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

from backend.mqtt.config import mqtt_config, validate_mqtt_config
from backend.mqtt.handlers import handle_message
from backend.mqtt.topics import readings_topic, subscriptions


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _status(app):
    return app.extensions.setdefault(
        "aquahogar_mqtt_status",
        {
            "enabled": False,
            "connected": False,
            "host": None,
            "port": None,
            "last_reason": None,
            "self_test_sent": False,
        },
    )


def build_client(app):
    config = mqtt_config()
    validate_mqtt_config(config)
    status = _status(app)
    status.update(
        {
            "enabled": True,
            "connected": False,
            "host": config["host"],
            "port": config["port"],
            "last_reason": "iniciando",
        }
    )

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=config["client_id"],
        protocol=mqtt.MQTTv311,
    )
    client.username_pw_set(config["user"], config["password"])
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

    def on_connect(mqtt_client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            status["connected"] = False
            status["last_reason"] = f"connect_error:{reason_code}"
            print(f"[MQTT] conexión rechazada, código={reason_code}", flush=True)
            return

        mqtt_client.subscribe(subscriptions())
        status["connected"] = True
        status["last_reason"] = "connected"
        print(
            f"[MQTT] conectado TLS a {config['host']}:{config['port']} y suscrito a lecturas/estado",
            flush=True,
        )

        if _as_bool(os.getenv("MQTT_SELF_TEST"), False) and not status.get("self_test_sent"):
            household_id = int(os.getenv("MQTT_SELF_TEST_HOUSEHOLD_ID", "1"))
            timezone = ZoneInfo(app.config.get("APP_TIMEZONE", "America/Bogota"))
            payload = {
                "caudal_lpm": 0.123,
                "volumen_l": 0.020,
                "recorded_at": datetime.now(timezone).isoformat(timespec="seconds"),
                "diagnostico": "mqtt_self_test",
            }
            result = mqtt_client.publish(
                readings_topic(household_id),
                json.dumps(payload),
                qos=1,
                retain=False,
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                status["self_test_sent"] = True
                print(
                    f"[MQTT] autoprueba publicada en {readings_topic(household_id)}",
                    flush=True,
                )
            else:
                print(f"[MQTT] no se pudo publicar autoprueba, rc={result.rc}", flush=True)

    def on_disconnect(mqtt_client, userdata, disconnect_flags, reason_code, properties):
        status["connected"] = False
        status["last_reason"] = f"disconnect:{reason_code}"
        print(f"[MQTT] desconectado, código={reason_code}", flush=True)

    def on_message(mqtt_client, userdata, message):
        try:
            with app.app_context():
                handle_message(message.topic, message.payload)
            print(f"[MQTT] mensaje procesado: {message.topic}", flush=True)
        except ValueError as exc:
            print(f"[MQTT] mensaje descartado [{message.topic}]: {exc}", flush=True)
        except Exception as exc:
            print(f"[MQTT] error procesando [{message.topic}]: {exc}", flush=True)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    return client, config


def start_mqtt(app):
    config = mqtt_config()
    status = _status(app)

    if not config["enabled"]:
        status.update(
            {
                "enabled": False,
                "connected": False,
                "host": None,
                "port": None,
                "last_reason": "disabled",
            }
        )
        print("[MQTT] desactivado (MQTT_ENABLED=false)", flush=True)
        return None

    if app.extensions.get("aquahogar_mqtt"):
        return app.extensions["aquahogar_mqtt"]

    client, config = build_client(app)
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(config["host"], config["port"], keepalive=config["keepalive"])
    client.loop_start()
    app.extensions["aquahogar_mqtt"] = client
    print("[MQTT] cliente iniciado en segundo plano", flush=True)
    return client
