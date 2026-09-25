"""
CRUD Web completo de PRODUTOS - refeições e lanches (item 8 da entrega).
Cada produto pertence a um restaurante.

Rotas:
  GET  /produtos                  -> lista todos os produtos (com filtro opcional por restaurante)
  GET  /produtos/novo             -> formulário de criação
  POST /produtos/novo             -> cria produto (Create)
  GET  /produtos/<id>             -> visualizar detalhes (Read)
  GET  /produtos/<id>/editar      -> formulário de edição
  POST /produtos/<id>/editar      -> atualiza produto (Update)
  POST /produtos/<id>/excluir     -> remove produto (Delete)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import run_query, IntegrityError

produtos_bp = Blueprint("produtos", __name__, url_prefix="/produtos")

CATEGORIAS_VALIDAS = ["Lanche", "Refeição", "Bebida", "Sobremesa", "Entrada", "Combo"]


def _restaurantes_para_select():
    """Lista de restaurantes ativos, usada para preencher o <select> do produto."""
    return run_query(
        "SELECT id, nome FROM restaurantes WHERE ativo = 1 ORDER BY nome",
        fetch=True,
    )


# ---------- READ (listar) ----------
@produtos_bp.route("/")
def listar():
    restaurante_id = request.args.get("restaurante_id", type=int)

    if restaurante_id:
        produtos = run_query(
            """SELECT p.*, r.nome AS restaurante_nome
               FROM produtos p
               JOIN restaurantes r ON r.id = p.restaurante_id
               WHERE p.restaurante_id = %s
               ORDER BY p.id DESC""",
            (restaurante_id,),
            fetch=True,
        )
    else:
        produtos = run_query(
            """SELECT p.*, r.nome AS restaurante_nome
               FROM produtos p
               JOIN restaurantes r ON r.id = p.restaurante_id
               ORDER BY p.id DESC""",
            fetch=True,
        )

    restaurantes = _restaurantes_para_select()
    return render_template(
        "produtos/list.html",
        produtos=produtos,
        restaurantes=restaurantes,
        restaurante_id=restaurante_id,
    )


# ---------- CREATE ----------
@produtos_bp.route("/novo", methods=["GET", "POST"])
def criar():
    if request.method == "GET":
        return render_template(
            "produtos/form.html",
            produto=None,
            restaurantes=_restaurantes_para_select(),
            categorias=CATEGORIAS_VALIDAS,
        )

    restaurante_id = request.form.get("restaurante_id", "").strip()
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip() or None
    categoria = request.form.get("categoria", "").strip()
    preco = request.form.get("preco", "").strip()
    imagem_url = request.form.get("imagem_url", "").strip() or None

    # ---- Regras de negócio básicas ----
    if not restaurante_id or not nome or not categoria or not preco:
        flash("Restaurante, nome, categoria e preço são obrigatórios.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    if categoria not in CATEGORIAS_VALIDAS:
        flash("Categoria inválida.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    try:
        preco_val = float(preco.replace(",", "."))
    except ValueError:
        flash("Preço deve ser um número válido.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    if preco_val < 0:
        flash("O preço não pode ser negativo.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    run_query(
        """INSERT INTO produtos (restaurante_id, nome, descricao, categoria, preco, imagem_url)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (restaurante_id, nome, descricao, categoria, preco_val, imagem_url),
        commit=True,
    )
    flash("Produto criado com sucesso!", "success")
    return redirect(url_for("produtos.listar"))


# ---------- READ (detalhe) ----------
@produtos_bp.route("/<int:produto_id>")
def detalhe(produto_id):
    produto = run_query(
        """SELECT p.*, r.nome AS restaurante_nome
           FROM produtos p
           JOIN restaurantes r ON r.id = p.restaurante_id
           WHERE p.id = %s""",
        (produto_id,),
        fetchone=True,
    )
    if not produto:
        flash("Produto não encontrado.", "warning")
        return redirect(url_for("produtos.listar"))
    return render_template("produtos/detalhe.html", produto=produto)


# ---------- UPDATE ----------
@produtos_bp.route("/<int:produto_id>/editar", methods=["GET", "POST"])
def editar(produto_id):
    produto = run_query(
        "SELECT * FROM produtos WHERE id = %s", (produto_id,), fetchone=True
    )
    if not produto:
        flash("Produto não encontrado.", "warning")
        return redirect(url_for("produtos.listar"))

    if request.method == "GET":
        return render_template(
            "produtos/form.html", produto=produto,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    restaurante_id = request.form.get("restaurante_id", "").strip()
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip() or None
    categoria = request.form.get("categoria", "").strip()
    preco = request.form.get("preco", "").strip()
    imagem_url = request.form.get("imagem_url", "").strip() or None
    disponivel = 1 if request.form.get("disponivel") == "on" else 0

    if not restaurante_id or not nome or not categoria or not preco:
        flash("Restaurante, nome, categoria e preço são obrigatórios.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    if categoria not in CATEGORIAS_VALIDAS:
        flash("Categoria inválida.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    try:
        preco_val = float(preco.replace(",", "."))
        if preco_val < 0:
            raise ValueError
    except ValueError:
        flash("Preço deve ser um número válido e não negativo.", "danger")
        return render_template(
            "produtos/form.html", produto=request.form,
            restaurantes=_restaurantes_para_select(), categorias=CATEGORIAS_VALIDAS,
        )

    run_query(
        """UPDATE produtos SET
               restaurante_id=%s, nome=%s, descricao=%s, categoria=%s,
               preco=%s, imagem_url=%s, disponivel=%s
           WHERE id=%s""",
        (restaurante_id, nome, descricao, categoria, preco_val,
         imagem_url, disponivel, produto_id),
        commit=True,
    )
    flash("Produto atualizado com sucesso!", "success")
    return redirect(url_for("produtos.listar"))


# ---------- DELETE ----------
@produtos_bp.route("/<int:produto_id>/excluir", methods=["POST"])
def excluir(produto_id):
    run_query("DELETE FROM produtos WHERE id = %s", (produto_id,), commit=True)
    flash("Produto excluído com sucesso!", "success")
    return redirect(url_for("produtos.listar"))