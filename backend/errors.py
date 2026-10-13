from flask import render_template


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", None) or "La solicitud contiene datos inválidos."
        return render_template("error.html", code=400, title="Solicitud inválida", message=message), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, title="Acceso restringido", message="No tienes permisos para realizar esta operación."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, title="Página no encontrada", message="La ruta solicitada no existe."), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("error.html", code=413, title="Solicitud demasiado grande", message="El contenido enviado supera el límite permitido."), 413

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("error.html", code=500, title="Error interno", message="Ocurrió un error inesperado. Intenta nuevamente."), 500
