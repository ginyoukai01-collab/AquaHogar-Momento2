import ssl

import paho.mqtt.client as mqtt

from backend.mqtt.config import mqtt_config, validate_mqtt_config
from backend.mqtt.handlers import handle_message
from backend.mqtt.topics import subscriptions


def build_client(app):
    config = mqtt_config()
    validate_mqtt_config(config)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=config["client_id"],
        protocol=mqtt.MQTTv311,
    )
    client.username_pw_set(config["user"], config["password"])
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

    def on_connect(mqtt_client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            app.logger.error("MQTT no pudo conectarse. Código: %s", reason_code)
            return
        mqtt_client.subscribe(subscriptions())
        app.logger.info(
            "MQTT conectado a %s:%s y suscrito a lecturas/estado",
            config["host"],
            config["port"],
        )

    def on_disconnect(mqtt_client, userdata, disconnect_flags, reason_code, properties):
        if reason_code != 0:
            app.logger.warning("MQTT desconectado inesperadamente. Código: %s", reason_code)
        else:
            app.logger.info("MQTT desconectado")

    def on_message(mqtt_client, userdata, message):
        try:
            with app.app_context():
                handle_message(message.topic, message.payload)
        except ValueError as exc:
            app.logger.warning("Mensaje MQTT descartado [%s]: %s", message.topic, exc)
        except Exception:
            app.logger.exception("Error procesando mensaje MQTT [%s]", message.topic)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    return client, config


def start_mqtt(app):
    config = mqtt_config()
    if not config["enabled"]:
        app.logger.info("MQTT desactivado (MQTT_ENABLED=false)")
        return None

    if app.extensions.get("aquahogar_mqtt"):
        return app.extensions["aquahogar_mqtt"]

    client, config = build_client(app)
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(config["host"], config["port"], keepalive=config["keepalive"])
    client.loop_start()
    app.extensions["aquahogar_mqtt"] = client
    app.logger.info("Cliente MQTT iniciado en segundo plano")
    return client
