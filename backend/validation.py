import re
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import current_app

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean_text(value, max_length=120):
    value = (value or "").strip()
    if len(value) > max_length:
        raise ValueError(f"El texto supera {max_length} caracteres.")
    return value


def validate_email(value):
    email = clean_text(value, 180).lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Ingresa un correo electrónico válido.")
    return email


def validate_password(value):
    password = value or ""
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("La contraseña debe contener letras y números.")
    return password


def bounded_float(value, field_name, minimum=0.0, maximum=None, strictly_positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} debe ser numérico.")
    if strictly_positive and number <= minimum:
        raise ValueError(f"{field_name} debe ser mayor que {minimum}.")
    if not strictly_positive and number < minimum:
        raise ValueError(f"{field_name} no puede ser menor que {minimum}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field_name} supera el máximo permitido ({maximum}).")
    return number


def positive_float(value, field_name, max_value=None):
    return bounded_float(value, field_name, 0.0, max_value, strictly_positive=True)


def nonnegative_float(value, field_name, max_value=None):
    return bounded_float(value, field_name, 0.0, max_value, strictly_positive=False)


def parse_datetime(date_value, time_value):
    try:
        naive = datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        raise ValueError("Fecha u hora inválida.")
    timezone = current_app.config.get("APP_TIMEZONE", "America/Bogota")
    try:
        return naive.replace(tzinfo=ZoneInfo(timezone))
    except Exception:
        return naive.replace(tzinfo=ZoneInfo("UTC"))
