from flask import Blueprint, request, jsonify, render_template
from app.db import run_query

api_restaurantes_bp = Blueprint("api_restaurantes", __name__)


@api_restaurantes_bp.route("/mobile/restaurantes")
def tela_mobile():
    return render_template("mobile/restaurantes.html")


@api_restaurantes_bp.route("/api/restaurantes", methods=["GET"])
def listar():
    dados = run_query("SELECT * FROM restaurantes ORDER BY id DESC", fetch=True)
    return jsonify(dados), 200


@api_restaurantes_bp.route("/api/restaurantes", methods=["POST"])
def criar():
    body = request.get_json() or {}
    nome = body.get("nome", "").strip()
    categoria = body.get("categoria", "Geral").strip()
    cidade = body.get("cidade", "").strip()
    taxa_entrega = float(body.get("taxa_entrega", 0))

    if not nome or not cidade:
        return jsonify({"erro": "Nome e cidade são obrigatórios"}), 400

    novo_id = run_query(
        "INSERT INTO restaurantes (nome, categoria, cidade, taxa_entrega) VALUES (?, ?, ?, ?)",
        (nome, categoria, cidade, taxa_entrega),
        commit=True,
    )
    criado = run_query("SELECT * FROM restaurantes WHERE id = ?", (novo_id,), fetchone=True)
    return jsonify(criado), 201


@api_restaurantes_bp.route("/api/restaurantes/<int:restaurante_id>", methods=["PUT"])
def atualizar(restaurante_id):
    body = request.get_json() or {}
    existente = run_query("SELECT * FROM restaurantes WHERE id = ?", (restaurante_id,), fetchone=True)
    if not existente:
        return jsonify({"erro": "Restaurante não encontrado"}), 404

    nome = body.get("nome", existente["nome"]).strip()
    categoria = body.get("categoria", existente["categoria"]).strip()
    cidade = body.get("cidade", existente["cidade"]).strip()
    taxa_entrega = float(body.get("taxa_entrega", existente.get("taxa_entrega", 0)))

    run_query(
        """UPDATE restaurantes
           SET nome = ?, categoria = ?, cidade = ?, taxa_entrega = ?
           WHERE id = ?""",
        (nome, categoria, cidade, taxa_entrega, restaurante_id),
        commit=True,
    )
    atualizado = run_query("SELECT * FROM restaurantes WHERE id = ?", (restaurante_id,), fetchone=True)
    return jsonify(atualizado), 200


@api_restaurantes_bp.route("/api/restaurantes/<int:restaurante_id>", methods=["DELETE"])
def deletar(restaurante_id):
    run_query("DELETE FROM restaurantes WHERE id = ?", (restaurante_id,), commit=True)
    return jsonify({"mensagem": "Restaurante removido"}), 200