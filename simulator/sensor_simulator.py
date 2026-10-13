import os
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("AQUAHOGAR_API_URL", "http://127.0.0.1:5000/api/iot/lecturas")
API_KEY = os.getenv("IOT_API_KEY")
SENSOR_CODE = os.getenv("SENSOR_CODE", "ESP32-PRINCIPAL-01")
TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Bogota"))

if not API_KEY:
    raise SystemExit("Configura IOT_API_KEY antes de ejecutar el simulador.")

print(f"Simulando {SENSOR_CODE} -> {URL}")
print("Ctrl+C para detener.")

while True:
    flow = round(random.uniform(0.4, 9.5), 2)
    volume = round(flow * (5 / 60), 3)
    payload = {
        "sensor_code": SENSOR_CODE,
        "recorded_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "flow_l_min": flow,
        "volume_liters": volume,
    }
    try:
        response = requests.post(
            URL,
            json=payload,
            headers={"X-AquaHogar-Key": API_KEY},
            timeout=10,
        )
        print(response.status_code, payload, response.text[:160])
    except requests.RequestException as exc:
        print("Error de conexión:", exc)
    time.sleep(5)
