import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from app.db import init_db

load_dotenv()  # lê o arquivo .env


def create_app():
    app = Flask(__name__, template_folder="front_end")
    app.secret_key = os.getenv("SECRET_KEY", "dev-key-troque-em-producao")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "1") == "1"

    # cria o arquivo/tabelas do SQLite automaticamente, se ainda não existirem
    init_db()

    # ---- Blueprints ----
    from app.routes.contas import contas_bp
    from app.routes.cadastro_gmail import auth_google_bp, init_oauth
    from app.routes.restaurantes import restaurantes_bp
    from app.routes.produtos import produtos_bp

    app.register_blueprint(contas_bp)
    app.register_blueprint(auth_google_bp)
    app.register_blueprint(restaurantes_bp)
    app.register_blueprint(produtos_bp)
    init_oauth(app)

    @app.route("/")
    def index():
        return redirect(url_for("contas.listar"))

    return app