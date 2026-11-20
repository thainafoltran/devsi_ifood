from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import run_query
from app.auth_utils import login_required, usuario_atual

cesta_bp = Blueprint("cesta", __name__, url_prefix="/cesta")


def quantidade_na_cesta(conta_id):
    if not conta_id:
        return 0
    try:
        res = run_query(
            """SELECT COALESCE(SUM(ci.quantidade), 0) AS total
               FROM cesta_itens ci
               JOIN cestas c ON c.id = ci.cesta_id
               WHERE c.conta_id = ?""",
            (conta_id,),
            fetchone=True,
        )
        return res["total"] if res else 0
    except Exception:
        return 0


@cesta_bp.route("/")
@login_required
def ver():
    u = usuario_atual()
    cesta = run_query(
        """SELECT c.id, c.restaurante_id, r.nome AS restaurante_nome
           FROM cestas c
           JOIN restaurantes r ON r.id = c.restaurante_id
           WHERE c.conta_id = ?
           ORDER BY c.id DESC LIMIT 1""",
        (u["id"],),
        fetchone=True,
    )
    if not cesta:
        return render_template("cesta/index.html", cesta=None, itens=[], subtotal=0)

    rows = run_query(
        """SELECT ci.id, ci.quantidade, p.id AS produto_id, p.nome, p.preco,
                  p.disponivel, p.imagem_url AS imagem
           FROM cesta_itens ci
           JOIN produtos p ON p.id = ci.produto_id
           WHERE ci.cesta_id = ?""",
        (cesta["id"],),
        fetch=True,
    )

    itens = []
    subtotal = 0.0
    for r in rows:
        item = dict(r)
        item["total_item"] = item["preco"] * item["quantidade"]
        subtotal += item["total_item"]
        itens.append(item)

    return render_template("cesta/index.html", cesta=cesta, itens=itens, subtotal=subtotal)


@cesta_bp.route("/adicionar", methods=["POST"])
@cesta_bp.route("/adicionar/<int:produto_id>", methods=["POST"])
@login_required
def adicionar(produto_id=None):
    u = usuario_atual()
    produto_id = produto_id or request.form.get("produto_id", type=int)
    qtd = max(1, int(request.form.get("quantidade", 1)))

    if not produto_id:
        flash("Produto inválido.", "danger")
        return redirect(request.referrer or url_for("explorar.restaurantes"))

    produto = run_query(
        "SELECT id, restaurante_id FROM produtos WHERE id = ?",
        (produto_id,),
        fetchone=True,
    )
    if not produto:
        flash("Produto não encontrado.", "danger")
        return redirect(request.referrer or url_for("explorar.restaurantes"))

    cesta = run_query(
        "SELECT id, restaurante_id FROM cestas WHERE conta_id = ?",
        (u["id"],),
        fetchone=True,
    )

    if cesta and cesta["restaurante_id"] != produto["restaurante_id"]:
        run_query("DELETE FROM cesta_itens WHERE cesta_id = ?", (cesta["id"],), commit=True)
        run_query("DELETE FROM cestas WHERE id = ?", (cesta["id"],), commit=True)
        cesta = None

    if not cesta:
        cesta_id = run_query(
            "INSERT INTO cestas (conta_id, restaurante_id) VALUES (?, ?)",
            (u["id"], produto["restaurante_id"]),
            commit=True,
        )
    else:
        cesta_id = cesta["id"]

    existente = run_query(
        "SELECT id, quantidade FROM cesta_itens WHERE cesta_id = ? AND produto_id = ?",
        (cesta_id, produto_id),
        fetchone=True,
    )
    if existente:
        run_query(
            "UPDATE cesta_itens SET quantidade = ? WHERE id = ?",
            (existente["quantidade"] + qtd, existente["id"]),
            commit=True,
        )
    else:
        run_query(
            "INSERT INTO cesta_itens (cesta_id, produto_id, quantidade) VALUES (?, ?, ?)",
            (cesta_id, produto_id, qtd),
            commit=True,
        )

    flash("Item adicionado à cesta!", "success")
    return redirect(request.referrer or url_for("cesta.ver"))


@cesta_bp.route("/atualizar/<int:item_id>", methods=["POST"])
@login_required
def atualizar(item_id):
    u = usuario_atual()
    qtd = request.form.get("quantidade", type=int) or 0
    if qtd <= 0:
        run_query(
            """DELETE FROM cesta_itens
               WHERE id = ? AND cesta_id IN (SELECT id FROM cestas WHERE conta_id = ?)""",
            (item_id, u["id"]),
            commit=True,
        )
    else:
        run_query(
            """UPDATE cesta_itens SET quantidade = ?
               WHERE id = ? AND cesta_id IN (SELECT id FROM cestas WHERE conta_id = ?)""",
            (qtd, item_id, u["id"]),
            commit=True,
        )
    flash("Quantidade atualizada.", "success")
    return redirect(url_for("cesta.ver"))


