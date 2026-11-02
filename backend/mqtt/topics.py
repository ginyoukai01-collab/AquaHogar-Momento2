BASE_TOPIC = "aquahogar"


def readings_topic(household_id):
    return f"{BASE_TOPIC}/{int(household_id)}/lecturas"


def state_topic(household_id):
    return f"{BASE_TOPIC}/{int(household_id)}/estado"


def commands_topic(household_id):
    return f"{BASE_TOPIC}/{int(household_id)}/comandos"


def subscriptions():
    return [
        (f"{BASE_TOPIC}/+/lecturas", 1),
        (f"{BASE_TOPIC}/+/estado", 1),
    ]


def parse_topic(topic):
    parts = str(topic).split("/")
    if len(parts) != 3 or parts[0] != BASE_TOPIC:
        raise ValueError("Tópico MQTT no reconocido")
    try:
        household_id = int(parts[1])
    except ValueError as exc:
        raise ValueError("El identificador de hogar del tópico es inválido") from exc
    message_type = parts[2]
    if message_type not in {"lecturas", "estado", "comandos"}:
        raise ValueError("Tipo de tópico MQTT no soportado")
    return household_id, message_type
