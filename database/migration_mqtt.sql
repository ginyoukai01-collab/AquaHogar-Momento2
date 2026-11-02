BEGIN;

ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS origen_mqtt BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE sensors
    ADD COLUMN IF NOT EXISTS en_linea BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ultima_conexion TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS estado_valvula VARCHAR(8);

ALTER TABLE sensors DROP CONSTRAINT IF EXISTS sensors_estado_valvula_check;
ALTER TABLE sensors
    ADD CONSTRAINT sensors_estado_valvula_check
    CHECK (estado_valvula IS NULL OR estado_valvula IN ('abierta', 'cerrada'));

ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS origen VARCHAR(10) NOT NULL DEFAULT 'regla',
    ADD COLUMN IF NOT EXISTS puntaje NUMERIC(6,4);

ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_origen_check;
ALTER TABLE alerts
    ADD CONSTRAINT alerts_origen_check
    CHECK (origen IN ('regla', 'modelo'));

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

CREATE INDEX IF NOT EXISTS idx_readings_mqtt
    ON readings(sensor_id, recorded_at DESC) WHERE origen_mqtt = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_origen
    ON alerts(household_id, origen, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comandos_household_estado
    ON comandos(household_id, estado, enviado_en DESC);

COMMIT;
