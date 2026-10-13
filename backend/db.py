from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from flask import current_app


def _database_url():
    url = current_app.config.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    return url


@contextmanager
def get_connection():
    conn = psycopg.connect(_database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(query, params=()):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetch_all(query, params=()):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def execute(query, params=(), returning=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone() if returning else None
