"""
Testes do Pipeline Scrapy – tests/test_pipeline.py
====================================================
Simula respostas da API e verifica se o SubscriberNotificationPipeline
consome a API corretamente (sem fazer chamadas HTTP reais).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import json

import pytest
from scrapy import Item
from scrapy.item import Field


# Item de teste mínimo
class EditalItem(Item):
    url = Field()
    text = Field()
    summary = Field()
    matched_keywords = Field()


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline():
    """Instância do SubscriberNotificationPipeline com configuração de teste."""
    from govoportunidades.pipelines import SubscriberNotificationPipeline
    return SubscriberNotificationPipeline(
        api_base_url="https://fake-api.vercel.app",
        api_secret_key="test-secret",
        mail_host="smtp.test.com",
        mail_port=587,
        mail_user="bot@test.com",
        mail_pass="secret",
        mail_from="bot@test.com",
    )


@pytest.fixture
def mock_spider():
    spider = MagicMock()
    spider.logger = MagicMock()
    return spider


FAKE_SUBSCRIBERS = [
    {"email": "alice@example.com", "keywords": ["engenharia", "civil"]},
    {"email": "bob@example.com", "keywords": ["ti", "software"]},
]


# ─────────────────────────────────────────────────────────────────────────────
# open_spider – carregamento de assinantes
# ─────────────────────────────────────────────────────────────────────────────

def test_open_spider_loads_subscribers(pipeline, mock_spider):
    """open_spider deve buscar e armazenar os assinantes da API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"subscribers": FAKE_SUBSCRIBERS, "total": 2}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        pipeline.open_spider(mock_spider)

    mock_get.assert_called_once_with(
        "https://fake-api.vercel.app/api/internal/subscribers",
        headers={"X-API-Key": "test-secret"},
        timeout=30,
    )
    assert len(pipeline.subscribers) == 2
    assert pipeline.subscribers[0]["email"] == "alice@example.com"


def test_open_spider_handles_api_error(pipeline, mock_spider):
    """Falha na API deve resultar em lista vazia (sem crash)."""
    with patch("requests.get", side_effect=Exception("connection refused")):
        pipeline.open_spider(mock_spider)

    assert pipeline.subscribers == []
    mock_spider.logger.error.assert_called_once()


def test_open_spider_skips_when_no_config(mock_spider):
    """Pipeline sem API_BASE_URL configurado deve logar aviso e não chamar a API."""
    from govoportunidades.pipelines import SubscriberNotificationPipeline
    p = SubscriberNotificationPipeline(
        api_base_url="",
        api_secret_key="",
        mail_host="", mail_port=587, mail_user="", mail_pass="", mail_from="",
    )
    with patch("requests.get") as mock_get:
        p.open_spider(mock_spider)
    mock_get.assert_not_called()
    mock_spider.logger.warning.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# process_item – sem matched_keywords
# ─────────────────────────────────────────────────────────────────────────────

def test_process_item_no_keywords(pipeline, mock_spider):
    """Itens sem matched_keywords não devem disparar nenhuma chamada à API."""
    pipeline.subscribers = FAKE_SUBSCRIBERS
    item = EditalItem(url="https://example.com/edital/1", text="texto qualquer")

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        result = pipeline.process_item(item, mock_spider)

    assert result is item
    mock_post.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# process_item – item com keywords que batem
# ─────────────────────────────────────────────────────────────────────────────

def test_process_item_sends_email_when_keywords_match(pipeline, mock_spider):
    """Deve enviar e-mail e logar notificação quando há match de keywords."""
    pipeline.subscribers = FAKE_SUBSCRIBERS
    item = EditalItem(
        url="https://example.com/edital/42",
        text="Edital de engenharia civil do governo",
        matched_keywords=["engenharia", "civil"],
    )

    # check-dedup retorna False (ainda não enviado)
    dedup_response = MagicMock()
    dedup_response.json.return_value = {"already_sent": False}
    dedup_response.raise_for_status = MagicMock()

    # log retorna 201
    log_response = MagicMock()
    log_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=dedup_response) as mock_post, \
         patch.object(pipeline, "_send_email", return_value=True) as mock_send:
        # Segunda chamada ao mock_post será o log; precisamos distingui-las
        mock_post.side_effect = [dedup_response, log_response]
        pipeline.process_item(item, mock_spider)

    # Verificar que check-dedup foi chamado para alice (que tem keywords engenharia/civil)
    first_call_args = mock_post.call_args_list[0]
    assert "check-dedup" in first_call_args[0][0]

    # Verificar que _send_email foi chamado para alice
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs[0][0] == "alice@example.com"

    # Verificar que log foi chamado
    second_call_args = mock_post.call_args_list[1]
    assert "/log" in second_call_args[0][0]


def test_process_item_skips_when_already_sent(pipeline, mock_spider):
    """Não deve enviar e-mail quando check-dedup retorna already_sent=True."""
    pipeline.subscribers = [FAKE_SUBSCRIBERS[0]]  # apenas alice
    item = EditalItem(
        url="https://example.com/edital/42",
        text="Edital de engenharia civil",
        matched_keywords=["engenharia"],
    )

    dedup_response = MagicMock()
    dedup_response.json.return_value = {"already_sent": True}
    dedup_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=dedup_response), \
         patch.object(pipeline, "_send_email") as mock_send:
        pipeline.process_item(item, mock_spider)

    mock_send.assert_not_called()


def test_process_item_no_keyword_match_for_subscriber(pipeline, mock_spider):
    """Assinante cujas keywords não batem com o edital não deve ser notificado."""
    pipeline.subscribers = [FAKE_SUBSCRIBERS[1]]  # bob (TI, software)
    item = EditalItem(
        url="https://example.com/edital/99",
        text="Edital de engenharia civil",
        matched_keywords=["engenharia", "civil"],
    )

    with patch("requests.post") as mock_post, \
         patch.object(pipeline, "_send_email") as mock_send:
        pipeline.process_item(item, mock_spider)

    mock_post.assert_not_called()  # Nem chegou a verificar dedup
    mock_send.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# _send_email – falha SMTP não deve propagar exceção
# ─────────────────────────────────────────────────────────────────────────────

def test_send_email_smtp_failure_returns_false(pipeline, mock_spider):
    """Falha de SMTP deve retornar False sem levantar exceção."""
    import smtplib
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("connection failed")):
        result = pipeline._send_email(
            "user@example.com", "https://example.com/edital/1",
            "texto", "resumo", ["engenharia"], mock_spider,
        )
    assert result is False
    mock_spider.logger.error.assert_called_once()
