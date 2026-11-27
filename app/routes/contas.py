from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from app.db import run_query, IntegrityError
from app.services.notificacao import normalizar_telefone

contas_bp = Blueprint("contas", __name__, url_prefix="/contas")


def _validar_telefone(bruto, ignorar_id=None):
    """Devolve (telefone_normalizado, erro). O telefone é guardado só com dígitos (DDD + número),
    do mesmo jeito que o login por SMS/WhatsApp o procura. Telefone é opcional, mas não pode se repetir."""
    bruto = (bruto or "").strip()
    if not bruto:
        return None, None
    tel = normalizar_telefone(bruto)
    if len(tel) not in (10, 11):
        return None, "Telefone inválido. Informe o DDD + número, ex.: (11) 91234-5678."
    outras = run_query(
        "SELECT id, telefone FROM contas WHERE telefone IS NOT NULL AND telefone <> ''", fetch=True)
    for o in outras:
        if o["id"] != ignorar_id and normalizar_telefone(o["telefone"]) == tel:
            return None, "Já existe uma conta cadastrada com esse telefone."
    return tel, None


# READ
@contas_bp.route("/")
def listar():
    contas = run_query(
        """SELECT id, nome, email, tipo_login, telefone, ativo, data_criacao
           FROM contas ORDER BY id DESC""",
        fetch=True,
    )
    return render_template("contas/list.html", contas=contas)


# CREATE
@contas_bp.route("/nova", methods=["GET", "POST"])
def criar():
    if request.method == "GET":
        return render_template("contas/form.html", conta=None)

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    telefone, erro_tel = _validar_telefone(request.form.get("telefone"))

    if erro_tel:
        flash(erro_tel, "danger")
        return render_template("contas/form.html", conta=request.form)

    if not nome or not email or not senha:
        flash("Nome, e-mail e senha são obrigatórios.", "danger")
        return render_template("contas/form.html", conta=request.form)

    if len(senha) < 6:
        flash("A senha deve ter pelo menos 6 caracteres.", "danger")
        return render_template("contas/form.html", conta=request.form)

    senha_hash = generate_password_hash(senha)

    try:
        run_query(
            """INSERT INTO contas (nome, email, senha_hash, tipo_login, telefone)
               VALUES (?, ?, ?, 'local', ?)""",
            (nome, email, senha_hash, telefone),
            commit=True,
        )
        flash("Conta criada com sucesso!", "success")
        return redirect(url_for("contas.listar"))
    except IntegrityError:
        flash("Já existe uma conta cadastrada com esse e-mail.", "danger")
        return render_template("contas/form.html", conta=request.form)


# READ
@contas_bp.route("/<int:conta_id>")
def detalhe(conta_id):
    conta = run_query(
        "SELECT * FROM contas WHERE id = ?", (conta_id,), fetchone=True
    )
    if not conta:
        flash("Conta não encontrada.", "warning")
        return redirect(url_for("contas.listar"))
    return render_template("contas/detalhe.html", conta=conta)


# UPDATE
@contas_bp.route("/<int:conta_id>/editar", methods=["GET", "POST"])
def editar(conta_id):
    conta = run_query(
        "SELECT * FROM contas WHERE id = ?", (conta_id,), fetchone=True
    )
    if not conta:
        flash("Conta não encontrada.", "warning")
        return redirect(url_for("contas.listar"))

    if request.method == "GET":
        return render_template("contas/form.html", conta=conta)

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    telefone, erro_tel = _validar_telefone(request.form.get("telefone"), ignorar_id=conta_id)
    nova_senha = request.form.get("senha", "")
    ativo = 1 if request.form.get("ativo") == "on" else 0

    if erro_tel:
        flash(erro_tel, "danger")
        return render_template("contas/form.html", conta=request.form)

    if not nome or not email:
        flash("Nome e e-mail são obrigatórios.", "danger")
        return render_template("contas/form.html", conta=request.form)

    try:
        if nova_senha:
            if len(nova_senha) < 6:
                flash("A nova senha deve ter pelo menos 6 caracteres.", "danger")
                return render_template("contas/form.html", conta=request.form)
            senha_hash = generate_password_hash(nova_senha)
            run_query(
                """UPDATE contas SET nome=?, email=?, telefone=?,
                   senha_hash=?, ativo=? WHERE id=?""",
                (nome, email, telefone, senha_hash, ativo, conta_id),
                commit=True,
            )
        else:
            run_query(
                """UPDATE contas SET nome=?, email=?, telefone=?,
                   ativo=? WHERE id=?""",
                (nome, email, telefone, ativo, conta_id),
                commit=True,
            )
        flash("Conta atualizada com sucesso!", "success")
        return redirect(url_for("contas.listar"))
    except IntegrityError:
        flash("Já existe uma conta cadastrada com esse e-mail.", "danger")
        return render_template("contas/form.html", conta=request.form)


# DELETE
@contas_bp.route("/<int:conta_id>/excluir", methods=["POST"])
def excluir(conta_id):
    run_query("DELETE FROM contas WHERE id = ?", (conta_id,), commit=True)
    flash("Conta excluída com sucesso!", "success")
    return redirect(url_for("contas.listar"))

# TROCA RÁPIDA DE CONTA
@contas_bp.route("/<int:conta_id>/entrar", methods=["POST", "GET"])
def entrar_como(conta_id):
    conta = run_query("SELECT * FROM contas WHERE id = ? AND ativo = 1", (conta_id,), fetchone=True)
    if not conta:
        flash("Conta não encontrada ou inativa.", "danger")
        return redirect(url_for("contas.listar"))
    session.clear()
    session.permanent = True
    session["conta_id"] = conta["id"]
    flash(f"Você entrou como {conta['nome']} ({conta['email']}).", "success")
    return redirect(url_for("explorar.restaurantes"))