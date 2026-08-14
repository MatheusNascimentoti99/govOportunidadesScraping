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

def test_process_item_dispatches_notification_when_keywords_match(pipeline, mock_spider):
    """Deve chamar endpoint de notificação na API quando há match de keywords."""
    pipeline.subscribers = FAKE_SUBSCRIBERS
    item = EditalItem(
        url="https://example.com/edital/42",
        text="Edital de engenharia civil do governo",
        summary="Resumo de teste",
        matched_keywords=["engenharia", "civil"],
    )

    send_response = MagicMock()
    send_response.json.return_value = {"status": "queued", "message": "Enfileirado"}
    send_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=send_response) as mock_post:
        pipeline.process_item(item, mock_spider)

    mock_post.assert_called_once()
    called_url, called_kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
    assert called_url == "https://fake-api.vercel.app/api/internal/notifications/send"
    assert called_kwargs["headers"]["X-API-Key"] == "test-secret"

    payload = json.loads(called_kwargs["data"])
    assert payload["edital_url"] == "https://example.com/edital/42"
    assert payload["subscriber_email"] == "alice@example.com"
    assert payload["matched_keywords"] == ["engenharia", "civil"]
    assert payload["summary"] == "Resumo de teste"


def test_process_item_handles_already_sent_response(pipeline, mock_spider):
    """Quando a API retorna status already_sent, pipeline registra em debug sem erro."""
    pipeline.subscribers = [FAKE_SUBSCRIBERS[0]]  # alice
    item = EditalItem(
        url="https://example.com/edital/42",
        text="Edital de engenharia civil",
        matched_keywords=["engenharia"],
    )

    send_response = MagicMock()
    send_response.json.return_value = {"status": "already_sent", "message": "Já enviado"}
    send_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=send_response) as mock_post:
        pipeline.process_item(item, mock_spider)

    mock_post.assert_called_once()
    mock_spider.logger.debug.assert_called_once()


def test_process_item_no_keyword_match_for_subscriber(pipeline, mock_spider):
    """Assinante cujas keywords não batem com o edital não deve receber disparo."""
    pipeline.subscribers = [FAKE_SUBSCRIBERS[1]]  # bob (TI, software)
    item = EditalItem(
        url="https://example.com/edital/99",
        text="Edital de engenharia civil",
        matched_keywords=["engenharia", "civil"],
    )

    with patch("requests.post") as mock_post:
        pipeline.process_item(item, mock_spider)

    mock_post.assert_not_called()


def test_dispatch_notification_api_failure_does_not_crash(pipeline, mock_spider):
    """Falha de rede ao chamar a API deve ser capturada no log sem propagar exceção."""
    with patch("requests.post", side_effect=Exception("Timeout da API")):
        result = pipeline._dispatch_notification(
            "https://example.com/edital/1",
            "user@example.com",
            ["engenharia"],
            "resumo",
            "texto",
            mock_spider,
        )
    assert result is False
    mock_spider.logger.error.assert_called_once()


def test_process_item_matches_keywords_from_text_automatically(pipeline, mock_spider):
    """Quando matched_keywords não está presente, extrai do texto usando palavras-chave dos assinantes."""
    pipeline.subscribers = FAKE_SUBSCRIBERS
    # alice quer 'engenharia', 'civil'; bob quer 'ti', 'software'
    item = EditalItem(
        url="https://example.com/edital/101",
        text="Vaga aberta para especialista em software e desenvolvimento.",
    )

    send_response = MagicMock()
    send_response.json.return_value = {"status": "queued"}
    send_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=send_response) as mock_post:
        result = pipeline.process_item(item, mock_spider)

    assert "software" in result.get("matched_keywords", [])
    mock_post.assert_called_once()
    payload = json.loads(mock_post.call_args[1]["data"])
    assert payload["subscriber_email"] == "bob@example.com"


