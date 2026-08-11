"""
routes.py – Todos os endpoints FastAPI (públicos + internos).
"""
from __future__ import annotations

import hashlib
import secrets
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from .models import get_db
from .schemas import DedupCheckRequest, NotificationLogRequest, SubscribeRequest
from .settings import API_SECRET_KEY, APP_BASE_URL, SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Segurança
# ─────────────────────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if not API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_SECRET_KEY não configurada no servidor.",
        )
    if not secrets.compare_digest(x_api_key, API_SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_unsubscribe_token(email: str) -> str:
    rand = secrets.token_hex(16)
    return hashlib.sha256(f"{email}{rand}".encode()).hexdigest()


def _send_confirmation_email(email: str, keywords: str, token: str) -> None:
    """Envia e-mail de confirmação de inscrição. Falha silenciosamente."""
    if not SMTP_USER or not SMTP_PASS:
        return
    unsubscribe_url = f"{APP_BASE_URL}/api/unsubscribe?token={token}"
    body = (
        f"Olá!\n\n"
        f"Sua inscrição para receber alertas de editais foi confirmada.\n\n"
        f"Palavras-chave monitoradas: {keywords}\n\n"
        f"Para cancelar sua inscrição, acesse:\n{unsubscribe_url}\n\n"
        f"Equipe GovOportunidades"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Inscrição confirmada – GovOportunidades"
    msg["From"] = SMTP_FROM
    msg["To"] = email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [email], msg.as_string())
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Públicos
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe(body: SubscribeRequest, conn=Depends(get_db)):
    """Cadastra um novo assinante ou atualiza as palavras-chave de um existente."""
    token = _generate_unsubscribe_token(body.email)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO subscribers (email, keywords, unsubscribe_token)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE
                SET keywords          = EXCLUDED.keywords,
                    active            = TRUE,
                    unsubscribe_token = EXCLUDED.unsubscribe_token
            RETURNING unsubscribe_token
            """,
            (body.email, body.keywords.strip(), token),
        )
        result = cur.fetchone()
        conn.commit()
        final_token = result[0] if result else token

    _send_confirmation_email(body.email, body.keywords, final_token)
    return {"message": "Inscrição realizada com sucesso!", "email": body.email}


@router.get("/api/unsubscribe")
def unsubscribe(
    token: str = Query(..., description="Token de cancelamento recebido no e-mail"),
    conn=Depends(get_db),
):
    """Cancela a assinatura de um usuário via token."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE subscribers SET active = FALSE WHERE unsubscribe_token = %s RETURNING email",
            (token,),
        )
        result = cur.fetchone()
        conn.commit()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token inválido ou assinatura já cancelada.",
        )
    return {"message": f"Assinatura de {result[0]} cancelada com sucesso."}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Internos (Scrapy / GitHub Actions)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/internal/subscribers", dependencies=[Depends(verify_api_key)])
def list_subscribers(conn=Depends(get_db)):
    """Retorna a lista de todos os assinantes ativos com suas palavras-chave."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT email, keywords FROM subscribers WHERE active = TRUE ORDER BY id"
        )
        rows = cur.fetchall()

    subscribers = [
        {
            "email": row[0],
            "keywords": [kw.strip().lower() for kw in row[1].split(",") if kw.strip()],
        }
        for row in rows
    ]
    return {"subscribers": subscribers, "total": len(subscribers)}


@router.post("/api/internal/notifications/check-dedup", dependencies=[Depends(verify_api_key)])
def check_dedup(body: DedupCheckRequest, conn=Depends(get_db)):
    """
    Verifica se uma notificação já foi enviada para o par (edital_url, subscriber_email).
    Retorna `{ "already_sent": true/false }`.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM notification_log WHERE edital_url = %s AND subscriber_email = %s LIMIT 1",
            (body.edital_url, body.subscriber_email),
        )
        already_sent = cur.fetchone() is not None

    return {"already_sent": already_sent}


@router.post(
    "/api/internal/notifications/log",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
def log_notification(body: NotificationLogRequest, conn=Depends(get_db)):
    """Registra que uma notificação foi enviada com sucesso."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO notification_log (edital_url, subscriber_email)
            VALUES (%s, %s)
            ON CONFLICT (edital_url, subscriber_email) DO NOTHING
            """,
            (body.edital_url, body.subscriber_email),
        )
        conn.commit()
    return {"message": "Notificação registrada com sucesso."}


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
