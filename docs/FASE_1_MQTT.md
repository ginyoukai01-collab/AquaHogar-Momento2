# AquaHogar · Fase 1 MQTT

## Objetivo

Preparar AquaHogar para el requerimiento avanzado de telemetría MQTT sin interrumpir el flujo HTTP que ya está operativo en Render.

## Estado implementado

- `paho-mqtt 2.1.0` agregado a dependencias.
- Variables MQTT agregadas a `.env.example`.
- MQTT desactivado por defecto con `MQTT_ENABLED=false`.
- Tópicos centralizados en `backend/mqtt/topics.py`.
- Esquema PostgreSQL ampliado de forma idempotente.
- Migración independiente disponible en `database/migration_mqtt.sql`.
- DBML actualizado con las nuevas entidades.
- Simulador MQTT disponible en `simulator/mqtt_simulator.py`.
- El endpoint HTTP `/api/iot/lecturas` permanece disponible como compatibilidad durante la migración.

## Tópicos

```text
aquahogar/<hogar_id>/lecturas
aquahogar/<hogar_id>/estado
aquahogar/<hogar_id>/comandos
```

Las lecturas y el estado se consumirán con QoS 1. El estado del dispositivo se publica retenido para que un navegador recién abierto conozca inmediatamente si el dispositivo está en línea.

## Cambios en PostgreSQL

### readings

- `origen_mqtt BOOLEAN NOT NULL DEFAULT FALSE`

### sensors

- `en_linea BOOLEAN NOT NULL DEFAULT FALSE`
- `ultima_conexion TIMESTAMPTZ`
- `estado_valvula VARCHAR(8)` (`abierta` o `cerrada`)

### alerts

- `origen VARCHAR(10)` (`regla` o `modelo`)
- `puntaje NUMERIC(6,4)`

### nuevas tablas

- `modelos_anomalia`: almacenará el Isolation Forest serializado y metadatos del entrenamiento por hogar.
- `comandos`: almacena comandos remotos y sus estados `enviado`, `confirmado` o `fallido`.

## Configuración del broker

Cuando se cree el broker TLS (HiveMQ Cloud o EMQX Cloud), configurar en Render:

```env
MQTT_ENABLED=true
MQTT_HOST=<host>
MQTT_PORT=8883
MQTT_USER=<usuario-backend>
MQTT_PASS=<secreto>
MQTT_CLIENT_ID=aquahogar-backend
MQTT_KEEPALIVE=60
```

No subir contraseñas al repositorio.

## Ejecutar el simulador

Configurar un `.env` local con las credenciales del broker y luego:

```bash
python simulator/mqtt_simulator.py
```

Por defecto el simulador avanza 10 minutos simulados por cada segundo real. El patrón incluye picos de consumo en la mañana y la tarde/noche.

Para inyectar una fuga nocturna:

```env
MQTT_SIMULATOR_LEAK_ENABLED=true
MQTT_SIMULATOR_LEAK_START_HOUR=3
MQTT_SIMULATOR_LEAK_FLOW_L_MIN=2.0
```

El simulador también:

- usa TLS;
- publica con QoS 1;
- declara LWT `en_linea=false`;
- publica `en_linea=true` al conectar;
- escucha `aquahogar/<hogar_id>/comandos`;
- simula abrir/cerrar válvula y publica confirmación por el tópico de estado.

## Compatibilidad

Durante esta fase no se inicia todavía el suscriptor MQTT dentro de Flask. Esto evita afectar la versión productiva mientras el broker no esté configurado. La Fase 2 añadirá la ingesta real en Flask y conectará mensajes MQTT con `create_reading()`.

## Próxima fase

1. Crear broker MQTT TLS.
2. Probar credenciales con el simulador.
3. Implementar suscriptor Flask.
4. Guardar lecturas MQTT en PostgreSQL.
5. Procesar LWT y estado de válvula.
6. Añadir SSE al dashboard.
