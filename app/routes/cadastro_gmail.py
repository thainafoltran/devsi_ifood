"""
Inserção de nova conta via Google/Gmail (item 6 da entrega).

Fluxo:
  1. Usuário clica em "Entrar com Google" -> /auth/google/login
  2. É redirecionado para a tela de consentimento do Google
  3. Google chama de volta /auth/google/callback com um código
  4. Trocamos o código por dados do usuário (nome, email, sub/id)
  5. Se já existe conta com esse email -> apenas loga
     Se não existe -> cria uma nova conta (tipo_login='google', sem senha)
"""
import os
from flask import Blueprint, redirect, url_for, session, flash
from authlib.integrations.flask_client import OAuth
from mysql.connector import IntegrityError
from app.db import run_query

auth_google_bp = Blueprint("auth_google", __name__, url_prefix="/auth/google")

oauth = OAuth()


def init_oauth(app):
    """Registra o provedor Google no Authlib. Chamado no create_app()."""
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@auth_google_bp.route("/login")
def login():
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or url_for(
        "auth_google.callback", _external=True
    )
    return oauth.google.authorize_redirect(redirect_uri)


@auth_google_bp.route("/callback")
def callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.google.userinfo()

    google_id = userinfo["sub"]
    email = userinfo["email"].lower()
    nome = userinfo.get("name") or email.split("@")[0]
    foto_url = userinfo.get("picture")

    # 1) já existe conta com esse google_id ou esse email?
    conta = run_query(
        """SELECT * FROM contas
           WHERE (tipo_login='google' AND provider_id=%s) OR email=%s
           LIMIT 1""",
        (google_id, email),
        fetchone=True,
    )

    if conta:
        conta_id = conta["id"]
        flash(f"Bem-vindo de volta, {conta['nome']}!", "success")
    else:
        # 2) cria nova conta -- sem senha, pois a autenticação é feita pelo Google
        try:
            conta_id = run_query(
                """INSERT INTO contas (nome, email, senha_hash, tipo_login,
                   provider_id, foto_url)
                   VALUES (%s, %s, NULL, 'google', %s, %s)""",
                (nome, email, google_id, foto_url),
                commit=True,
            )
            flash(f"Conta criada com sucesso via Google, {nome}!", "success")
        except IntegrityError:
            flash("Já existe uma conta local com esse e-mail.", "danger")
            return redirect(url_for("contas.listar"))

    # guarda o usuário logado na sessão
    session["conta_id"] = conta_id
    return redirect(url_for("contas.detalhe", conta_id=conta_id))


@auth_google_bp.route("/logout")
def logout():
    session.pop("conta_id", None)
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("contas.listar"))