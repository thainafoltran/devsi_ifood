import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.db import run_query
from app.auth_utils import safe_next, usuario_atual
from app.services.notificacao import enviar_codigo, normalizar_telefone

auth_codigo_bp = Blueprint("auth_codigo", __name__)

VALIDADE_MIN = 5
MAX_TENTATIVAS = 5
INTERVALO_REENVIO_S = 60
CANAIS = ("email", "sms", "whatsapp")


def _agora():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _hash(conta_id, codigo):
    chave = current_app.secret_key.encode()
    return hmac.new(chave, f"{conta_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def _achar_contas(ident):
    """Procura a conta pelo que a pessoa digitou: e-mail (tem '@') ou telefone.

    O canal escolhido (e-mail/SMS/WhatsApp) só define ONDE o código será enviado,
    não como a conta é encontrada. O telefone é comparado só pelos dígitos, então
    '(11) 91234-5678', '11912345678' e '+55 11 91234-5678' são o mesmo número.
    """
    ident = ident.strip()
    if "@" in ident:
        return run_query("SELECT * FROM contas WHERE email=? AND ativo=1", (ident.lower(),), fetch=True)
    tel = normalizar_telefone(ident)
    if len(tel) not in (10, 11):
        return []
    candidatas = run_query(
        "SELECT * FROM contas WHERE ativo=1 AND telefone IS NOT NULL AND telefone <> '' ORDER BY id",
        fetch=True)
    return [c for c in candidatas if normalizar_telefone(c["telefone"]) == tel]


def _gerar_e_enviar(conta, canal, destino):
    ultimo = run_query("SELECT criado_em FROM codigos_login WHERE conta_id=? ORDER BY id DESC LIMIT 1",
                       (conta["id"],), fetchone=True)
    if ultimo and _agora() - datetime.fromisoformat(ultimo["criado_em"]) < timedelta(seconds=INTERVALO_REENVIO_S):
        return None, f"Aguarde {INTERVALO_REENVIO_S}s para pedir um novo código."
    
    run_query("UPDATE codigos_login SET usado=1 WHERE conta_id=? AND usado=0", (conta["id"],), commit=True)
    
    codigo = f"{secrets.randbelow(10**6):06d}"
    agora = _agora()
    
    cid = run_query(
        """INSERT INTO codigos_login (conta_id, canal, destino, codigo_hash, criado_em, expira_em)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (conta["id"], canal, destino, _hash(conta["id"], codigo),
         _iso(agora), _iso(agora + timedelta(minutes=VALIDADE_MIN))), commit=True)
         
    r = enviar_codigo(canal, destino, codigo)
    if r is False:
        return None, "Não foi possível enviar o código agora. Tente outro canal."
        
    if r == "dev" and os.getenv("DEV_SHOW_CODE", "1") == "1":
        flash(f"[modo desenvolvimento] código: {codigo}", "info")
        
    return cid, None


@auth_codigo_bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if usuario_atual():
        return redirect(url_for("explorar.restaurantes"))
        
    nxt = safe_next(request.values.get("next"))
    if request.method == "GET":
        return render_template("auth/entrar.html", next=nxt)

    canal = request.form.get("canal", "email")
    ident = request.form.get("identificador", "").strip()

    if canal not in CANAIS or not ident:
        flash("Escolha o canal e informe seu e-mail ou telefone.", "danger")
        return render_template("auth/entrar.html", next=nxt), 400

    if "@" in ident and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", ident):
        flash("E-mail inválido.", "danger")
        return render_template("auth/entrar.html", next=nxt), 400

    contas = _achar_contas(ident)
    if not contas:
        flash("Não encontramos uma conta ativa com esses dados. Cadastre-se primeiro.", "warning")
        return render_template("auth/entrar.html", next=nxt), 404
    if len(contas) > 1:
        flash("Mais de uma conta usa esse telefone. Entre informando o e-mail da conta.", "warning")
        return render_template("auth/entrar.html", next=nxt), 409
    conta = contas[0]

    if canal == "email":
        destino = conta["email"]
    else:
        destino = normalizar_telefone(conta["telefone"])
        if len(destino) not in (10, 11):
            flash("Essa conta não tem telefone cadastrado para receber o código por SMS/WhatsApp. "
                  "Escolha o canal E-mail ou cadastre um telefone na conta.", "warning")
            return render_template("auth/entrar.html", next=nxt), 400

    codigo_id, erro = _gerar_e_enviar(conta, canal, destino)
    
    if erro:
        flash(erro, "danger")
        return render_template("auth/entrar.html", next=nxt), 429
        
    session["login_pendente"] = {"conta_id": conta["id"], "canal": canal, "destino": destino, "next": nxt}
    return redirect(url_for("auth_codigo.verificar"))


@auth_codigo_bp.route("/entrar/verificar", methods=["GET", "POST"])
def verificar():
    p = session.get("login_pendente")
    if not p:
        return redirect(url_for("auth_codigo.entrar"))
        
    mascarado = p["destino"]
    if p["canal"] == "email":
        u, d = mascarado.split("@", 1)
        mascarado = u[:2] + "***@" + d
    else:
        mascarado = "(**) *****-" + mascarado[-4:]
        
    if request.method == "GET":
        return render_template("auth/verificar.html", destino=mascarado, canal=p["canal"])

    codigo = request.form.get("codigo", "").strip()
    if not re.fullmatch(r"\d{6}", codigo):
        flash("Digite os 6 dígitos do código.", "danger")
        return render_template("auth/verificar.html", destino=mascarado, canal=p["canal"]), 400

    reg = run_query("SELECT * FROM codigos_login WHERE conta_id=? AND usado=0 ORDER BY id DESC LIMIT 1",
                    (p["conta_id"],), fetchone=True)
                    
    if not reg or _agora() > datetime.fromisoformat(reg["expira_em"]):
        flash("Código expirado. Peça um novo.", "warning")
        session.pop("login_pendente", None)
        return redirect(url_for("auth_codigo.entrar"))
        
    if reg["tentativas"] >= MAX_TENTATIVAS:
        run_query("UPDATE codigos_login SET usado=1 WHERE id=?", (reg["id"],), commit=True)
        session.pop("login_pendente", None)
        flash("Muitas tentativas. Peça um novo código.", "danger")
        return redirect(url_for("auth_codigo.entrar"))
        
    if not hmac.compare_digest(reg["codigo_hash"], _hash(p["conta_id"], codigo)):
        run_query("UPDATE codigos_login SET tentativas=tentativas+1 WHERE id=?", (reg["id"],), commit=True)
        restantes = MAX_TENTATIVAS - reg["tentativas"] - 1
        flash(f"Código incorreto. Restam {restantes} tentativa(s).", "danger")
        return render_template("auth/verificar.html", destino=mascarado, canal=p["canal"]), 400

    run_query("UPDATE codigos_login SET usado=1 WHERE id=?", (reg["id"],), commit=True)
    nxt = p.get("next")
    
    session.clear()
    session.permanent = True
    session["conta_id"] = p["conta_id"]
    flash("Login realizado com sucesso!", "success")
    
    return redirect(nxt or url_for("explorar.restaurantes"))


@auth_codigo_bp.route("/entrar/reenviar", methods=["POST"])
def reenviar():
    p = session.get("login_pendente")
    if not p:
        return redirect(url_for("auth_codigo.entrar"))
        
    conta = run_query("SELECT * FROM contas WHERE id=? AND ativo=1", (p["conta_id"],), fetchone=True)
    if not conta:
        session.pop("login_pendente", None)
        flash("Conta inválida ou inativa.", "danger")
        return redirect(url_for("auth_codigo.entrar"))
        
    _, erro = _gerar_e_enviar(conta, p["canal"], p["destino"])
    flash(erro or "Novo código enviado.", "danger" if erro else "success")
    return redirect(url_for("auth_codigo.verificar"))


@auth_codigo_bp.route("/sair", methods=["POST", "GET"])
def sair():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth_codigo.entrar"))