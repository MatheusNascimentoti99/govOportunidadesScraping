"""
schemas.py – Schemas Pydantic para request/response da API com documentação OpenAPI.
"""
from typing import List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Inscrição & Desinscrição (Público)
# ─────────────────────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    """Schema para cadastro ou atualização de assinante."""
    email: EmailStr = Field(
        ...,
        description="Endereço de e-mail do assinante que receberá os alertas de editais.",
        examples=["usuario@exemplo.com"],
    )
    keywords: str = Field(
        ...,
        description="Termos ou palavras-chave separados por vírgula para monitoramento no Diário Oficial/SIGEPE.",
        examples=["engenharia, civil, infraestrutura, tecnologia"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@exemplo.com",
                "keywords": "engenharia, civil, infraestrutura, ti",
            }
        }
    )

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("keywords não pode ser vazio.")
        return cleaned


class SubscribeResponse(BaseModel):
    """Resposta de confirmação de inscrição."""
    message: str = Field(
        ...,
        description="Mensagem informativa sobre o sucesso da inscrição/atualização.",
        examples=["Inscrição realizada com sucesso!"],
    )
    email: EmailStr = Field(
        ...,
        description="E-mail cadastrado ou atualizado no sistema.",
        examples=["usuario@exemplo.com"],
    )


class UnsubscribeResponse(BaseModel):
    """Resposta de cancelamento de assinatura."""
    message: str = Field(
        ...,
        description="Mensagem confirmando o cancelamento do recebimento de alertas.",
        examples=["Assinatura de usuario@exemplo.com cancelada com sucesso."],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Notificações e Crawler (Interno)
# ─────────────────────────────────────────────────────────────────────────────

class SubscriberItem(BaseModel):
    """Representação de um assinante ativo e seus termos de interesse."""
    email: EmailStr = Field(
        ...,
        description="E-mail do assinante ativo.",
        examples=["usuario@exemplo.com"],
    )
    keywords: List[str] = Field(
        ...,
        description="Lista de palavras-chave normalizadas em letras minúsculas cadastradas pelo assinante.",
        examples=[["engenharia", "civil", "ti"]],
    )


class SubscribersListResponse(BaseModel):
    """Lista de assinantes ativos para uso pelo pipeline do Scrapy."""
    subscribers: List[SubscriberItem] = Field(
        ...,
        description="Lista de assinantes ativos cadastrados no banco de dados.",
    )
    total: int = Field(
        ...,
        description="Total de assinantes ativos encontrados.",
        examples=[1],
    )


class NotificationSendRequest(BaseModel):
    """Payload enviado pelo Scrapy para notificar um assinante sobre um edital correspondente."""
    edital_url: str = Field(
        ...,
        description="URL completa do edital no portal do governo.",
        examples=["https://oportunidades.sigepe.gov.br/oportunidades/exemplo/123"],
    )
    subscriber_email: EmailStr = Field(
        ...,
        description="E-mail do assinante destinatário.",
        examples=["usuario@exemplo.com"],
    )
    matched_keywords: List[str] = Field(
        default_factory=list,
        description="Lista de palavras-chave que casaram com o conteúdo do edital.",
        examples=[["engenharia", "civil"]],
    )
    summary: str = Field(
        default="",
        description="Resumo executivo do edital gerado via IA (OpenRouter).",
        examples=["Edital de seleção para contratação temporária de engenheiro civil..."],
    )
    text: str = Field(
        default="",
        description="Texto bruto extraído do PDF ou página do edital.",
        examples=["Ministério da Gestão e Inovação em Serviços Públicos..."],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "edital_url": "https://oportunidades.sigepe.gov.br/oportunidades/exemplo/123",
                "subscriber_email": "usuario@exemplo.com",
                "matched_keywords": ["engenharia", "civil"],
                "summary": "Edital para seleção de consultores em obras públicas...",
                "text": "Extrato de edital publicado no Diário Oficial...",
            }
        }
    )


class NotificationSendResponse(BaseModel):
    """Status do enfileiramento ou descarte da notificação."""
    status: str = Field(
        ...,
        description="Status do processamento da notificação ('queued', 'already_sent', 'ignored').",
        examples=["queued"],
    )
    message: str = Field(
        ...,
        description="Descrição detalhada sobre a ação tomada.",
        examples=["Notificação enfileirada para envio assíncrono."],
    )


class DedupCheckRequest(BaseModel):
    """Payload para checagem de deduplicação de envio."""
    edital_url: str = Field(
        ...,
        description="URL do edital para verificação de histórico.",
        examples=["https://oportunidades.sigepe.gov.br/oportunidades/exemplo/123"],
    )
    subscriber_email: str = Field(
        ...,
        description="E-mail do assinante.",
        examples=["usuario@exemplo.com"],
    )


class DedupCheckResponse(BaseModel):
    """Resultado da checagem de deduplicação."""
    already_sent: bool = Field(
        ...,
        description="`true` se este edital já foi enviado anteriormente para o assinante informado; `false` caso contrário.",
        examples=[False],
    )


class NotificationLogRequest(BaseModel):
    """Payload para registro manual de log de notificação enviada."""
    edital_url: str = Field(
        ...,
        description="URL do edital notificado.",
        examples=["https://oportunidades.sigepe.gov.br/oportunidades/exemplo/123"],
    )
    subscriber_email: str = Field(
        ...,
        description="E-mail do assinante notificado.",
        examples=["usuario@exemplo.com"],
    )


class NotificationLogResponse(BaseModel):
    """Confirmação de registro do log de envio."""
    message: str = Field(
        ...,
        description="Mensagem de sucesso do registro de envio.",
        examples=["Notificação registrada com sucesso."],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sistema / Health
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Status operacional do serviço da API."""
    status: str = Field(
        ...,
        description="Status de disponibilidade da API.",
        examples=["ok"],
    )
    timestamp: str = Field(
        ...,
        description="Data e hora da checagem em formato ISO 8601 UTC.",
        examples=["2026-08-14T01:00:00.000000+00:00"],
    )


class ErrorResponse(BaseModel):
    """Modelo padrão para erros HTTP."""
    detail: str = Field(
        ...,
        description="Descrição detalhada do motivo do erro retornado pelo servidor.",
        examples=["API Key inválida."],
    )

