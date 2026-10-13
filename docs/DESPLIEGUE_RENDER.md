# Manual de despliegue en Render

## 1. Repositorio GitHub

Repositorio público oficial:

`https://github.com/ginyoukai01-collab/AquaHogar-Momento2`

## 2. Crear el Blueprint

1. Ingresar a Render.
2. Elegir **New > Blueprint**.
3. Conectar el repositorio `ginyoukai01-collab/AquaHogar-Momento2`.
4. Render detectará `render.yaml`.
5. Completar las variables marcadas como `sync: false`:
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`
   - `DEMO_USER_EMAIL`
   - `DEMO_USER_PASSWORD`
6. Crear los recursos.

El Blueprint crea un servicio web Python y una base PostgreSQL. `DATABASE_URL` se obtiene directamente de la base y no se escribe en el código.

## 3. Inicialización automática

El `startCommand` ejecuta de forma idempotente:

```bash
python -m backend.init_db
python -m backend.seed
gunicorn --bind 0.0.0.0:$PORT wsgi:app
```

`schema.sql` usa `CREATE TABLE IF NOT EXISTS` y el seed verifica la existencia de usuarios, sensor y lecturas antes de insertar datos.

## 4. Verificación obligatoria

Abrir la URL pública en ventana de incógnito y probar:

1. `/` carga correctamente.
2. Login administrador.
3. Login usuario regular.
4. Dashboard muestra datos persistidos.
5. Registrar una lectura manual.
6. Cerrar sesión y volver a entrar; la lectura debe permanecer.
7. Abrir Gestión y Reportes.
8. `/api/health` debe devolver `status: ok` y `database: true`.

## 5. Credenciales de evaluación

Las credenciales entregadas al docente deben coincidir con las variables configuradas en Render. No reutilizar contraseñas personales.
