from datetime import timedelta
from statistics import mean

from backend.db import fetch_one, fetch_all, execute
from backend.services.analytics import (
    daily_consumption_anomaly,
    possible_continuous_flow,
    recommendation_for,
)


def create_reading(*, household_id, sensor_id, recorded_at, flow_l_min, volume_liters, source, created_by_user_id=None):
    sensor = fetch_one(
        """
        SELECT s.id, s.code, s.household_id, s.name, s.installation_point, s.active,
               h.daily_goal_liters, h.anomaly_threshold_percent,
               h.leak_flow_threshold_l_min, h.leak_duration_minutes
        FROM sensors s
        JOIN households h ON h.id = s.household_id
        WHERE s.id = %s AND s.active = TRUE
        """,
        (sensor_id,),
    )
    if not sensor or sensor["household_id"] != household_id:
        raise ValueError("El caudalímetro principal no pertenece al hogar activo o está inactivo.")

    duplicate = fetch_one(
        """
        SELECT id FROM readings
        WHERE sensor_id=%s AND recorded_at=%s AND source=%s
        """,
        (sensor_id, recorded_at, source),
    )
    if duplicate:
        raise ValueError("Ya existe una lectura para ese sensor, fecha/hora y origen.")

    reading = execute(
        """
        INSERT INTO readings(sensor_id, recorded_at, flow_l_min, volume_liters, source, created_by_user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, sensor_id, recorded_at, flow_l_min, volume_liters, source
        """,
        (sensor_id, recorded_at, flow_l_min, volume_liters, source, created_by_user_id),
        returning=True,
    )

    _evaluate_household_alerts(sensor, reading)
    return reading


def _evaluate_household_alerts(sensor, reading):
    household_id = sensor["household_id"]
    recorded_at = reading["recorded_at"]
    day_start = recorded_at.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    current = fetch_one(
        """
        SELECT COALESCE(SUM(r.volume_liters), 0) AS total
        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s AND r.recorded_at >= %s AND r.recorded_at < %s
        """,
        (household_id, day_start, day_end),
    )
    current_total = float(current["total"] or 0)

    previous_rows = fetch_all(
        """
        SELECT DATE(r.recorded_at) AS day, SUM(r.volume_liters) AS total
        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s
          AND r.recorded_at >= %s
          AND r.recorded_at < %s
        GROUP BY DATE(r.recorded_at)
        ORDER BY day
        """,
        (household_id, day_start - timedelta(days=7), day_start),
    )
    baseline_values = [float(row["total"]) for row in previous_rows if float(row["total"] or 0) > 0]
    baseline = mean(baseline_values) if baseline_values else 0.0

    severity = daily_consumption_anomaly(
        current_total,
        baseline,
        sensor["daily_goal_liters"],
        sensor["anomaly_threshold_percent"],
    )
    if severity:
        _upsert_alert(
            household_id=household_id,
            reading_id=reading["id"],
            alert_type="consumo_inusual",
            severity=severity,
            title="Consumo total inusual detectado",
            message=recommendation_for("consumo_inusual", severity),
            alert_date=recorded_at.date(),
        )

    window_start = recorded_at - timedelta(minutes=int(sensor["leak_duration_minutes"]))
    recent = fetch_all(
        """
        SELECT r.recorded_at, r.flow_l_min
        FROM readings r
        WHERE r.sensor_id=%s AND r.recorded_at BETWEEN %s AND %s
        ORDER BY r.recorded_at ASC
        """,
        (sensor["id"], window_start, recorded_at),
    )
    if possible_continuous_flow(
        recent,
        sensor["leak_flow_threshold_l_min"],
        sensor["leak_duration_minutes"],
    ):
        _upsert_alert(
            household_id=household_id,
            reading_id=reading["id"],
            alert_type="posible_fuga",
            severity="alta",
            title="Posible fuga general",
            message=recommendation_for("posible_fuga", "alta"),
            alert_date=recorded_at.date(),
        )


def _upsert_alert(*, household_id, reading_id, alert_type, severity, title, message, alert_date):
    execute(
        """
        INSERT INTO alerts(household_id, reading_id, alert_type, severity, title, message, alert_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'activa')
        ON CONFLICT (household_id, alert_type, alert_date)
        DO UPDATE SET
            reading_id=EXCLUDED.reading_id,
            severity=EXCLUDED.severity,
            title=EXCLUDED.title,
            message=EXCLUDED.message,
            status='activa',
            resolved_at=NULL
        """,
        (household_id, reading_id, alert_type, severity, title, message, alert_date),
    )
