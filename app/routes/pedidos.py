from enum import Enum
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import run_query, transaction
from app.auth_utils import login_required, usuario_atual
from app.services.pagamento import FORMAS

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")

class StatusPedido(str, Enum):
    RECEBIDO = "recebido"
    CONFIRMADO = "confirmado"
    EM_PREPARO = "em_preparo"
    SAIU_PARA_ENTREGA = "saiu_para_entrega"
    PRONTO_PARA_RETIRADA = "pronto_para_retirada"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"

ROTULOS = {
    StatusPedido.RECEBIDO: "Pedido recebido", 
    StatusPedido.CONFIRMADO: "Restaurante confirmou",
    StatusPedido.EM_PREPARO: "Em preparo", 
    StatusPedido.SAIU_PARA_ENTREGA: "Saiu para entrega",
    StatusPedido.PRONTO_PARA_RETIRADA: "Pronto para retirada", 
    StatusPedido.ENTREGUE: "Entregue / concluído",
    StatusPedido.CANCELADO: "Cancelado"
}

FLUXO = {
    "entrega":  [StatusPedido.RECEBIDO, StatusPedido.CONFIRMADO, StatusPedido.EM_PREPARO, StatusPedido.SAIU_PARA_ENTREGA, StatusPedido.ENTREGUE],
    "retirada": [StatusPedido.RECEBIDO, StatusPedido.CONFIRMADO, StatusPedido.EM_PREPARO, StatusPedido.PRONTO_PARA_RETIRADA, StatusPedido.ENTREGUE],
}

def _pedido_do_cliente(pid):
    return run_query("""SELECT p.*, r.nome AS restaurante_nome, r.endereco AS restaurante_endereco,
                               r.telefone AS restaurante_telefone, c.nome AS cliente_nome, c.email AS cliente_email
                        FROM pedidos p JOIN restaurantes r ON r.id=p.restaurante_id
                        JOIN contas c ON c.id=p.conta_id
                        WHERE p.id=? AND p.conta_id=?""", (pid, usuario_atual()["id"]), fetchone=True)

def _pedido_do_restaurante(pid):
    return run_query("""SELECT p.* FROM pedidos p JOIN restaurantes r ON r.id=p.restaurante_id
                        WHERE p.id=? AND r.conta_id=?""", (pid, usuario_atual()["id"]), fetchone=True)


@pedidos_bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page
    
    peds = run_query("""SELECT p.*, r.nome AS restaurante_nome FROM pedidos p
                        JOIN restaurantes r ON r.id=p.restaurante_id
                        WHERE p.conta_id=? ORDER BY p.id DESC LIMIT ? OFFSET ?""", 
                     (usuario_atual()["id"], per_page, offset), fetch=True)
    
    return render_template("pedidos/list.html", pedidos=peds, rotulos=ROTULOS, page=page)


@pedidos_bp.route("/<int:pedido_id>")
@login_required
def detalhe(pedido_id):
    p = _pedido_do_cliente(pedido_id)
    if not p:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedidos.listar"))
    
    itens = run_query("SELECT * FROM pedido_itens WHERE pedido_id=?", (pedido_id,), fetch=True)
    pg = run_query("SELECT * FROM pagamentos WHERE pedido_id=?", (pedido_id,), fetchone=True)
    hist = {h["status"]: h["criado_em"] for h in run_query(
        "SELECT status, criado_em FROM pedido_status_historico WHERE pedido_id=?", (pedido_id,), fetch=True)}
    
    etapas = FLUXO[p["tipo_entrega"]]
    atual = etapas.index(p["status"]) if p["status"] in etapas else -1
    return render_template("pedidos/detalhe.html", p=p, itens=itens, pg=pg, hist=hist, etapas=etapas,
                           atual=atual, rotulos=ROTULOS, formas=FORMAS)


@pedidos_bp.route("/<int:pedido_id>/nota")
@login_required
def nota(pedido_id):
    p = _pedido_do_cliente(pedido_id)
    if not p:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedidos.listar"))
    itens = run_query("SELECT * FROM pedido_itens WHERE pedido_id=?", (pedido_id,), fetch=True)
    pg = run_query("SELECT * FROM pagamentos WHERE pedido_id=?", (pedido_id,), fetchone=True)
    return render_template("pedidos/nota.html", p=p, itens=itens, pg=pg, formas=FORMAS, rotulos=ROTULOS)


@pedidos_bp.route("/<int:pedido_id>/cancelar", methods=["POST"])
@login_required
def cancelar(pedido_id):
    p = _pedido_do_cliente(pedido_id)
    if not p or p["status"] != StatusPedido.RECEBIDO:
        flash("Este pedido não pode mais ser cancelado.", "danger")
        return redirect(url_for("pedidos.listar"))
    
    with transaction() as conn:
        conn.execute("UPDATE pedidos SET status=? WHERE id=?", (StatusPedido.CANCELADO, pedido_id))
        conn.execute("INSERT INTO pedido_status_historico (pedido_id, status) VALUES (?, ?)", (pedido_id, StatusPedido.CANCELADO))
        conn.execute("""UPDATE pagamentos SET status = CASE WHEN status='aprovado' THEN 'estornado' ELSE 'recusado' END
                        WHERE pedido_id=?""", (pedido_id,))
        
    flash("Pedido cancelado.", "success")
    return redirect(url_for("pedidos.detalhe", pedido_id=pedido_id))


# ---------- painel do restaurante ----------
@pedidos_bp.route("/painel")
@login_required
def painel():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    peds = run_query("""SELECT p.*, r.nome AS restaurante_nome, c.nome AS cliente_nome
                        FROM pedidos p JOIN restaurantes r ON r.id=p.restaurante_id
                        JOIN contas c ON c.id=p.conta_id
                        WHERE r.conta_id=? ORDER BY (p.status IN (?, ?)), p.id DESC LIMIT ? OFFSET ?""",
                     (usuario_atual()["id"], StatusPedido.ENTREGUE, StatusPedido.CANCELADO, per_page, offset), fetch=True)
                     
    for p in peds:
        et = FLUXO[p["tipo_entrega"]]
        p["proximo"] = et[et.index(p["status"]) + 1] if p["status"] in et[:-1] else None
        
    return render_template("pedidos/painel.html", pedidos=peds, rotulos=ROTULOS, page=page)


@pedidos_bp.route("/<int:pedido_id>/avancar", methods=["POST"])
@login_required
def avancar(pedido_id):
    p = _pedido_do_restaurante(pedido_id)
    if not p:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedidos.painel"))
        
    et = FLUXO[p["tipo_entrega"]]
    if p["status"] not in et[:-1]:
        flash("O pedido não pode avançar.", "danger")
        return redirect(url_for("pedidos.painel"))
        
    novo = et[et.index(p["status"]) + 1]
    
    with transaction() as conn:
        conn.execute("UPDATE pedidos SET status=? WHERE id=?", (novo, pedido_id))
        conn.execute("INSERT INTO pedido_status_historico (pedido_id, status) VALUES (?,?)", (pedido_id, novo))
        
        if novo == StatusPedido.ENTREGUE:
            conn.execute("""UPDATE pagamentos SET status='aprovado' 
                            WHERE pedido_id=? AND status='pendente'""", 
                         (pedido_id,))
                         
    flash(f"Pedido #{pedido_id:06d}: {ROTULOS[novo]}.", "success")
    return redirect(url_for("pedidos.painel"))