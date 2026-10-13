import os
from flask import Flask
from dotenv import load_dotenv


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app(test_config=None):
    load_dotenv()
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        DATABASE_URL=os.getenv("DATABASE_URL"),
        IOT_API_KEY=os.getenv("IOT_API_KEY"),
        APP_TIMEZONE=os.getenv("APP_TIMEZONE", "America/Bogota"),
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_as_bool(os.getenv("COOKIE_SECURE"), False),
    )

    if test_config:
        app.config.update(test_config)

    if not app.config.get("TESTING"):
        missing = [name for name in ("SECRET_KEY", "DATABASE_URL") if not app.config.get(name)]
        if missing:
            raise RuntimeError(
                "Faltan variables obligatorias: " + ", ".join(missing) + ". "
                "Copia .env.example a .env y configura valores reales."
            )

    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.api import api_bp
    from .security import csrf_token

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.jinja_env.globals["csrf_token"] = csrf_token

    from .errors import register_error_handlers
    register_error_handlers(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        return response

    return app
