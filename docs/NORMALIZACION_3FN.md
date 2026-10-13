# Justificación de normalización - AquaHogar

## Objetivo

Evitar redundancia y anomalías de inserción, actualización y eliminación sin perder la trazabilidad del consumo total del inmueble.

## Entidades

- **households**: configuración propia del inmueble y de su estrategia de monitoreo.
- **users**: personas con acceso al hogar; la autenticación no se mezcla con telemetría.
- **sensors**: dispositivo físico único del inmueble.
- **readings**: eventos de telemetría producidos por el sensor.
- **alerts**: hallazgos derivados de las lecturas y asociados al hogar.

## 1FN

Todos los campos son atómicos. No existen columnas del tipo `lectura_1`, `lectura_2` ni arreglos de usuarios/sensores dentro de una misma fila.

## 2FN

Cada entidad usa una llave primaria simple (`id`). Por tanto, todo atributo no llave depende de la llave completa de su fila.

## 3FN

No se mantienen dependencias transitivas innecesarias:

- una lectura almacena `sensor_id`, no vuelve a copiar el hogar ni los datos descriptivos del sensor;
- el sensor referencia el hogar y no repite la configuración de consumo;
- el usuario referencia el hogar y no duplica los atributos del inmueble;
- las alertas almacenan su evidencia histórica y referencias, pero no duplican credenciales, configuración del sensor ni valores de telemetría.

## Regla de negocio central

`sensors.household_id` es `UNIQUE`. Esto impide que un hogar tenga más de un caudalímetro dentro del modelo actual y hace que el esquema coincida con la arquitectura física implementada.
