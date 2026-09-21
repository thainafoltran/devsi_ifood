import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-key-troque-em-producao")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "1") == "1"

    # ---- Blueprints ----
    from app.routes.crud import contas_bp
    from app.routes.cadastro_gmail import auth_google_bp, init_oauth

    app.register_blueprint(contas_bp)
    app.register_blueprint(auth_google_bp)
    init_oauth(app)

    @app.route("/")
    def index():
        return redirect(url_for("contas.listar"))

    return app