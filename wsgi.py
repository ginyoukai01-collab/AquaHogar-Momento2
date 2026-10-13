import os

# En Render, la inicialización puede habilitarse mediante AUTO_INIT_DB=true.
# init_db y seed son idempotentes: crean el esquema y los datos de evaluación
# únicamente cuando hacen falta.
if os.getenv("AUTO_INIT_DB", "false").strip().lower() in {"1", "true", "yes", "on"}:
    import backend.init_db  # noqa: F401
    import backend.seed  # noqa: F401

from backend import create_app

app = create_app()
