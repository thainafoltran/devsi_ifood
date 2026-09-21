"""
CRUD Web completo do cadastro de CONTAS (item 5 da entrega).
Rotas:
  GET  /contas            -> lista todas as contas
  GET  /contas/nova        -> formulário de criação
  POST /contas/nova        -> cria conta (Create)
  GET  /contas/<id>        -> visualizar detalhes (Read)
  GET  /contas/<id>/editar -> formulário de edição
  POST /contas/<id>/editar -> atualiza conta (Update)
  POST /contas/<id>/excluir-> remove conta (Delete)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from mysql.connector import IntegrityError
from app.db import run_query

contas_bp = Blueprint("contas", __name__, url_prefix="/contas")


# ---------- READ (listar) ----------
@contas_bp.route("/")
def listar():
    contas = run_query(
        """SELECT id, nome, email, tipo_login, telefone, ativo, data_criacao
           FROM contas ORDER BY id DESC""",
        fetch=True,
    )
    return render_template("contas/list.html", contas=contas)


# ---------- CREATE ----------
@contas_bp.route("/nova", methods=["GET", "POST"])
def criar():
    if request.method == "GET":
        return render_template("contas/form.html", conta=None)

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    telefone = request.form.get("telefone", "").strip() or None

    # ---- Regras de negócio básicas ----
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
               VALUES (%s, %s, %s, 'local', %s)""",
            (nome, email, senha_hash, telefone),
            commit=True,
        )
        flash("Conta criada com sucesso!", "success")
        return redirect(url_for("contas.listar"))
    except IntegrityError:
        flash("Já existe uma conta cadastrada com esse e-mail.", "danger")
        return render_template("contas/form.html", conta=request.form)


# ---------- READ (detalhe) ----------
@contas_bp.route("/<int:conta_id>")
def detalhe(conta_id):
    conta = run_query(
        "SELECT * FROM contas WHERE id = %s", (conta_id,), fetchone=True
    )
    if not conta:
        flash("Conta não encontrada.", "warning")
        return redirect(url_for("contas.listar"))
    return render_template("contas/detalhe.html", conta=conta)


# ---------- UPDATE ----------
@contas_bp.route("/<int:conta_id>/editar", methods=["GET", "POST"])
def editar(conta_id):
    conta = run_query(
        "SELECT * FROM contas WHERE id = %s", (conta_id,), fetchone=True
    )
    if not conta:
        flash("Conta não encontrada.", "warning")
        return redirect(url_for("contas.listar"))

    if request.method == "GET":
        return render_template("contas/form.html", conta=conta)

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    telefone = request.form.get("telefone", "").strip() or None
    nova_senha = request.form.get("senha", "")
    ativo = 1 if request.form.get("ativo") == "on" else 0

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
                """UPDATE contas SET nome=%s, email=%s, telefone=%s,
                   senha_hash=%s, ativo=%s WHERE id=%s""",
                (nome, email, telefone, senha_hash, ativo, conta_id),
                commit=True,
            )
        else:
            run_query(
                """UPDATE contas SET nome=%s, email=%s, telefone=%s,
                   ativo=%s WHERE id=%s""",
                (nome, email, telefone, ativo, conta_id),
                commit=True,
            )
        flash("Conta atualizada com sucesso!", "success")
        return redirect(url_for("contas.listar"))
    except IntegrityError:
        flash("Já existe uma conta cadastrada com esse e-mail.", "danger")
        return render_template("contas/form.html", conta=request.form)


# ---------- DELETE ----------
@contas_bp.route("/<int:conta_id>/excluir", methods=["POST"])
def excluir(conta_id):
    run_query("DELETE FROM contas WHERE id = %s", (conta_id,), commit=True)
    flash("Conta excluída com sucesso!", "success")
    return redirect(url_for("contas.listar"))