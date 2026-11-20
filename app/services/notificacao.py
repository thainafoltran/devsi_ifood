"""Envio do código de 6 dígitos. Sem credenciais configuradas, cai no modo DEV (imprime no console)."""
import os
import re
import smtplib
import logging
from email.message import EmailMessage
import requests

log = logging.getLogger(__name__)


def normalizar_telefone(t):
    d = re.sub(r"\D", "", t or "")
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    return d


def _e164(t):
    return "+55" + normalizar_telefone(t)


def _email(destino, texto):
    host = os.getenv("SMTP_HOST")
    if not host:
        return "dev"
    m = EmailMessage()
    m["Subject"] = "Seu código de acesso"
    m["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "no-reply@example.com"))
    m["To"] = destino
    m.set_content(texto)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
        s.starttls()
        if os.getenv("SMTP_USER"):
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
        s.send_message(m)
    return True


def _twilio(canal, destino, texto):
    sid, token = os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")
    origem = os.getenv("TWILIO_WHATSAPP_FROM" if canal == "whatsapp" else "TWILIO_SMS_FROM")
    if not (sid and token and origem):
        return "dev"
    para = _e164(destino)
    if canal == "whatsapp":
        para, origem = f"whatsapp:{para}", f"whatsapp:{origem}"
    r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                      auth=(sid, token), data={"From": origem, "To": para, "Body": texto}, timeout=15)
    r.raise_for_status()
    return True


def enviar_codigo(canal, destino, codigo):
    """True = enviado | 'dev' = simulado (console) | False = falhou"""
    texto = f"Seu código de acesso é {codigo}. Vale por 5 minutos. Não compartilhe com ninguém."
    try:
        r = _email(destino, texto) if canal == "email" else _twilio(canal, destino, texto)
    except Exception:
        log.exception("Falha ao enviar código")
        return False
    if r == "dev":
        print(f"[DEV] código {canal} para {destino}: {codigo}", flush=True)
    return r
