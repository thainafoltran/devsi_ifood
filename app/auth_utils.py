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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "conta_id" not in session:
            flash("Por favor, faça login para continuar.", "warning")
            return redirect(url_for("auth_codigo.entrar", next=request.path))
        return f(*args, **kwargs)
    return decorated_function