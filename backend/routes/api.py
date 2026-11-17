        FROM readings r
        JOIN sensors s ON s.id=r.sensor_id
        WHERE s.household_id=%s
        ORDER BY r.id DESC LIMIT 100
        """,
        (household_id,),
    )
    serializable = [dict(r, recorded_at=r["recorded_at"].isoformat()) for r in rows]
    return jsonify({"readings": serializable})


@api_bp.post("/iot/lecturas")
def iot_reading():
    expected = current_app.config.get("IOT_API_KEY")
    supplied = request.headers.get("X-AquaHogar-Key")
    if not expected:
        return jsonify({"error": "Integración IoT no configurada"}), 503
    if supplied != expected:
        return jsonify({"error": "No autorizado"}), 401

    body = request.get_json(silent=True) or {}
    try:
        sensor_code = str(body.get("sensor_code", "")).strip().upper()
        if not sensor_code:
            raise ValueError("sensor_code es obligatorio")

        sensor = fetch_one(
            """
            SELECT id, household_id
            FROM sensors
            WHERE code=%s AND active=TRUE AND installation_point='acometida_principal'
            """,
            (sensor_code,),
        )
        if not sensor:
            return jsonify({"error": "Caudalímetro principal no encontrado"}), 404

        recorded_at = datetime.fromisoformat(body.get("recorded_at")) if body.get("recorded_at") else datetime.now()
        flow = nonnegative_float(body.get("flow_l_min"), "flow_l_min", 500)
        volume = nonnegative_float(body.get("volume_liters"), "volume_liters", 10000)
        reading = create_reading(
            household_id=sensor["household_id"],
            sensor_id=sensor["id"],
            recorded_at=recorded_at,
            flow_l_min=flow,
            volume_liters=volume,
            source="iot",
            created_by_user_id=None,
        )
        return jsonify({"accepted": True, "reading_id": reading["id"]}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Error interno al registrar la lectura"}), 500


@api_bp.post("/hogares/<int:household_id>/comandos")
def create_remote_command(household_id):
    if not session.get("user_id"):
        return jsonify({"error": "Autenticación requerida"}), 401
    if household_id != session.get("household_id"):
        return jsonify({"error": "No autorizado para controlar este hogar"}), 403
    if session.get("role") != "admin":
        return jsonify({"error": "Se requiere rol administrador"}), 403

    validate_csrf()
    body = request.get_json(silent=True) or {}
    try:
        command = send_command(
            household_id=household_id,
            user_id=session["user_id"],
            action=str(body.get("accion", "")).strip(),
        )
        return jsonify(
            {
                "accepted": True,
                "command_id": command["id"],
                "accion": command["accion"],
                "estado": command["estado"],
            }
        ), 202
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.get("/hogares/<int:household_id>/comandos")
def remote_commands(household_id):
    if not session.get("user_id"):
        return jsonify({"error": "Autenticación requerida"}), 401
    if household_id != session.get("household_id"):
        return jsonify({"error": "No autorizado para consultar este hogar"}), 403

    rows = list_commands(household_id, limit=20)
    commands = []
    for row in rows:
        commands.append(
            {
                "id": row["id"],
                "accion": row["accion"],
                "estado": row["estado"],
                "usuario": row["usuario_nombre"],
                "enviado_en": row["enviado_en"].isoformat(),
                "confirmado_en": row["confirmado_en"].isoformat() if row["confirmado_en"] else None,
            }
        )
    return jsonify({"commands": commands})