@cesta_bp.route("/remover/<int:item_id>", methods=["POST"])
@login_required
def remover(item_id):
    u = usuario_atual()
    run_query(
        """DELETE FROM cesta_itens
           WHERE id = ? AND cesta_id IN (SELECT id FROM cestas WHERE conta_id = ?)""",
        (item_id, u["id"]),
        commit=True,
    )
    flash("Item removido da cesta.", "info")
    return redirect(url_for("cesta.ver"))


@cesta_bp.route("/limpar", methods=["POST"])
@login_required
def limpar():
    u = usuario_atual()
    cesta = run_query("SELECT id FROM cestas WHERE conta_id = ?", (u["id"],), fetchone=True)
    if cesta:
        run_query("DELETE FROM cesta_itens WHERE cesta_id = ?", (cesta["id"],), commit=True)
        run_query("DELETE FROM cestas WHERE id = ?", (cesta["id"],), commit=True)
    flash("Cesta esvaziada.", "info")
    return redirect(url_for("cesta.ver"))


@cesta_bp.route("/fechar", methods=["GET", "POST"])
@login_required
def fechar():
    u = usuario_atual()
    cesta = run_query(
        """SELECT c.id, c.restaurante_id, r.nome AS restaurante_nome, r.taxa_entrega
           FROM cestas c
           JOIN restaurantes r ON r.id = c.restaurante_id
           WHERE c.conta_id = ?
           ORDER BY c.id DESC LIMIT 1""",
        (u["id"],),
        fetchone=True,
    )
    if not cesta:
        flash("Sua cesta está vazia.", "warning")
        return redirect(url_for("cesta.ver"))

    rows = run_query(
        """SELECT ci.quantidade, p.id AS produto_id, p.nome, p.preco
           FROM cesta_itens ci
           JOIN produtos p ON p.id = ci.produto_id
           WHERE ci.cesta_id = ?""",
        (cesta["id"],),
        fetch=True,
    )
    if not rows:
        flash("Sua cesta está vazia.", "warning")
        return redirect(url_for("cesta.ver"))

    itens = []
    subtotal = 0.0
    for r in rows:
        item = dict(r)
        item["total_item"] = item["preco"] * item["quantidade"]
        subtotal += item["total_item"]
        itens.append(item)

    tipo = request.values.get("tipo_entrega", "entrega")
    if tipo not in ("entrega", "retirada"):
        tipo = "entrega"

    try:
        enderecos = run_query(
            "SELECT * FROM enderecos WHERE conta_id = ? ORDER BY id DESC",
            (u["id"],),
            fetch=True,
        )
    except Exception:
        enderecos = []

    endereco_id = request.values.get("endereco_id", type=int)
    if not endereco_id and enderecos:
        endereco_id = enderecos[0]["id"]

    erro_frete = None
    if tipo == "entrega" and not enderecos:
        erro_frete = "Cadastre um endereço ou escolha 'Retirar no local'."

    frete = float(cesta["taxa_entrega"] or 0.0) if tipo == "entrega" else 0.0
    total = subtotal + frete

    formas = {
        "pix": "PIX",
        "cartao_online": "Cartão de crédito (pelo app)",
        "cartao_entrega": "Cartão na entrega",
        "dinheiro": "Dinheiro",
    }
    forma = request.form.get("forma_pagamento", "pix")

    if request.method == "GET":
        return render_template(
            "cesta/fechar.html",
            cesta=cesta,
            tipo=tipo,
            enderecos=enderecos,
            endereco_id=endereco_id,
            erro_frete=erro_frete,
            itens=itens,
            subtotal=subtotal,
            dist=None,
            frete=frete,
            total=total,
            formas=formas,
            forma=forma,
        )

    if erro_frete:
        flash(erro_frete, "danger")
        return redirect(url_for("cesta.fechar", tipo_entrega=tipo))

    endereco_texto = None
    if tipo == "entrega" and endereco_id:
        end = next((e for e in enderecos if e["id"] == endereco_id), None)
        if end:
            endereco_texto = f"{end['logradouro']}, {end['numero']} - {end['bairro']}, {end['cidade']}"

    pedido_id = run_query(
        """INSERT INTO pedidos
           (conta_id, restaurante_id, endereco_id, endereco_texto,
            tipo_entrega, subtotal, taxa_frete, total, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'recebido')""",
        (
            u["id"],
            cesta["restaurante_id"],
            endereco_id if tipo == "entrega" else None,
            endereco_texto,
            tipo,
            subtotal,
            frete,
            total,
        ),
        commit=True,
    )

    for i in itens:
        run_query(
            """INSERT INTO pedido_itens
               (pedido_id, produto_id, nome, preco_unitario, quantidade, total_item)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pedido_id, i["produto_id"], i["nome"], i["preco"], i["quantidade"], i["total_item"]),
            commit=True,
        )

    run_query("DELETE FROM cesta_itens WHERE cesta_id = ?", (cesta["id"],), commit=True)
    run_query("DELETE FROM cestas WHERE id = ?", (cesta["id"],), commit=True)

    flash(f"Pedido #{pedido_id} realizado com sucesso!", "success")
    return redirect(url_for("explorar.restaurantes"))