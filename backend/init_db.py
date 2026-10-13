from pathlib import Path
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("Falta DATABASE_URL en .env")

schema_path = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
sql = schema_path.read_text(encoding="utf-8")
statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip() and stmt.strip().upper() not in {"BEGIN", "COMMIT"}]

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)
    conn.commit()

print("Esquema PostgreSQL aplicado correctamente.")
