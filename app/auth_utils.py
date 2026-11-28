from functools import wraps
from urllib.parse import urlparse
from flask import session, redirect, url_for, flash, request
from app.db import run_query


def usuario_atual():
    cid = session.get("conta_id")
    if not cid:
        return None
    return run_query("SELECT * FROM contas WHERE id = ? AND ativo = 1", (cid,), fetchone=True)


def safe_next(next_url, fallback="/"):
    if not next_url:
        return fallback
    parsed = urlparse(next_url)
    if parsed.netloc or parsed.scheme:
        return fallback
    return next_url if next_url.startswith("/") else fallback


def _destino_pos_login():
    """Para onde voltar depois do login.

    GET  -> a própria página (com a query string).
    POST -> a página de onde o formulário foi enviado (campo 'next' ou Referer).
            Não dá para voltar para a URL do POST, porque ela só aceita POST (daria erro 405).
    """
    if request.method == "GET":
        return request.full_path.rstrip("?")
    nxt = request.form.get("next")
    if not nxt and request.referrer:
        ref = urlparse(request.referrer)
        nxt = ref.path + (f"?{ref.query}" if ref.query else "")
    return safe_next(nxt, "/")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # usuario_atual() também cobre conta excluída/inativa com a sessão ainda aberta
        if not usuario_atual():
            session.pop("conta_id", None)
            flash("Por favor, faça login para continuar.", "warning")
            return redirect(url_for("auth_codigo.entrar", next=_destino_pos_login()))
        return f(*args, **kwargs)
    return decorated_function
