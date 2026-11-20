import os
from datetime import timedelta
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from app.db import init_db

load_dotenv()


def create_app():
    app = Flask(__name__, template_folder="front_end")
    app.secret_key = os.getenv("SECRET_KEY", "dev-key-troque-em-producao")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "1") == "1"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    init_db()

    from app.routes.contas import contas_bp
    from app.routes.cadastro_gmail import auth_google_bp, init_oauth
    #from app.routes.cadastro_facebook import auth_facebook_bp, init_oauth_facebook
    #from app.routes.auth_codigo import auth_codigo_bp
    from app.routes.restaurantes import restaurantes_bp
    from app.routes.produtos import produtos_bp
    from app.routes.enderecos import enderecos_bp
    from app.routes.explorar import explorar_bp
    from app.routes.cesta import cesta_bp
    from app.routes.pedidos import pedidos_bp

    for bp in (contas_bp, auth_google_bp, #auth_facebook_bp, 
               #auth_codigo_bp,
               restaurantes_bp, produtos_bp, enderecos_bp, explorar_bp,
               cesta_bp, pedidos_bp):
        app.register_blueprint(bp)
    init_oauth(app)
    #init_oauth_facebook()

    from devsi_ifood.app.auth_utils import usuario_atual
    from app.routes.cesta import quantidade_na_cesta

    @app.context_processor
    def globais():
        u = usuario_atual()
        return {"usuario": u, "cesta_qtd": quantidade_na_cesta(u["id"]) if u else 0}

    @app.template_filter("brl")
    def brl(v):
        return "R$ " + f"{float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @app.route("/")
    def index():
        return redirect(url_for("explorar.restaurantes"))

    return app



#ENTREGA 1
# import os 
# from flask import Flask, redirect, url_for
# from dotenv import load_dotenv
# from app.db import init_db

# load_dotenv() */ 


# def create_app():
#     app = Flask(__name__, template_folder="front_end")
#     app.secret_key = os.getenv("SECRET_KEY", "dev-key-troque-em-producao")
#     app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "1") == "1"

#     init_db()

#     # Blueprints 
#     from app.routes.contas import contas_bp
#     from app.routes.cadastro_gmail import auth_google_bp, init_oauth
#     from app.routes.restaurantes import restaurantes_bp
#     from app.routes.produtos import produtos_bp

#     app.register_blueprint(contas_bp)
#     app.register_blueprint(auth_google_bp)
#     app.register_blueprint(restaurantes_bp)
#     app.register_blueprint(produtos_bp)
#     init_oauth(app)

#     @app.route("/")
#     def index():
#         return redirect(url_for("contas.listar"))

#     return app