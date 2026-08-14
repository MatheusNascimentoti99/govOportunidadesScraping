"""
routes.py – Todos os endpoints FastAPI (públicos + internos) com documentação OpenAPI completa.
"""
from __future__ import annotations

import hashlib
import secrets
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status

from .models import get_db, get_unsubscribe_token_by_email
from .schemas import (
    DedupCheckRequest,
    DedupCheckResponse,
    ErrorResponse,
    HealthResponse,
    NotificationLogRequest,
    NotificationLogResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    SubscribeRequest,
    SubscribeResponse,
    SubscribersListResponse,
    UnsubscribeResponse,
)
from .settings import API_SECRET_KEY, APP_BASE_URL, SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Segurança
# ─────────────────────────────────────────────────────────────────────────────

def verify_api_key(
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
        description="Chave secreta compartilhada para autenticação em rotas internas.",
        examples=["sua-chave-secreta"],
    ),
) -> None:
    """Valida o cabeçalho X-API-Key com a variável API_SECRET_KEY em tempo constante."""
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


def _send_confirmation_email(email: str, keywords: str) -> None:
    """
    Envia e-mail de confirmação de inscrição.
    Busca o token de desinscrição no banco de dados a partir do e-mail.
    """
    if not SMTP_USER or not SMTP_PASS:
        return

    unsub_token = get_unsubscribe_token_by_email(email)
    if not unsub_token:
        return

    unsubscribe_url = f"{APP_BASE_URL}/api/unsubscribe?token={unsub_token}"
    body = (
        f"Olá!\n\n"
        f"Sua inscrição para receber alertas de editais foi confirmada.\n\n"
        f"Palavras-chave monitoradas: {keywords}\n\n"
        f"────────────────────────────────────────────\n"
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


def _send_opportunity_email(
    email: str,
    edital_url: str,
    matched_keywords: list[str],
    summary: str,
    text: str,
) -> None:
    """
    Envia e-mail de notificação de oportunidade com link de unsubscribe individual.
    Busca o token de desinscrição no banco de dados a partir do e-mail.
    """
    if not SMTP_USER or not SMTP_PASS:
        return

    token = get_unsubscribe_token_by_email(email)
    if not token:
        return

    keywords_str = ", ".join(matched_keywords) if matched_keywords else "geral"
    unsubscribe_url = f"{APP_BASE_URL}/api/unsubscribe?token={token}"

    if summary:
        details = summary
    elif text:
        details = f"Texto inicial:\n{text[:500]}"
    else:
        details = "Detalhes disponíveis no link do edital."

    body = (
        f"Olá!\n\n"
        f"Encontramos uma nova oportunidade que corresponde às suas palavras-chave: {keywords_str}\n\n"
        f"{details}\n\n"
        f"Link da oportunidade:\n{edital_url}\n\n"
        f"────────────────────────────────────────────\n"
        f"Para cancelar o recebimento destes alertas, acesse:\n{unsubscribe_url}\n\n"
        f"Equipe GovOportunidades"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Nova oportunidade encontrada: {keywords_str}"
    msg["From"] = SMTP_FROM
    msg["To"] = email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [email], msg.as_string())
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Públicos
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/subscribe",
    response_model=SubscribeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Público - Inscrições"],
    summary="Cadastrar ou atualizar assinatura de alertas",
    description=(
        "Cadastra um endereço de e-mail e uma lista de palavras-chave para monitoramento de editais. "
        "Se o e-mail já existir, as palavras-chave e o status ativo são atualizados. "
        "Um e-mail de confirmação é enviado em background com o link exclusivo de cancelamento."
    ),
    responses={
        201: {"description": "Inscrição criada ou atualizada com sucesso.", "model": SubscribeResponse},
        422: {"description": "Erro de validação nos dados enviados (ex: e-mail inválido ou keywords vazias)."},
        503: {"description": "Banco de dados indisponível.", "model": ErrorResponse},
    },
)
def subscribe(
    body: SubscribeRequest,
    background_tasks: BackgroundTasks,
    conn=Depends(get_db),
):
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
            """,
            (body.email, body.keywords.strip(), token),
        )
        conn.commit()

    background_tasks.add_task(_send_confirmation_email, body.email, body.keywords)
    return {"message": "Inscrição realizada com sucesso!", "email": body.email}


@router.get(
    "/api/unsubscribe",
    response_model=UnsubscribeResponse,
    tags=["Público - Inscrições"],
    summary="Cancelar assinatura de alertas",
    description="Desativa a assinatura do usuário identificado pelo token exclusivo enviado por e-mail.",
    responses={
        200: {"description": "Assinatura cancelada com sucesso.", "model": UnsubscribeResponse},
        404: {"description": "Token inválido ou assinatura já cancelada.", "model": ErrorResponse},
        503: {"description": "Banco de dados indisponível.", "model": ErrorResponse},
    },
)
def unsubscribe(
    token: str = Query(
        ...,
        description="Token de cancelamento recebido no rodapé do e-mail de notificação.",
        examples=["a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"],
    ),
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

@router.get(
    "/api/internal/subscribers",
    response_model=SubscribersListResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Interno - Scraper"],
    summary="Listar assinantes ativos",
    description="Retorna a lista de todos os assinantes ativos cadastrados no banco de dados e seus termos de busca normalizados.",
    responses={
        200: {"description": "Lista de assinantes retornada com sucesso.", "model": SubscribersListResponse},
        403: {"description": "API Key inválida.", "model": ErrorResponse},
        503: {"description": "Serviço ou banco de dados indisponível.", "model": ErrorResponse},
    },
)
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


@router.post(
    "/api/internal/notifications/send",
    response_model=NotificationSendResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
    tags=["Interno - Notificações"],
    summary="Despachar notificação de oportunidade encontrada",
    description=(
        "Recebe dados do edital correspondente a um assinante, verifica deduplicação no banco de dados, "
        "valida se o assinante está ativo e agenda o envio assíncrono do e-mail com resumo e link de descadastro."
    ),
    responses={
        202: {"description": "Notificação processada (enfileirada, duplicada ou ignorada).", "model": NotificationSendResponse},
        403: {"description": "API Key inválida.", "model": ErrorResponse},
        422: {"description": "Dados da requisição inválidos."},
        503: {"description": "Serviço ou banco de dados indisponível.", "model": ErrorResponse},
    },
)
def send_notification(
    body: NotificationSendRequest,
    background_tasks: BackgroundTasks,
    conn=Depends(get_db),
):
    """
    Recebe solicitação de notificação do crawler, verifica dedup
    e agenda o envio assíncrono do e-mail.
    """
    with conn.cursor() as cur:
        # 1. Verifica se já foi notificado
        cur.execute(
            "SELECT 1 FROM notification_log WHERE edital_url = %s AND subscriber_email = %s LIMIT 1",
            (body.edital_url, body.subscriber_email),
        )
        if cur.fetchone() is not None:
            return {"status": "already_sent", "message": "Notificação já enviada anteriormente."}

        # 2. Valida se assinante está ativo
        cur.execute(
            "SELECT 1 FROM subscribers WHERE email = %s AND active = TRUE LIMIT 1",
            (body.subscriber_email,),
        )
        if not cur.fetchone():
            return {"status": "ignored", "message": "Assinante inativo ou inexistente."}

        # 3. Registra no log de notificações
        cur.execute(
            """
            INSERT INTO notification_log (edital_url, subscriber_email)
            VALUES (%s, %s)
            ON CONFLICT (edital_url, subscriber_email) DO NOTHING
            """,
            (body.edital_url, body.subscriber_email),
        )
        conn.commit()

    # 4. Agenda envio do e-mail em background (busca o token pelo email internamente)
    background_tasks.add_task(
        _send_opportunity_email,
        body.subscriber_email,
        body.edital_url,
        body.matched_keywords,
        body.summary,
        body.text,
    )

    return {"status": "queued", "message": "Notificação enfileirada para envio assíncrono."}


@router.post(
    "/api/internal/notifications/check-dedup",
    response_model=DedupCheckResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Interno - Notificações"],
    summary="Verificar deduplicação de notificação",
    description="Verifica se uma notificação para a URL de um edital já foi registrada para um assinante específico.",
    responses={
        200: {"description": "Resultado da checagem retornado com sucesso.", "model": DedupCheckResponse},
        403: {"description": "API Key inválida.", "model": ErrorResponse},
        503: {"description": "Serviço ou banco de dados indisponível.", "model": ErrorResponse},
    },
)
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
    response_model=NotificationLogResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    tags=["Interno - Notificações"],
    summary="Registrar log de notificação enviada",
    description="Registra manualmente no banco de dados que uma notificação foi enviada para o par (edital_url, subscriber_email).",
    responses={
        201: {"description": "Notificação registrada com sucesso.", "model": NotificationLogResponse},
        403: {"description": "API Key inválida.", "model": ErrorResponse},
        503: {"description": "Serviço ou banco de dados indisponível.", "model": ErrorResponse},
    },
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

@router.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Sistema"],
    summary="Health check da API",
    description="Retorna o status operacional da API e timestamp atual em UTC.",
    responses={
        200: {"description": "API em funcionamento normal.", "model": HealthResponse},
    },
)
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

