# AquaHogar

**Sistema inteligente de monitoreo del consumo total de agua en el hogar**  
Proyecto universitario - Ingeniería de Sistemas - Universidad Cooperativa de Colombia  
**ODS 13: Acción por el Clima**

> Repositorio GitHub: `https://github.com/ginyoukai01-collab/AquaHogar-Momento2`  
> Aplicación desplegada: `https://aquahogar-web.onrender.com`

## 1. Descripción

AquaHogar monitorea el consumo total de agua de un inmueble mediante **un único caudalímetro instalado en la acometida principal**. El dispositivo se conecta a un ESP32, que transmite telemetría al backend. La plataforma persiste las mediciones en PostgreSQL, construye el historial de consumo, detecta aumentos anómalos y patrones de flujo persistente compatibles con una posible fuga general, y presenta alertas, recomendaciones y reportes al usuario.

El sistema prioriza una instalación económica y poco invasiva: no requiere intervenir cada grifo o ramal interno. Como consecuencia, AquaHogar detecta anomalías del **consumo global** y orienta la inspección; no identifica automáticamente el punto interno exacto de una fuga.

## 2. Relación con el ODS 13

La solución contribuye de manera complementaria a la acción climática mediante sensibilización, uso eficiente de recursos y apoyo a decisiones que reduzcan desperdicios. El proyecto no presenta el consumo de agua como una medición directa de CO2: las estimaciones ambientales de la interfaz están claramente separadas de la telemetría real.

## 3. Arquitectura

```text
Red de agua
    ↓
Acometida principal
    ↓
Caudalímetro único
    ↓
ESP32 ──HTTPS/JSON──> Flask / API ──> PostgreSQL
                              │
                              ├─ análisis de línea base
                              ├─ consumo inusual
                              ├─ flujo persistente
                              └─ alertas/recomendaciones
                                      ↓
                              Frontend web responsive
```

## 4. Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Jinja2 |
| Backend | Python 3, Flask |
| Servidor WSGI | Gunicorn |
| Base de datos | PostgreSQL |
| Driver | psycopg 3 |
| Seguridad | Werkzeug password hashing, sesiones Flask, CSRF |
| Hardware | ESP32 + caudalímetro |
| Despliegue | Render |

## 5. Vistas obligatorias

| Rúbrica | Ruta | Estado |
|---|---|---|
| Pantalla de inicio | `/` | Funcional |
| Registro / Inicio de sesión | `/acceso` | Funcional + PostgreSQL |
| Panel principal | `/dashboard` | Funcional |
| Gestión principal | `/gestion` | Funcional |
| Formulario de ingreso | `/lecturas/nueva` | Funcional + validación |
| Resultados / reportes | `/reportes` | Funcional |
| Historial adicional | `/historial` | Funcional |

## 6. Estructura

```text
AquaHogar/
├── backend/               # Flask, rutas, servicios, seguridad y DB
├── frontend/              # templates y archivos estáticos
├── database/              # schema.sql, dump.sql, DBML y DER
├── docs/                  # arquitectura, despliegue y evidencias técnicas
├── simulator/             # simulador del ESP32/caudalímetro
├── tests/                 # pruebas de lógica
├── .env.example
├── .gitignore
├── Procfile
├── render.yaml
├── requirements.txt
├── run.py
└── wsgi.py
```

## 7. Ejecución local

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Git

### Preparar entorno

```bash
git clone https://github.com/ginyoukai01-collab/AquaHogar-Momento2
cd AquaHogar-Momento2
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Instalar:

```bash
pip install -r requirements.txt
```

### Variables de entorno

Copiar `.env.example` a `.env` y configurar valores reales.

```env
SECRET_KEY=...
DATABASE_URL=postgresql://usuario:password@localhost:5432/aquahogar
IOT_API_KEY=...
COOKIE_SECURE=false
ADMIN_EMAIL=admin@aquahogar.demo
ADMIN_PASSWORD=...
DEMO_USER_EMAIL=usuario@aquahogar.demo
DEMO_USER_PASSWORD=...
```

Nunca subir `.env` a GitHub.

### Crear base y datos

```bash
python -m backend.init_db
python -m backend.seed
```

Alternativamente:

```bash
psql -d aquahogar -f database/schema.sql
psql -d aquahogar -f database/dump.sql
```

### Ejecutar

```bash
python run.py
```

Abrir `http://127.0.0.1:5000`.

## 8. API IoT

### Estado

```http
GET /api/health
```

En producción:

```text
https://aquahogar-web.onrender.com/api/health
```

### Nueva lectura

```http
POST /api/iot/lecturas
X-AquaHogar-Key: <IOT_API_KEY>
Content-Type: application/json
```

```json
{
  "sensor_code": "ESP32-PRINCIPAL-01",
  "recorded_at": "2026-10-12T20:15:00-05:00",
  "flow_l_min": 7.2,
  "volume_liters": 36.0
}
```

## 9. Usuarios de evaluación

El proyecto incluye un `dump.sql` con credenciales **exclusivas para evaluación local**:

- Administrador: `admin@aquahogar.demo` / `AquaAdmin2026!`
- Usuario: `usuario@aquahogar.demo` / `AquaUsuario2026!`

Para el despliegue en Render las contraseñas se configuran mediante variables de entorno y pueden ser diferentes.

## 10. Base de datos

El modelo PostgreSQL se encuentra en `/database` y está normalizado al menos a 3FN. La restricción `UNIQUE` sobre `sensors.household_id` implementa la regla física de un sensor principal por inmueble.

## 11. Despliegue

La versión pública se encuentra en:

`https://aquahogar-web.onrender.com`

Consultar [`docs/DESPLIEGUE_RENDER.md`](docs/DESPLIEGUE_RENDER.md). `render.yaml` documenta la infraestructura prevista para el servicio web y PostgreSQL.

## 12. Pruebas

```bash
python -m unittest discover -s tests -v
```

## 13. Limitaciones actuales

- La detección de fugas es una heurística de apoyo y no sustituye una inspección hidráulica.
- Un único sensor no permite localizar el ramal interno exacto donde ocurre el consumo.
- Las estimaciones energéticas/CO2e son académicas y no corresponden a una certificación de huella ambiental.
