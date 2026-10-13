import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import psycopg
from psycopg.rows import dict_row

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Falta DATABASE_URL en .env")

admin_email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
admin_password = os.getenv("ADMIN_PASSWORD") or ""
user_email = (os.getenv("DEMO_USER_EMAIL") or "").strip().lower()
user_password = os.getenv("DEMO_USER_PASSWORD") or ""

if not all([admin_email, admin_password, user_email, user_password]):
    raise SystemExit(
        "Configura ADMIN_EMAIL, ADMIN_PASSWORD, DEMO_USER_EMAIL y DEMO_USER_PASSWORD. "
        "Render solicita estos valores porque están definidos como sync:false."
    )

TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Bogota"))

with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM households ORDER BY id LIMIT 1")
        household = cur.fetchone()
        if household:
            household_id = household["id"]
        else:
            cur.execute(
                """
                INSERT INTO households(
                    name, daily_goal_liters, anomaly_threshold_percent,
                    leak_flow_threshold_l_min, leak_duration_minutes
                ) VALUES ('Hogar piloto AquaHogar', 310, 20, 0.30, 30)
                RETURNING id
                """
            )
            household_id = cur.fetchone()["id"]

        users = [
            (os.getenv("ADMIN_NAME", "Administrador AquaHogar"), admin_email, admin_password, "admin"),
            (os.getenv("DEMO_USER_NAME", "Usuario AquaHogar"), user_email, user_password, "usuario"),
        ]
        for name, email, password, role in users:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users(household_id,name,email,password_hash,role) VALUES (%s,%s,%s,%s,%s)",
                    (household_id, name, email, generate_password_hash(password), role),
                )

        cur.execute("SELECT id FROM sensors WHERE household_id=%s", (household_id,))
        sensor = cur.fetchone()
        if sensor:
            sensor_id = sensor["id"]
        else:
            cur.execute(
                """
                INSERT INTO sensors(household_id, code, name, sensor_type, installation_point, active, installed_at)
                VALUES (%s, 'ESP32-PRINCIPAL-01', 'Caudalimetro principal', 'flujo', 'acometida_principal', TRUE, NOW())
                RETURNING id
                """,
                (household_id,),
            )
            sensor_id = cur.fetchone()["id"]

        cur.execute("SELECT COUNT(*) AS total FROM readings WHERE sensor_id=%s", (sensor_id,))
        if cur.fetchone()["total"] == 0:
            today = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            day_patterns = [
                [(7, 10, 7.4, 88), (13, 10, 4.0, 42), (21, 30, 3.0, 72)],
                [(6, 50, 7.1, 84), (12, 40, 3.8, 39), (19, 0, 6.4, 108)],
                [(7, 5, 7.5, 91), (13, 0, 4.2, 44), (18, 20, 7.8, 98)],
                [(6, 45, 6.9, 82), (12, 15, 3.7, 40), (22, 10, 2.1, 132)],
                [(7, 15, 7.7, 96), (13, 25, 4.1, 45), (18, 0, 6.8, 116)],
                [(7, 10, 7.2, 90), (13, 30, 4.0, 43), (20, 0, 5.9, 105)],
                [(6, 50, 7.6, 102), (12, 20, 4.4, 49), (18, 40, 8.1, 168)],
            ]
            for day_offset, pattern in enumerate(day_patterns):
                base = today - timedelta(days=6-day_offset)
                for hour, minute, flow, volume in pattern:
                    recorded_at = base.replace(hour=hour, minute=minute)
                    cur.execute(
                        """
                        INSERT INTO readings(sensor_id, recorded_at, flow_l_min, volume_liters, source)
                        VALUES (%s,%s,%s,%s,'simulador')
                        ON CONFLICT (sensor_id, recorded_at, source) DO NOTHING
                        """,
                        (sensor_id, recorded_at, flow, volume),
                    )
    conn.commit()

print("Seed completado: hogar piloto, dos usuarios y un único caudalímetro en la acometida principal.")
