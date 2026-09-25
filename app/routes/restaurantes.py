from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import run_query, IntegrityError

restaurantes_bp = Blueprint("restaurantes", __name__, url_prefix="/restaurantes")


def _contas_para_select():
    """Lista de contas ativas, usada para preencher o <select> de dono do restaurante."""
    return run_query(
        "SELECT id, nome, email FROM contas WHERE ativo = 1 ORDER BY nome",
        fetch=True,
    )


# READ
@restaurantes_bp.route("/")
def listar():
    restaurantes = run_query(
        """SELECT r.id, r.nome, r.categoria, r.cidade, r.taxa_entrega,
                  r.tempo_entrega_min, r.tempo_entrega_max, r.avaliacao,
                  r.ativo, c.nome AS dono_nome
           FROM restaurantes r
           JOIN contas c ON c.id = r.conta_id
           ORDER BY r.id DESC""",
        fetch=True,
    )
    return render_template("restaurantes/list.html", restaurantes=restaurantes)


# CREATE
@restaurantes_bp.route("/novo", methods=["GET", "POST"])
def criar():
    if request.method == "GET":
        return render_template(
            "restaurantes/form.html", restaurante=None, contas=_contas_para_select()
        )

    conta_id = request.form.get("conta_id", "").strip()
    nome = request.form.get("nome", "").strip()
    categoria = request.form.get("categoria", "").strip()
    descricao = request.form.get("descricao", "").strip() or None
    endereco = request.form.get("endereco", "").strip()
    cidade = request.form.get("cidade", "").strip()
    telefone = request.form.get("telefone", "").strip() or None
    taxa_entrega = request.form.get("taxa_entrega", "0").strip() or "0"
    tempo_min = request.form.get("tempo_entrega_min", "30").strip() or "30"
    tempo_max = request.form.get("tempo_entrega_max", "45").strip() or "45"

    if not conta_id or not nome or not categoria or not endereco or not cidade:
        flash("Dono, nome, categoria, endereço e cidade são obrigatórios.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    try:
        taxa_entrega_val = float(taxa_entrega.replace(",", "."))
        tempo_min_val = int(tempo_min)
        tempo_max_val = int(tempo_max)
    except ValueError:
        flash("Taxa de entrega e tempos de entrega devem ser números válidos.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    if taxa_entrega_val < 0:
        flash("A taxa de entrega não pode ser negativa.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    if tempo_min_val <= 0 or tempo_max_val <= 0 or tempo_min_val > tempo_max_val:
        flash("Tempo mínimo de entrega deve ser maior que zero e menor ou igual ao tempo máximo.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    try:
        run_query(
            """INSERT INTO restaurantes
               (conta_id, nome, categoria, descricao, endereco, cidade,
                telefone, taxa_entrega, tempo_entrega_min, tempo_entrega_max)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conta_id, nome, categoria, descricao, endereco, cidade,
             telefone, taxa_entrega_val, tempo_min_val, tempo_max_val),
            commit=True,
        )
        flash("Restaurante criado com sucesso!", "success")
        return redirect(url_for("restaurantes.listar"))
    except IntegrityError:
        flash("Não foi possível criar o restaurante. Verifique o dono selecionado.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )


# READ
@restaurantes_bp.route("/<int:restaurante_id>")
def detalhe(restaurante_id):
    restaurante = run_query(
        """SELECT r.*, c.nome AS dono_nome, c.email AS dono_email
           FROM restaurantes r
           JOIN contas c ON c.id = r.conta_id
           WHERE r.id = ?""",
        (restaurante_id,),
        fetchone=True,
    )
    if not restaurante:
        flash("Restaurante não encontrado.", "warning")
        return redirect(url_for("restaurantes.listar"))
    return render_template("restaurantes/detalhe.html", restaurante=restaurante)


# UPDATE
@restaurantes_bp.route("/<int:restaurante_id>/editar", methods=["GET", "POST"])
def editar(restaurante_id):
    restaurante = run_query(
        "SELECT * FROM restaurantes WHERE id = ?", (restaurante_id,), fetchone=True
    )
    if not restaurante:
        flash("Restaurante não encontrado.", "warning")
        return redirect(url_for("restaurantes.listar"))

    if request.method == "GET":
        return render_template(
            "restaurantes/form.html", restaurante=restaurante, contas=_contas_para_select()
        )

    conta_id = request.form.get("conta_id", "").strip()
    nome = request.form.get("nome", "").strip()
    categoria = request.form.get("categoria", "").strip()
    descricao = request.form.get("descricao", "").strip() or None
    endereco = request.form.get("endereco", "").strip()
    cidade = request.form.get("cidade", "").strip()
    telefone = request.form.get("telefone", "").strip() or None
    taxa_entrega = request.form.get("taxa_entrega", "0").strip() or "0"
    tempo_min = request.form.get("tempo_entrega_min", "30").strip() or "30"
    tempo_max = request.form.get("tempo_entrega_max", "45").strip() or "45"
    ativo = 1 if request.form.get("ativo") == "on" else 0

    if not conta_id or not nome or not categoria or not endereco or not cidade:
        flash("Dono, nome, categoria, endereço e cidade são obrigatórios.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    try:
        taxa_entrega_val = float(taxa_entrega.replace(",", "."))
        tempo_min_val = int(tempo_min)
        tempo_max_val = int(tempo_max)
    except ValueError:
        flash("Taxa de entrega e tempos de entrega devem ser números válidos.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    if tempo_min_val > tempo_max_val:
        flash("Tempo mínimo de entrega não pode ser maior que o tempo máximo.", "danger")
        return render_template(
            "restaurantes/form.html", restaurante=request.form, contas=_contas_para_select()
        )

    run_query(
        """UPDATE restaurantes SET
               conta_id=?, nome=?, categoria=?, descricao=?, endereco=?,
               cidade=?, telefone=?, taxa_entrega=?, tempo_entrega_min=?,
               tempo_entrega_max=?, ativo=?
           WHERE id=?""",
        (conta_id, nome, categoria, descricao, endereco, cidade, telefone,
         taxa_entrega_val, tempo_min_val, tempo_max_val, ativo, restaurante_id),
        commit=True,
    )
    flash("Restaurante atualizado com sucesso!", "success")
    return redirect(url_for("restaurantes.listar"))


# DELETE
@restaurantes_bp.route("/<int:restaurante_id>/excluir", methods=["POST"])
def excluir(restaurante_id):
    run_query("DELETE FROM restaurantes WHERE id = ?", (restaurante_id,), commit=True)
    flash("Restaurante excluído com sucesso!", "success")
    return redirect(url_for("restaurantes.listar"))