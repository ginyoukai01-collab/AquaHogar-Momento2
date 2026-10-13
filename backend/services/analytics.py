from collections import defaultdict
from statistics import mean


def summarize_readings(readings, daily_goal=310.0):
    """Resume el consumo total del inmueble medido en la acometida principal."""
    by_day = defaultdict(float)
    by_hour = defaultdict(float)

    for row in readings:
        recorded_at = row["recorded_at"]
        volume = float(row["volume_liters"])
        by_day[recorded_at.date().isoformat()] += volume
        by_hour[recorded_at.hour] += volume

    daily = [{"date": d, "liters": round(v, 2)} for d, v in sorted(by_day.items())]
    values = [d["liters"] for d in daily]
    latest_day = values[-1] if values else 0.0
    previous = values[-8:-1]
    baseline = mean(previous) if previous else 0.0
    delta = ((latest_day - baseline) / baseline * 100) if baseline else 0.0
    week = sum(values[-7:])
    month = sum(values[-30:])
    status = "critico" if delta > 25 else "alerta" if delta > 10 else "normal"
    potential_saving = max(0.0, latest_day - float(daily_goal))

    energy_factor_kwh_per_l = 0.0005
    co2_factor_kg_per_kwh = 0.164

    hourly = [
        {"hour": f"{hour:02d}:00", "liters": round(by_hour.get(hour, 0.0), 2)}
        for hour in range(24)
        if by_hour.get(hour, 0.0) > 0
    ]

    return {
        "today": round(latest_day, 2),
        "week": round(week, 2),
        "month": round(month, 2),
        "baseline": round(baseline, 2),
        "delta": round(delta, 2),
        "status": status,
        "daily": daily[-14:],
        "hourly": hourly,
        "potential_saving_liters": round(potential_saving, 2),
        "estimated_energy_kwh": round(potential_saving * energy_factor_kwh_per_l, 4),
        "estimated_co2_kg": round(potential_saving * energy_factor_kwh_per_l * co2_factor_kg_per_kwh, 4),
    }


def daily_consumption_anomaly(current_total, baseline, daily_goal, threshold_percent=20.0):
    reference = float(baseline) if baseline and float(baseline) > 0 else float(daily_goal)
    if reference <= 0:
        return None
    ratio = float(current_total) / reference
    medium_ratio = 1 + (float(threshold_percent) / 100.0)
    high_ratio = 1 + (float(threshold_percent) * 2 / 100.0)
    if ratio >= high_ratio:
        return "alta"
    if ratio >= medium_ratio:
        return "media"
    return None


def possible_continuous_flow(recent_readings, minimum_flow_l_min, duration_minutes):
    rows = sorted(recent_readings, key=lambda r: r["recorded_at"])
    if len(rows) < 2:
        return False
    threshold = float(minimum_flow_l_min)
    if any(float(r["flow_l_min"]) < threshold for r in rows):
        return False
    elapsed_minutes = (rows[-1]["recorded_at"] - rows[0]["recorded_at"]).total_seconds() / 60.0
    return elapsed_minutes >= float(duration_minutes) * 0.8


def recommendation_for(alert_type, severity):
    if alert_type == "posible_fuga":
        return (
            "Se detectó flujo persistente en la acometida principal. Revisa llaves, sanitarios, "
            "grifos y conexiones internas; si no existe un uso intencional, considera cerrar la llave "
            "de paso y verificar una posible fuga."
        )
    prefix = "Consumo crítico detectado. " if severity == "alta" else "Consumo superior al patrón habitual. "
    return prefix + (
        "Revisa los usos recientes del hogar y descarta fugas generales. Compara el consumo del día "
        "con tu promedio y aplica acciones de ahorro donde sea posible."
    )
