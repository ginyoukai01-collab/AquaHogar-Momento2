# AquaHogar - Informe de Entrega Momento 2

> **Completar antes de exportar a PDF:** integrantes, fecha, URL Render y capturas reales del despliegue.

## 1. Descripción de la solución

AquaHogar es una aplicación web orientada al monitoreo centralizado del consumo total de agua de un inmueble. La solución utiliza un único caudalímetro instalado en la acometida principal y conectado a un ESP32. El dispositivo transmite lecturas hacia una API desarrollada en Flask; la información se valida y persiste en PostgreSQL para construir históricos, tendencias, alertas y reportes.

La decisión de utilizar un solo punto de medición busca reducir costo, complejidad de instalación y mantenimiento. El sistema no pretende identificar automáticamente qué grifo o ramal interno produjo el consumo; detecta comportamientos anómalos generales y orienta al usuario para realizar una revisión del inmueble.

## 2. Contribución al ODS 13

AquaHogar se articula con el ODS 13 desde la sensibilización climática, la gestión eficiente de recursos y el apoyo a decisiones de consumo responsable. Hacer visible el uso del agua y detectar posibles pérdidas puede ayudar a disminuir desperdicios. Las estimaciones energéticas o de CO2e mostradas en el prototipo se presentan como indicadores académicos y no como una medición certificada de emisiones.

## 3. Funcionalidades implementadas

1. Pantalla pública de inicio.
2. Registro e inicio de sesión con contraseñas almacenadas mediante hash.
3. Dashboard con consumo, línea base, tendencia diaria y patrón horario.
4. Gestión del sensor principal, umbrales y alertas.
5. Formulario de lectura manual como respaldo del canal IoT.
6. Resultados/reportes imprimibles.
7. Historial persistente.
8. API para telemetría ESP32.
9. Detección de consumo inusual.
10. Detección heurística de posible flujo persistente/fuga general.

## 4. Tecnologías

- Frontend: HTML5, CSS3, JavaScript y Jinja2.
- Backend: Python y Flask.
- Base de datos: PostgreSQL.
- Producción: Gunicorn.
- Hardware propuesto: ESP32 y caudalímetro.
- Despliegue: Render.
- Seguridad: hash de contraseñas, sesiones HTTPOnly, CSRF, validación backend, cabeceras de seguridad y secretos mediante variables de entorno.

## 5. Cambio respecto al Momento 1

La propuesta inicial contemplaba la posibilidad de múltiples sensores por zona. Durante la consolidación técnica se adoptó una arquitectura centralizada con un único sensor en la acometida principal. El cambio reduce costo e intervención física y hace coherente el alcance con un prototipo doméstico de fácil instalación. La consecuencia es que las alertas son generales y no localizan automáticamente el punto interno exacto de consumo.

## 6. Base de datos

Motor: PostgreSQL. El modelo se encuentra normalizado al menos a 3FN y contiene las entidades `households`, `users`, `sensors`, `readings` y `alerts`. La relación hogar-sensor es 1:1 mediante una restricción `UNIQUE` en `sensors.household_id`.

**Insertar aquí:** imagen `database/DER_AquaHogar.svg`.

## 7. Viabilidad

### Técnica

El stack usa tecnologías maduras y ampliamente soportadas. Flask concentra la lógica de negocio, PostgreSQL garantiza persistencia relacional y el ESP32 ofrece conectividad suficiente para la telemetría. La arquitectura permite trabajar primero con un simulador y sustituirlo por hardware real sin modificar el contrato de la API.

### Económica

La principal decisión de costo es utilizar un único caudalímetro por inmueble. Frente a una instrumentación distribuida por grifos o ramales, se reducen cantidad de sensores, cableado, mantenimiento e intervención hidráulica. El software utiliza tecnologías de código abierto y puede desplegarse inicialmente en planes de bajo costo para fines académicos.

### Ambiental

El aporte se concentra en visibilizar consumo, advertir desviaciones y favorecer una actuación más temprana frente al desperdicio o una posible fuga. El impacto real dependerá del comportamiento posterior del usuario y debe evaluarse con métricas como litros evitados, alertas atendidas y cambio porcentual frente a la línea base.

## 8. Impacto y evaluación

Indicadores sugeridos para una prueba piloto:

- consumo diario promedio antes/después;
- litros potencialmente evitados;
- número de alertas generadas y resueltas;
- tiempo medio desde alerta hasta revisión;
- porcentaje de días que cumplen la meta doméstica;
- disponibilidad del sistema y porcentaje de lecturas aceptadas por la API.

## 9. Repositorio y despliegue

- GitHub: `https://github.com/ginyoukai01-collab/AquaHogar-Momento2`
- Aplicación: `PENDIENTE_URL_RENDER`
- Administrador de prueba: `PENDIENTE_RENDER`
- Usuario regular: `PENDIENTE_RENDER`

## 10. Evidencias

Insertar capturas reales de:

1. Inicio.
2. Registro/inicio de sesión.
3. Dashboard.
4. Gestión principal.
5. Formulario de lectura.
6. Reportes.
7. DER.
8. URL pública en incógnito.

## 11. Conclusión

La versión final de AquaHogar materializa la propuesta del Momento 1 como una solución web con persistencia real, control de acceso, telemetría, análisis y reportes. La arquitectura centralizada conserva un alcance técnicamente viable para un prototipo universitario y permite demostrar cómo una solución de Ingeniería de Sistemas puede apoyar la gestión responsable de recursos y la sensibilización asociada al ODS 13.
