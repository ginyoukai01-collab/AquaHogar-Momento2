BEGIN;

CREATE TABLE IF NOT EXISTS households (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    daily_goal_liters NUMERIC(10,2) NOT NULL DEFAULT 310.00
        CHECK (daily_goal_liters > 0 AND daily_goal_liters <= 10000),
    anomaly_threshold_percent NUMERIC(5,2) NOT NULL DEFAULT 20.00
        CHECK (anomaly_threshold_percent > 0 AND anomaly_threshold_percent <= 200),
    leak_flow_threshold_l_min NUMERIC(8,2) NOT NULL DEFAULT 0.30
        CHECK (leak_flow_threshold_l_min >= 0 AND leak_flow_threshold_l_min <= 500),
    leak_duration_minutes INTEGER NOT NULL DEFAULT 30
        CHECK (leak_duration_minutes BETWEEN 5 AND 240),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL
        REFERENCES households(id) ON UPDATE CASCADE ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'usuario'
        CHECK (role IN ('admin', 'usuario')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sensors (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL UNIQUE
        REFERENCES households(id) ON UPDATE CASCADE ON DELETE CASCADE,
    code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL DEFAULT 'Caudalimetro principal',
    sensor_type VARCHAR(30) NOT NULL DEFAULT 'flujo'
        CHECK (sensor_type = 'flujo'),
    installation_point VARCHAR(60) NOT NULL DEFAULT 'acometida_principal'
        CHECK (installation_point = 'acometida_principal'),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    installed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS readings (
    id BIGSERIAL PRIMARY KEY,
    sensor_id BIGINT NOT NULL
        REFERENCES sensors(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL,
    flow_l_min NUMERIC(10,2) NOT NULL
        CHECK (flow_l_min >= 0 AND flow_l_min <= 500),
    volume_liters NUMERIC(12,2) NOT NULL
        CHECK (volume_liters >= 0 AND volume_liters <= 10000),
    source VARCHAR(20) NOT NULL
        CHECK (source IN ('manual', 'iot', 'simulador')),
    created_by_user_id BIGINT
        REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(sensor_id, recorded_at, source)
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL
        REFERENCES households(id) ON UPDATE CASCADE ON DELETE CASCADE,
    reading_id BIGINT
        REFERENCES readings(id) ON UPDATE CASCADE ON DELETE SET NULL,
    alert_type VARCHAR(30) NOT NULL
        CHECK (alert_type IN ('consumo_inusual', 'posible_fuga', 'anomalia_modelo')),
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('media', 'alta')),
    title VARCHAR(140) NOT NULL,
    message TEXT NOT NULL,
    alert_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'activa'
        CHECK (status IN ('activa', 'resuelta')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(household_id, alert_type, alert_date),
    CHECK (
        (status = 'activa' AND resolved_at IS NULL)
        OR
        (status = 'resuelta' AND resolved_at IS NOT NULL)
    )
);

ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS origen_mqtt BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE sensors
    ADD COLUMN IF NOT EXISTS en_linea BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ultima_conexion TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS estado_valvula VARCHAR(8);

ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS origen VARCHAR(10) NOT NULL DEFAULT 'regla',
    ADD COLUMN IF NOT EXISTS puntaje NUMERIC(6,4);

CREATE TABLE IF NOT EXISTS modelos_anomalia (
    household_id BIGINT PRIMARY KEY
        REFERENCES households(id) ON UPDATE CASCADE ON DELETE CASCADE,
    modelo BYTEA NOT NULL,
    muestras INTEGER NOT NULL CHECK (muestras >= 0),
    entrenado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comandos (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL
        REFERENCES households(id) ON UPDATE CASCADE ON DELETE CASCADE,
    usuario_id BIGINT NOT NULL
        REFERENCES users(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    accion VARCHAR(20) NOT NULL
        CHECK (accion IN ('cerrar_valvula', 'abrir_valvula', 'reiniciar')),
    estado VARCHAR(12) NOT NULL DEFAULT 'enviado'
        CHECK (estado IN ('enviado', 'confirmado', 'fallido')),
    enviado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmado_en TIMESTAMPTZ
);

ALTER TABLE readings DROP CONSTRAINT IF EXISTS readings_flow_l_min_check;
ALTER TABLE readings
    ADD CONSTRAINT readings_flow_l_min_check
    CHECK (flow_l_min >= 0 AND flow_l_min <= 500);
ALTER TABLE readings DROP CONSTRAINT IF EXISTS readings_volume_liters_check;
ALTER TABLE readings
    ADD CONSTRAINT readings_volume_liters_check
    CHECK (volume_liters >= 0 AND volume_liters <= 10000);

ALTER TABLE sensors DROP CONSTRAINT IF EXISTS sensors_estado_valvula_check;
ALTER TABLE sensors
    ADD CONSTRAINT sensors_estado_valvula_check
    CHECK (estado_valvula IS NULL OR estado_valvula IN ('abierta', 'cerrada'));

ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_origen_check;
ALTER TABLE alerts
    ADD CONSTRAINT alerts_origen_check
    CHECK (origen IN ('regla', 'modelo'));

ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_alert_type_check;
ALTER TABLE alerts
    ADD CONSTRAINT alerts_alert_type_check
    CHECK (alert_type IN ('consumo_inusual', 'posible_fuga', 'anomalia_modelo'));

CREATE INDEX IF NOT EXISTS idx_users_household
    ON users(household_id);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_recorded
    ON readings(sensor_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_mqtt
    ON readings(sensor_id, recorded_at DESC) WHERE origen_mqtt = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_household_status
    ON alerts(household_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_reading
    ON alerts(reading_id) WHERE reading_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_alerts_origen
    ON alerts(household_id, origen, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comandos_household_estado
    ON comandos(household_id, estado, enviado_en DESC);

COMMIT;
