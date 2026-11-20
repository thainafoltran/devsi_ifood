import random
from datetime import datetime
from flask import Blueprint, render_template, flash, redirect, url_for
from app.db import run_query
from app.auth_utils import login_required, usuario_atual

nf_bp = Blueprint("nf", __name__, url_prefix="/nf")


@nf_bp.route("/pedido/<int:pedido_id>")
@login_required
def exibir_nf(pedido_id):
    u = usuario_atual()

    # 1. Busca os dados do pedido, restaurante e cliente
    pedido = run_query(
        """SELECT p.*, r.nome AS restaurante_nome, r.cidade AS restaurante_cidade,
                  c.nome AS cliente_nome, c.email AS cliente_email, c.telefone AS cliente_telefone
           FROM pedidos p
           JOIN restaurantes r ON r.id = p.restaurante_id
           JOIN contas c ON c.id = p.conta_id
           WHERE p.id = ? AND p.conta_id = ?""",
        (pedido_id, u["id"]),
        fetchone=True,
    )

    if not pedido:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("explorar.restaurantes"))

    # 2. Busca os itens do pedido fechado
    itens = run_query(
        """SELECT pi.quantidade, pi.preco_unitario, pr.nome AS produto_nome
           FROM pedido_itens pi
           JOIN produtos pr ON pr.id = pi.produto_id
           WHERE pi.pedido_id = ?""",
        (pedido_id,),
        fetch=True,
    )

    # 3. Verifica se a NF já foi emitida no banco; se não, grava uma nova
    nf = run_query(
        "SELECT * FROM notas_fiscais WHERE pedido_id = ?",
        (pedido_id,),
        fetchone=True,
    )

    if not nf:
        numero_nf = f"{datetime.now().year}{pedido_id:06d}"
        chave_acesso = "".join([str(random.randint(0, 9)) for _ in range(44)])
        emitida_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        valor_total = pedido.get("total") or sum(
            i["quantidade"] * i["preco_unitario"] for i in itens
        )

        run_query(
            """INSERT INTO notas_fiscais (pedido_id, numero_nf, chave_acesso, valor_total, emitida_em)
               VALUES (?, ?, ?, ?, ?)""",
            (pedido_id, numero_nf, chave_acesso, valor_total, emitida_em),
            commit=True,
        )
        nf = run_query(
            "SELECT * FROM notas_fiscais WHERE pedido_id = ?",
            (pedido_id,),
            fetchone=True,
        )

    return render_template("nf/nota_fiscal.html", pedido=pedido, itens=itens, nf=nf)