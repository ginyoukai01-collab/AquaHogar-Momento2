import pickle
from datetime import timedelta

import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.db import execute, fetch_all, fetch_one
from backend.realtime import publish_event

FEATURE_COLUMNS = [
    "litros",
    "caudal_medio",
    "caudal_min",
    "caudal_max",
    "hora",
    "fin_semana",
]
MIN_WINDOWS = 7 * 96
MODEL_VERSION = 1


def _rows_for_household(household_id):
    return fetch_all(
        """
        SELECT r.id, r.recorded_at, r.flow_l_min, r.volume_liters
        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s
          AND r.origen_mqtt=TRUE
        ORDER BY r.recorded_at ASC
        """,
        (household_id,),
    )


def _feature_frame(rows):
    if not rows:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    frame = pd.DataFrame(
        [
            {
                "recorded_at": row["recorded_at"],
                "flow_l_min": float(row["flow_l_min"]),
                "volume_liters": float(row["volume_liters"]),
            }
            for row in rows
        ]
    )
    frame["recorded_at"] = pd.to_datetime(frame["recorded_at"], utc=True)
    frame = frame.set_index("recorded_at").sort_index()

    windows = frame.resample("15min").agg(
        litros=("volume_liters", "sum"),
        caudal_medio=("flow_l_min", "mean"),
        caudal_min=("flow_l_min", "min"),
        caudal_max=("flow_l_min", "max"),
    )
    # No inventar ventanas donde no hubo telemetría.
    windows = windows.dropna(subset=["caudal_medio", "caudal_min", "caudal_max"])
    windows["hora"] = windows.index.hour + (windows.index.minute / 60.0)
    windows["fin_semana"] = (windows.index.dayofweek >= 5).astype(int)
    return windows[FEATURE_COLUMNS]


def model_status(household_id):
    row = fetch_one(
        "SELECT muestras, entrenado_en FROM modelos_anomalia WHERE household_id=%s",
        (household_id,),
    )
    if row:
        return {
            "trained": True,
            "samples": int(row["muestras"]),
            "trained_at": row["entrenado_en"],
        }

    rows = _rows_for_household(household_id)
    windows = _feature_frame(rows)
    return {
        "trained": False,
        "samples": len(windows),
        "required": MIN_WINDOWS,
    }


def train_household_model(household_id):
    rows = _rows_for_household(household_id)
    windows = _feature_frame(rows)
    if len(windows) < MIN_WINDOWS:
        return {
            "trained": False,
            "samples": len(windows),
            "required": MIN_WINDOWS,
        }

    model = IsolationForest(
        n_estimators=200,
        contamination=0.02,
        random_state=42,
        n_jobs=1,
    )
    model.fit(windows[FEATURE_COLUMNS])

    bundle = {
        "version": MODEL_VERSION,
        "columns": FEATURE_COLUMNS,
        "model": model,
    }
    payload = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
    execute(
        """
        INSERT INTO modelos_anomalia(household_id, modelo, muestras, entrenado_en)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (household_id)
        DO UPDATE SET modelo=EXCLUDED.modelo,
                      muestras=EXCLUDED.muestras,
                      entrenado_en=NOW()
        """,
        (household_id, payload, len(windows)),
    )
    return {"trained": True, "samples": len(windows)}


def _load_model(household_id):
    row = fetch_one(
        "SELECT modelo, muestras, entrenado_en FROM modelos_anomalia WHERE household_id=%s",
        (household_id,),
    )
    if not row:
        return None
    bundle = pickle.loads(bytes(row["modelo"]))
    if bundle.get("version") != MODEL_VERSION:
        return None
    return bundle


def _latest_window(household_id, recorded_at):
    start = recorded_at.replace(minute=(recorded_at.minute // 15) * 15, second=0, microsecond=0)
    end = start + timedelta(minutes=15)
    rows = fetch_all(
        """
        SELECT r.recorded_at, r.flow_l_min, r.volume_liters
        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s
          AND r.origen_mqtt=TRUE
          AND r.recorded_at >= %s
          AND r.recorded_at < %s
        ORDER BY r.recorded_at ASC
        """,
        (household_id, start, end),
    )
    windows = _feature_frame(rows)
    if windows.empty:
        return None
    return windows.iloc[[-1]]


def _explanation(window):
    row = window.iloc[0]
    hour = float(row["hora"])
    min_flow = float(row["caudal_min"])
    liters = float(row["litros"])
    if 0 <= hour < 5 and min_flow >= 0.3:
        return (
            f"Patrón anómalo nocturno: caudal mínimo continuo de "
            f"{min_flow:.2f} L/min y {liters:.2f} L en la ventana."
        )
    return (
        f"La ventana de 15 minutos se aparta del patrón histórico del hogar "
        f"(caudal medio {float(row['caudal_medio']):.2f} L/min, {liters:.2f} L)."
    )


def evaluate_latest_window(household_id, reading):
    bundle = _load_model(household_id)
    if bundle is None:
        # Entrenar automáticamente cuando ya exista una semana completa de ventanas.
        training = train_household_model(household_id)
        if not training.get("trained"):
            return {"evaluated": False, **training}
        bundle = _load_model(household_id)
        if bundle is None:
            return {"evaluated": False, "trained": False}

    window = _latest_window(household_id, reading["recorded_at"])
    if window is None:
        return {"evaluated": False, "trained": True}

    model = bundle["model"]
    prediction = int(model.predict(window[FEATURE_COLUMNS])[0])
    score = float(model.decision_function(window[FEATURE_COLUMNS])[0])
    anomaly = prediction == -1

    if anomaly:
        message = _explanation(window)
        execute(
            """
            INSERT INTO alerts(
                household_id, reading_id, alert_type, severity, title, message,
                alert_date, status, origen, puntaje
            )
            VALUES (%s, %s, 'anomalia_modelo', 'alta',
                    'Anomalía detectada por el modelo', %s, %s,
                    'activa', 'modelo', %s)
            ON CONFLICT (household_id, alert_type, alert_date)
            DO UPDATE SET
                reading_id=EXCLUDED.reading_id,
                severity='alta',
                title=EXCLUDED.title,
                message=EXCLUDED.message,
                status='activa',
                resolved_at=NULL,
                origen='modelo',
                puntaje=EXCLUDED.puntaje
            """,
            (
                household_id,
                reading["id"],
                message,
                reading["recorded_at"].date(),
                round(score, 4),
            ),
        )
        publish_event(
            household_id,
            {
                "tipo": "alerta_modelo",
                "reading_id": reading["id"],
                "puntaje": round(score, 4),
                "mensaje": message,
            },
        )

    return {
        "evaluated": True,
        "trained": True,
        "anomaly": anomaly,
        "score": score,
    }
