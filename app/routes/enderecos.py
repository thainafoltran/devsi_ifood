#Entrega 2 
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import run_query, transaction
from app.auth_utils import login_required, usuario_atual

enderecos_bp = Blueprint("enderecos", __name__, url_prefix="/enderecos")


def _ler_e_validar(form):
    """Retorna (dados, erros)."""
    d = {k: form.get(k, "").strip() for k in
         ("apelido", "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")}
    d["cep"] = re.sub(r"\D", "", d["cep"])
    d["uf"] = d["uf"].upper()
    d["principal"] = 1 if form.get("principal") == "on" else 0
    erros = []
    for campo, rotulo in (("apelido", "Apelido"), ("cep", "CEP"), ("logradouro", "Logradouro"),
                          ("numero", "Número"), ("bairro", "Bairro"), ("cidade", "Cidade"), ("uf", "UF")):
        if not d[campo]:
            erros.append(f"{rotulo} é obrigatório.")
    if d["apelido"] and len(d["apelido"]) > 30:
        erros.append("Apelido deve ter até 30 caracteres.")
    if d["cep"] and not re.fullmatch(r"\d{8}", d["cep"]):
        erros.append("CEP deve ter 8 dígitos.")
    if d["uf"] and not re.fullmatch(r"[A-Z]{2}", d["uf"]):
        erros.append("UF deve ter 2 letras.")
    if len(d["numero"]) > 10:
        erros.append("Número deve ter até 10 caracteres.")
    for c, lim in (("latitude", 90), ("longitude", 180)):
        bruto = form.get(c, "").strip().replace(",", ".")
        d[c] = None
        if bruto:
            try:
                v = float(bruto)
                if abs(v) > lim:
                    raise ValueError
                d[c] = v
            except ValueError:
                erros.append(f"{c.title()} inválida.")
    if (d["latitude"] is None) != (d["longitude"] is None):
        erros.append("Informe latitude e longitude juntas (ou nenhuma).")
    d["complemento"] = d["complemento"] or None
    return d, erros


def _meu(endereco_id):
    return run_query("SELECT * FROM enderecos WHERE id=? AND conta_id=?",
                     (endereco_id, usuario_atual()["id"]), fetchone=True)


# READ
@enderecos_bp.route("/")
@login_required
def listar():
    ends = run_query("SELECT * FROM enderecos WHERE conta_id=? ORDER BY principal DESC, id DESC",
                     (usuario_atual()["id"],), fetch=True)
    return render_template("enderecos/list.html", enderecos=ends)


# CREATE
@enderecos_bp.route("/novo", methods=["GET", "POST"])
@login_required
def criar():
    if request.method == "GET":
        return render_template("enderecos/form.html", e=None)
    d, erros = _ler_e_validar(request.form)
    if erros:
        for e in erros:
            flash(e, "danger")
        return render_template("enderecos/form.html", e=request.form), 400
    cid = usuario_atual()["id"]
    with transaction() as conn:
        tem = conn.execute("SELECT COUNT(*) FROM enderecos WHERE conta_id=?", (cid,)).fetchone()[0]
        if d["principal"] or tem == 0:           # primeiro endereço vira principal
            d["principal"] = 1
            conn.execute("UPDATE enderecos SET principal=0 WHERE conta_id=?", (cid,))
        conn.execute(
            """INSERT INTO enderecos (conta_id, apelido, cep, logradouro, numero, complemento,
               bairro, cidade, uf, latitude, longitude, principal)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, d["apelido"], d["cep"], d["logradouro"], d["numero"], d["complemento"],
             d["bairro"], d["cidade"], d["uf"], d["latitude"], d["longitude"], d["principal"]))
    flash("Endereço cadastrado!", "success")
    return redirect(url_for("enderecos.listar"))


# UPDATE
@enderecos_bp.route("/<int:endereco_id>/editar", methods=["GET", "POST"])
@login_required
def editar(endereco_id):
    e = _meu(endereco_id)
    if not e:
        flash("Endereço não encontrado.", "warning")
        return redirect(url_for("enderecos.listar"))
    if request.method == "GET":
        return render_template("enderecos/form.html", e=e)
    d, erros = _ler_e_validar(request.form)
    if erros:
        for er in erros:
            flash(er, "danger")
        return render_template("enderecos/form.html", e={**request.form, "id": endereco_id}), 400
    cid = usuario_atual()["id"]
    with transaction() as conn:
        if d["principal"]:
            conn.execute("UPDATE enderecos SET principal=0 WHERE conta_id=?", (cid,))
        conn.execute(
            """UPDATE enderecos SET apelido=?, cep=?, logradouro=?, numero=?, complemento=?, bairro=?,
               cidade=?, uf=?, latitude=?, longitude=?, principal=? WHERE id=? AND conta_id=?""",
            (d["apelido"], d["cep"], d["logradouro"], d["numero"], d["complemento"], d["bairro"],
             d["cidade"], d["uf"], d["latitude"], d["longitude"],
             d["principal"] or e["principal"], endereco_id, cid))
    flash("Endereço atualizado!", "success")
    return redirect(url_for("enderecos.listar"))


# DELETE
@enderecos_bp.route("/<int:endereco_id>/excluir", methods=["POST"])
@login_required
def excluir(endereco_id):
    e = _meu(endereco_id)
    if not e:
        flash("Endereço não encontrado.", "warning")
        return redirect(url_for("enderecos.listar"))
    cid = usuario_atual()["id"]
    with transaction() as conn:
        conn.execute("DELETE FROM enderecos WHERE id=? AND conta_id=?", (endereco_id, cid))
        if e["principal"]:                       # promove outro endereço a principal
            conn.execute("""UPDATE enderecos SET principal=1 WHERE id =
                            (SELECT id FROM enderecos WHERE conta_id=? ORDER BY id LIMIT 1)""", (cid,))
    flash("Endereço excluído.", "success")
    return redirect(url_for("enderecos.listar"))


@enderecos_bp.route("/<int:endereco_id>/principal", methods=["POST"])
@login_required
def tornar_principal(endereco_id):
    if _meu(endereco_id):
        cid = usuario_atual()["id"]
        with transaction() as conn:
            conn.execute("UPDATE enderecos SET principal=0 WHERE conta_id=?", (cid,))
            conn.execute("UPDATE enderecos SET principal=1 WHERE id=?", (endereco_id,))
        flash("Endereço principal atualizado.", "success")
    return redirect(url_for("enderecos.listar"))
