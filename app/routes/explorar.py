#entrega 2
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import run_query
from app.auth_utils import login_required, usuario_atual, safe_next
from app.services.geo import origem, filtrar_proximos, anotar_distancia

explorar_bp = Blueprint("explorar", __name__)

CATEGORIAS_PRODUTO = ["Lanche", "Refeição", "Bebida", "Sobremesa", "Entrada", "Combo"]
RAIO_PADRAO_KM = 10


def _raio():
    r = request.args.get("raio", type=float) or RAIO_PADRAO_KM
    return min(max(r, 1), 50)


def _aviso_proximos(ref):
    if not ref:
        flash("Para ver o que está perto, cadastre um endereço ou permita sua localização.", "warning")


# ------------------------- RESTAURANTES -------------------------
@explorar_bp.route("/explorar/restaurantes")
def restaurantes():
    u = usuario_atual()
    uid = u["id"] if u else 0
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    so_fav = request.args.get("favoritos") == "1" and u
    proximos = request.args.get("proximos") == "1"

    sql = """SELECT r.*, (f.conta_id IS NOT NULL) AS favorito
             FROM restaurantes r
             LEFT JOIN favoritos_restaurantes f ON f.restaurante_id = r.id AND f.conta_id = ?
             WHERE r.ativo = 1"""
    params = [uid]
    if categoria:
        sql += " AND r.categoria = ?"
        params.append(categoria)
    if q:
        sql += " AND r.nome LIKE ?"
        params.append(f"%{q}%")
    if so_fav:
        sql += " AND f.conta_id IS NOT NULL"
    sql += " ORDER BY r.avaliacao DESC, r.nome"
    lista = run_query(sql, params, fetch=True)

    ref = origem(uid, request.args)
    if proximos:
        _aviso_proximos(ref)
        lista = filtrar_proximos(lista, ref, _raio()) if ref else []
    else:
        anotar_distancia(lista, ref)

    cats = [c["categoria"] for c in run_query(
        "SELECT DISTINCT categoria FROM restaurantes WHERE ativo=1 ORDER BY categoria", fetch=True)]
    enderecos = run_query("SELECT id, apelido FROM enderecos WHERE conta_id=?", (uid,), fetch=True) if u else []
    return render_template("explorar/restaurantes.html", restaurantes=lista, categorias=cats,
                           enderecos=enderecos, f=request.args, ref=ref, raio=_raio())


@explorar_bp.route("/explorar/restaurantes/<int:restaurante_id>")
def cardapio(restaurante_id):
    u = usuario_atual()
    uid = u["id"] if u else 0
    r = run_query("""SELECT r.*, (f.conta_id IS NOT NULL) AS favorito FROM restaurantes r
                     LEFT JOIN favoritos_restaurantes f ON f.restaurante_id=r.id AND f.conta_id=?
                     WHERE r.id=? AND r.ativo=1""", (uid, restaurante_id), fetchone=True)
    if not r:
        flash("Restaurante não encontrado.", "warning")
        return redirect(url_for("explorar.restaurantes"))
    produtos = run_query("""SELECT p.*, (f.conta_id IS NOT NULL) AS favorito FROM produtos p
                            LEFT JOIN favoritos_produtos f ON f.produto_id=p.id AND f.conta_id=?
                            WHERE p.restaurante_id=? AND p.disponivel=1 ORDER BY p.categoria, p.nome""",
                         (uid, restaurante_id), fetch=True)
    return render_template("explorar/cardapio.html", r=r, produtos=produtos)


# ------------------------- PRODUTOS -------------------------
@explorar_bp.route("/explorar/produtos")
def produtos():
    u = usuario_atual()
    uid = u["id"] if u else 0
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    so_fav = request.args.get("favoritos") == "1" and u
    proximos = request.args.get("proximos") == "1"

    sql = """SELECT p.*, r.nome AS restaurante_nome, r.cidade, r.latitude, r.longitude,
                    r.taxa_entrega, (f.conta_id IS NOT NULL) AS favorito
             FROM produtos p
             JOIN restaurantes r ON r.id = p.restaurante_id AND r.ativo = 1
             LEFT JOIN favoritos_produtos f ON f.produto_id = p.id AND f.conta_id = ?
             WHERE p.disponivel = 1"""
    params = [uid]
    if categoria in CATEGORIAS_PRODUTO:
        sql += " AND p.categoria = ?"
        params.append(categoria)
    if q:
        sql += " AND (p.nome LIKE ? OR p.descricao LIKE ?)"
        params += [f"%{q}%"] * 2
    if so_fav:
        sql += " AND f.conta_id IS NOT NULL"
    sql += " ORDER BY p.nome"
    lista = run_query(sql, params, fetch=True)

    ref = origem(uid, request.args)
    if proximos:
        _aviso_proximos(ref)
        lista = filtrar_proximos(lista, ref, _raio()) if ref else []
    else:
        anotar_distancia(lista, ref)
    enderecos = run_query("SELECT id, apelido FROM enderecos WHERE conta_id=?", (uid,), fetch=True) if u else []
    return render_template("explorar/produtos.html", produtos=lista, categorias=CATEGORIAS_PRODUTO,
                           enderecos=enderecos, f=request.args, ref=ref, raio=_raio())


# ------------------------- FAVORITOS -------------------------
def _alternar(tabela, coluna, item_id):
    uid = usuario_atual()["id"]
    existe = run_query(f"SELECT 1 FROM {tabela} WHERE conta_id=? AND {coluna}=?", (uid, item_id), fetchone=True)
    if existe:
        run_query(f"DELETE FROM {tabela} WHERE conta_id=? AND {coluna}=?", (uid, item_id), commit=True)
        flash("Removido dos favoritos.", "info")
    else:
        run_query(f"INSERT INTO {tabela} (conta_id, {coluna}) VALUES (?, ?)", (uid, item_id), commit=True)
        flash("Adicionado aos favoritos!", "success")


@explorar_bp.route("/favoritos/restaurante/<int:restaurante_id>", methods=["POST"])
@login_required
def favoritar_restaurante(restaurante_id):
    if run_query("SELECT 1 FROM restaurantes WHERE id=?", (restaurante_id,), fetchone=True):
        _alternar("favoritos_restaurantes", "restaurante_id", restaurante_id)
    return redirect(safe_next(request.form.get("next"), url_for("explorar.restaurantes")))


@explorar_bp.route("/favoritos/produto/<int:produto_id>", methods=["POST"])
@login_required
def favoritar_produto(produto_id):
    if run_query("SELECT 1 FROM produtos WHERE id=?", (produto_id,), fetchone=True):
        _alternar("favoritos_produtos", "produto_id", produto_id)
    return redirect(safe_next(request.form.get("next"), url_for("explorar.produtos")))
