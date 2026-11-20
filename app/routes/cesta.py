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
    subtotal = 0
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