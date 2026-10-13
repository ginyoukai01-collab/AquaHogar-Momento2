-- AquaHogar - datos de demostracion para PostgreSQL
-- SOLO EVALUACION / DESARROLLO. No usar estas credenciales en produccion.
-- Admin:   admin@aquahogar.demo / AquaAdmin2026!
-- Usuario: usuario@aquahogar.demo / AquaUsuario2026!
-- Aplicar primero database/schema.sql.

BEGIN;
TRUNCATE TABLE alerts, readings, sensors, users, households RESTART IDENTITY CASCADE;

INSERT INTO households(
    id, name, daily_goal_liters, anomaly_threshold_percent,
    leak_flow_threshold_l_min, leak_duration_minutes
) VALUES (1, 'Hogar piloto AquaHogar', 310.00, 20.00, 0.30, 30);

INSERT INTO users(id, household_id, name, email, password_hash, role, active)
VALUES
(1, 1, 'Administrador AquaHogar', 'admin@aquahogar.demo', 'pbkdf2:sha256:600000$AquaAdminSalt$91d015f923eda2ddaadbf4ad868d41f79a1c8effaf1752fe50b89d52a5155054', 'admin', TRUE),
(2, 1, 'Usuario AquaHogar', 'usuario@aquahogar.demo', 'pbkdf2:sha256:600000$AquaUserSalt$e32a07dc4aab9a56f4a9d9fca6934b8c91cfe2833d47f8cae8e7008a09feedad', 'usuario', TRUE);

INSERT INTO sensors(
    id, household_id, code, name, sensor_type,
    installation_point, active, installed_at
) VALUES (
    1, 1, 'ESP32-PRINCIPAL-01', 'Caudalimetro principal', 'flujo',
    'acometida_principal', TRUE, '2026-10-01 09:00:00-05'
);

INSERT INTO readings(sensor_id, recorded_at, flow_l_min, volume_liters, source, created_by_user_id)
VALUES
(1, '2026-10-06 07:00:00-05', 7.40, 88.00, 'simulador', NULL),
(1, '2026-10-06 13:10:00-05', 4.00, 42.00, 'simulador', NULL),
(1, '2026-10-06 21:30:00-05', 3.00, 72.00, 'simulador', NULL),
(1, '2026-10-07 06:50:00-05', 7.10, 84.00, 'simulador', NULL),
(1, '2026-10-07 12:40:00-05', 3.80, 39.00, 'simulador', NULL),
(1, '2026-10-07 19:00:00-05', 6.40, 108.00, 'simulador', NULL),
(1, '2026-10-08 07:05:00-05', 7.50, 91.00, 'simulador', NULL),
(1, '2026-10-08 13:00:00-05', 4.20, 44.00, 'simulador', NULL),
(1, '2026-10-08 18:20:00-05', 7.80, 98.00, 'simulador', NULL),
(1, '2026-10-09 06:45:00-05', 6.90, 82.00, 'simulador', NULL),
(1, '2026-10-09 12:15:00-05', 3.70, 40.00, 'simulador', NULL),
(1, '2026-10-09 22:10:00-05', 2.10, 132.00, 'simulador', NULL),
(1, '2026-10-10 07:15:00-05', 7.70, 96.00, 'simulador', NULL),
(1, '2026-10-10 13:25:00-05', 4.10, 45.00, 'simulador', NULL),
(1, '2026-10-10 18:00:00-05', 6.80, 116.00, 'simulador', NULL),
(1, '2026-10-11 07:10:00-05', 7.20, 90.00, 'simulador', NULL),
(1, '2026-10-11 13:30:00-05', 4.00, 43.00, 'simulador', NULL),
(1, '2026-10-11 20:00:00-05', 5.90, 105.00, 'simulador', NULL),
(1, '2026-10-12 06:50:00-05', 7.60, 102.00, 'simulador', NULL),
(1, '2026-10-12 12:20:00-05', 4.40, 49.00, 'simulador', NULL),
(1, '2026-10-12 18:40:00-05', 8.10, 168.00, 'simulador', NULL);

INSERT INTO alerts(
    household_id, reading_id, alert_type, severity, title, message,
    alert_date, status, created_at
) VALUES (
    1, 21, 'consumo_inusual', 'media',
    'Consumo total inusual detectado',
    'Consumo superior al patron habitual. Revisa los usos recientes del hogar y descarta fugas generales.',
    '2026-10-12', 'activa', '2026-10-12 18:41:00-05'
);

SELECT setval(pg_get_serial_sequence('households','id'), (SELECT MAX(id) FROM households));
SELECT setval(pg_get_serial_sequence('users','id'), (SELECT MAX(id) FROM users));
SELECT setval(pg_get_serial_sequence('sensors','id'), (SELECT MAX(id) FROM sensors));
SELECT setval(pg_get_serial_sequence('readings','id'), (SELECT MAX(id) FROM readings));
SELECT setval(pg_get_serial_sequence('alerts','id'), (SELECT MAX(id) FROM alerts));
COMMIT;
