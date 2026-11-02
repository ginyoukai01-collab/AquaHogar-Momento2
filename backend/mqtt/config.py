import os


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def mqtt_config():
    return {
        "enabled": _as_bool(os.getenv("MQTT_ENABLED"), False),
        "host": (os.getenv("MQTT_HOST") or "").strip(),
        "port": int(os.getenv("MQTT_PORT", "8883")),
        "user": os.getenv("MQTT_USER") or "",
        "password": os.getenv("MQTT_PASS") or "",
        "client_id": os.getenv("MQTT_CLIENT_ID", "aquahogar-backend"),
        "keepalive": int(os.getenv("MQTT_KEEPALIVE", "60")),
    }


def validate_mqtt_config(config):
    if not config.get("enabled"):
        return
    missing = [name for name in ("host", "user", "password") if not config.get(name)]
    if missing:
        raise RuntimeError(
            "MQTT_ENABLED=true pero faltan variables: " + ", ".join(missing)
        )
