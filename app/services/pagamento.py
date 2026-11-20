import re
import uuid
from datetime import date

FORMAS = {"pix": "Pix", "cartao_credito": "Cartão de crédito",
          "cartao_debito": "Cartão de débito", "dinheiro": "Dinheiro na entrega"}


def _luhn(numero):
    total = 0
    for i, d in enumerate(reversed(numero)):
        n = int(d)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _bandeira(n):
    if n.startswith("4"):
        return "Visa"
    if re.match(r"^(5[1-5]|2[2-7])", n):
        return "Mastercard"
    if re.match(r"^3[47]", n):
        return "Amex"
    if re.match(r"^(636368|438935|504175|451416|636297|5067|4576|4011|506699)", n):
        return "Elo"
    return "Outra"


def validar_pagamento(forma, total, form):
    """Valida e 'processa' o pagamento (gateway simulado).
    Retorna dict com status/bandeira/cartao_final/troco_para/transacao_id. Lança ValueError se inválido."""
    if forma not in FORMAS:
        raise ValueError("Forma de pagamento inválida.")
    res = {"forma": forma, "status": "aprovado", "bandeira": None, "cartao_final": None,
           "troco_para": None, "transacao_id": uuid.uuid4().hex[:20].upper()}

    if forma == "pix":
        return res                                   # confirmação simulada

    if forma == "dinheiro":
        res["status"] = "pendente"                   # cobrado na entrega
        res["transacao_id"] = None
        troco = form.get("troco_para", "").strip().replace(",", ".")
        if troco:
            try:
                v = float(troco)
            except ValueError:
                raise ValueError("Valor do troco inválido.")
            if v < total:
                raise ValueError("O valor para troco deve ser maior ou igual ao total do pedido.")
            res["troco_para"] = round(v, 2)
        return res

    numero = re.sub(r"\D", "", form.get("cartao_numero", ""))
    nome = form.get("cartao_nome", "").strip()
    validade = form.get("cartao_validade", "").strip()
    cvv = form.get("cartao_cvv", "").strip()

    if not (13 <= len(numero) <= 19) or not _luhn(numero):
        raise ValueError("Número de cartão inválido.")
    if len(nome) < 3:
        raise ValueError("Informe o nome impresso no cartão.")
    m = re.fullmatch(r"(\d{2})/(\d{2})", validade)
    if not m or not 1 <= int(m.group(1)) <= 12:
        raise ValueError("Validade inválida (use MM/AA).")
    ano, mes = 2000 + int(m.group(2)), int(m.group(1))
    hoje = date.today()
    if (ano, mes) < (hoje.year, hoje.month):
        raise ValueError("Cartão vencido.")
    if not re.fullmatch(r"\d{3,4}", cvv):
        raise ValueError("CVV inválido.")

    res["bandeira"] = _bandeira(numero)
    res["cartao_final"] = numero[-4:]                # nunca gravamos o número completo nem o CVV
    return res
