import psycopg
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from backend.db import fetch_one, get_connection
from backend.validation import clean_text, validate_email, validate_password
from backend.security import validate_csrf

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/acceso", methods=["GET", "POST"])
def auth():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    mode = request.args.get("modo", "login")
    if request.method == "POST":
        validate_csrf()
        action = request.form.get("action", "login")
        try:
            if action == "register":
                name = clean_text(request.form.get("name"), 120)
                email = validate_email(request.form.get("email"))
                password = validate_password(request.form.get("password"))
                if not name:
                    raise ValueError("El nombre es obligatorio.")

                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                        if cur.fetchone():
                            flash("Ya existe una cuenta con ese correo.", "error")
                            return render_template("auth.html", mode="register"), 409

                        cur.execute(
                            """
                            INSERT INTO households(
                                name, daily_goal_liters, anomaly_threshold_percent,
                                leak_flow_threshold_l_min, leak_duration_minutes
                            ) VALUES (%s, 310, 20, 0.30, 30)
                            RETURNING id
                            """,
                            (f"Hogar de {name}",),
                        )
                        household_id = cur.fetchone()["id"]

                        cur.execute(
                            """
                            INSERT INTO users(household_id, name, email, password_hash, role)
                            VALUES (%s, %s, %s, %s, 'admin')
                            RETURNING id, household_id, name, email, role
                            """,
                            (household_id, name, email, generate_password_hash(password)),
                        )
                        user = cur.fetchone()

                        cur.execute(
                            """
                            INSERT INTO sensors(
                                household_id, code, name, sensor_type, installation_point, active
                            ) VALUES (%s, %s, 'Caudalímetro principal', 'flujo', 'acometida_principal', TRUE)
                            """,
                            (household_id, f"ESP32-PRINCIPAL-{household_id}"),
                        )

                _set_session(user)
                flash("Cuenta creada. AquaHogar configuró un caudalímetro principal para tu inmueble.", "success")
                return redirect(url_for("main.dashboard"))

            email = validate_email(request.form.get("email"))
            password = request.form.get("password") or ""
            user = fetch_one(
                "SELECT id, household_id, name, email, password_hash, role, active FROM users WHERE email = %s",
                (email,),
            )
            if not user or not user["active"] or not check_password_hash(user["password_hash"], password):
                flash("Correo o contraseña incorrectos.", "error")
                return render_template("auth.html", mode="login"), 401

            _set_session(user)
            flash("Sesión iniciada correctamente.", "success")
            return redirect(url_for("main.dashboard"))

        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("auth.html", mode=action), 400
        except psycopg.errors.UniqueViolation:
            flash("Ya existe una cuenta o identificador con esos datos.", "error")
            return render_template("auth.html", mode="register"), 409
        except Exception:
            flash("No fue posible completar la operación. Intenta nuevamente.", "error")
            return render_template("auth.html", mode=mode), 500

    return render_template("auth.html", mode=mode)


@auth_bp.post("/salir")
def logout():
    validate_csrf()
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("auth.auth"))


def _set_session(user):
    session.clear()
    session["user_id"] = user["id"]
    session["household_id"] = user["household_id"]
    session["user_name"] = user["name"]
    session["role"] = user["role"]
