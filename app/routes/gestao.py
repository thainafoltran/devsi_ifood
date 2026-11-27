from flask import Blueprint, render_template
from app.db import run_query

gestao_bp = Blueprint("gestao", __name__, url_prefix="/gestao")


@gestao_bp.route("/")
def index():
    """Tela inicial da Gestão (CRUD): atalhos para cadastrar/editar/excluir os dados do sistema."""
    total = lambda tabela: run_query(f"SELECT COUNT(*) AS n FROM {tabela}", fetchone=True)["n"]
    contagens = {t: total(t) for t in ("contas", "restaurantes", "produtos", "enderecos")}
    return render_template("gestao/index.html", n=contagens)
