"""
Testes da API FastAPI – tests/test_api.py
==========================================
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@localhost/fakedb")
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("SCRAPY_MAIL_HOST", "")
    monkeypatch.setenv("SCRAPY_MAIL_USER", "")
    monkeypatch.setenv("SCRAPY_MAIL_PASS", "")


def _make_mock_conn(fetchone_result=None, fetchall_result=None):
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = fetchone_result
    mock_cursor.fetchall.return_value = fetchall_result or []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def client():
    from api.app.app import app
    from api.app.models import get_db

    def override_get_db():
        conn, _ = _make_mock_conn()
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/subscribe
# ─────────────────────────────────────────────────────────────────────────────

def test_subscribe_success(client):
    resp = client.post(
        "/api/subscribe",
        json={"email": "user@example.com", "keywords": "engenharia,civil"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "user@example.com"
    assert "Inscrição realizada" in resp.json()["message"]


def test_subscribe_invalid_email(client):
    resp = client.post("/api/subscribe", json={"email": "not-an-email", "keywords": "engenharia"})
    assert resp.status_code == 422


def test_subscribe_empty_keywords(client):
    resp = client.post("/api/subscribe", json={"email": "user@example.com", "keywords": "   "})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/unsubscribe
# ─────────────────────────────────────────────────────────────────────────────

def _client_with_db(fetchone=None, fetchall=None):
    from api.app.app import app
    from api.app.models import get_db

    def override():
        conn, _ = _make_mock_conn(fetchone_result=fetchone, fetchall_result=fetchall)
        yield conn

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    return app, client


def test_unsubscribe_invalid_token():
    app, c = _client_with_db(fetchone=None)
    resp = c.get("/api/unsubscribe?token=invalid-token-xyz")
    app.dependency_overrides.clear()
    assert resp.status_code == 404


def test_unsubscribe_valid_token():
    app, c = _client_with_db(fetchone=("user@example.com",))
    resp = c.get("/api/unsubscribe?token=valid-token-abc")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert "cancelada" in resp.json()["message"]


# ─────────────────────────────────────────────────────────────────────────────
# Autenticação das rotas internas
# ─────────────────────────────────────────────────────────────────────────────

def test_internal_requires_api_key(client):
    resp = client.get("/api/internal/subscribers")
    assert resp.status_code == 422


def test_internal_wrong_api_key(client):
    resp = client.get("/api/internal/subscribers", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 403


def test_internal_correct_api_key():
    app, c = _client_with_db(fetchall=[("a@b.com", "engenharia,civil"), ("c@d.com", "TI")])
    resp = c.get("/api/internal/subscribers", headers={"X-API-Key": "test-secret-key"})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["subscribers"][0]["email"] == "a@b.com"
    assert "engenharia" in data["subscribers"][0]["keywords"]


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/internal/notifications/check-dedup
# ─────────────────────────────────────────────────────────────────────────────

def test_check_dedup_not_sent():
    app, c = _client_with_db(fetchone=None)
    resp = c.post(
        "/api/internal/notifications/check-dedup",
        headers={"X-API-Key": "test-secret-key"},
        json={"edital_url": "https://example.com/edital/1", "subscriber_email": "a@b.com"},
    )
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["already_sent"] is False


def test_check_dedup_already_sent():
    app, c = _client_with_db(fetchone=(1,))
    resp = c.post(
        "/api/internal/notifications/check-dedup",
        headers={"X-API-Key": "test-secret-key"},
        json={"edital_url": "https://example.com/edital/1", "subscriber_email": "a@b.com"},
    )
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["already_sent"] is True


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/internal/notifications/log
# ─────────────────────────────────────────────────────────────────────────────

def test_log_notification():
    app, c = _client_with_db()
    resp = c.post(
        "/api/internal/notifications/log",
        headers={"X-API-Key": "test-secret-key"},
        json={"edital_url": "https://example.com/edital/1", "subscriber_email": "a@b.com"},
    )
    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert "registrada" in resp.json()["message"]


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/internal/notifications/send (Async Background Dispatch)
# ─────────────────────────────────────────────────────────────────────────────

def test_send_notification_queued():
    """Notificação válida deve ser enfileirada e agendar envio assíncrono."""
    # 1ª consulta (dedup): None; 2ª consulta (active subscriber): (1,)
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.side_effect = [None, (1,)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    from api.app.app import app
    from api.app.models import get_db

    def override():
        yield mock_conn

    app.dependency_overrides[get_db] = override
    with patch("api.app.routes._send_opportunity_email") as mock_email:
        client = TestClient(app)
        resp = client.post(
            "/api/internal/notifications/send",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "edital_url": "https://example.com/edital/99",
                "subscriber_email": "user@example.com",
                "matched_keywords": ["engenharia", "civil"],
                "summary": "Resumo do edital",
                "text": "Texto completo...",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"
    mock_email.assert_called_once_with(
        "user@example.com",
        "https://example.com/edital/99",
        ["engenharia", "civil"],
        "Resumo do edital",
        "Texto completo...",
    )


def test_send_notification_already_sent():
    """Se já foi enviada notificação para a mesma URL/email, retorna already_sent sem agendar envio."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = (1,)  # já existe no log
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    from api.app.app import app
    from api.app.models import get_db

    def override():
        yield mock_conn

    app.dependency_overrides[get_db] = override
    with patch("api.app.routes._send_opportunity_email") as mock_email:
        client = TestClient(app)
        resp = client.post(
            "/api/internal/notifications/send",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "edital_url": "https://example.com/edital/99",
                "subscriber_email": "user@example.com",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 202
    assert resp.json()["status"] == "already_sent"
    mock_email.assert_not_called()


def test_send_notification_inactive_or_unknown_subscriber():
    """Se o assinante não for encontrado ou estiver inativo, não agenda envio."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    # 1ª consulta (dedup): None; 2ª consulta (active subscriber): None (não encontrado)
    mock_cursor.fetchone.side_effect = [None, None]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    from api.app.app import app
    from api.app.models import get_db

    def override():
        yield mock_conn

    app.dependency_overrides[get_db] = override
    with patch("api.app.routes._send_opportunity_email") as mock_email:
        client = TestClient(app)
        resp = client.post(
            "/api/internal/notifications/send",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "edital_url": "https://example.com/edital/99",
                "subscriber_email": "unknown@example.com",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 202
    assert resp.json()["status"] == "ignored"
    mock_email.assert_not_called()


def test_opportunity_email_body_contains_unsubscribe_link(monkeypatch):
    """Verifica que o e-mail montado por _send_opportunity_email contém o link de unsubscribe correto buscando o token no banco."""
    from api.app.routes import _send_opportunity_email

    monkeypatch.setenv("SCRAPY_MAIL_USER", "sender@test.com")
    monkeypatch.setenv("SCRAPY_MAIL_PASS", "pass123")
    monkeypatch.setenv("API_BASE_URL", "https://meu-app.vercel.app")

    sent_messages = []

    mock_server = MagicMock()
    mock_server.__enter__ = lambda s: s
    mock_server.__exit__ = MagicMock(return_value=False)

    def fake_sendmail(sender, recipients, msg_str):
        sent_messages.append((sender, recipients, msg_str))

    mock_server.sendmail = fake_sendmail

    with patch("smtplib.SMTP", return_value=mock_server), \
         patch("api.app.routes.get_unsubscribe_token_by_email", return_value="tok_secret_999") as mock_lookup, \
         patch("api.app.routes.SMTP_USER", "sender@test.com"), \
         patch("api.app.routes.SMTP_PASS", "pass123"), \
         patch("api.app.routes.APP_BASE_URL", "https://meu-app.vercel.app"):
        _send_opportunity_email(
            email="subscriber@example.com",
            edital_url="https://example.com/edital/500",
            matched_keywords=["dados", "ia"],
            summary="Oportunidade para Cientista de Dados.",
            text="Texto de teste...",
        )

    mock_lookup.assert_called_once_with("subscriber@example.com")
    assert len(sent_messages) == 1
    _, recipients, msg_raw = sent_messages[0]
    import email
    msg_obj = email.message_from_string(msg_raw)
    payload_bytes = msg_obj.get_payload(decode=True)
    msg_decoded = payload_bytes.decode("utf-8") if payload_bytes else msg_raw

    assert "subscriber@example.com" in recipients
    assert "https://meu-app.vercel.app/api/unsubscribe?token=tok_secret_999" in msg_decoded
    assert "Oportunidade para Cientista de Dados." in msg_decoded
    assert "https://example.com/edital/500" in msg_decoded


def test_api_summarize_with_openrouter_success():
    """Verifica que _summarize_with_openrouter chama a API e retorna o conteúdo gerado."""
    from api.app.routes import _summarize_with_openrouter

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Resumo gerado pelo OpenRouter na API."}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("api.app.routes.OPENROUTER_API_KEY", "test-sk-123"), \
         patch("requests.post", return_value=mock_resp) as mock_post:
        summary = _summarize_with_openrouter("Texto completo do edital governamental.")

    assert summary == "Resumo gerado pelo OpenRouter na API."
    mock_post.assert_called_once()


def test_api_summarize_with_openrouter_missing_key():
    """Se OPENROUTER_API_KEY estiver vazia, retorna string vazia sem fazer requisição HTTP."""
    from api.app.routes import _summarize_with_openrouter

    with patch("api.app.routes.OPENROUTER_API_KEY", ""), \
         patch("requests.post") as mock_post:
        summary = _summarize_with_openrouter("Texto do edital.")

    assert summary == ""
    mock_post.assert_not_called()


def test_opportunity_email_invokes_openrouter_when_summary_empty(monkeypatch):
    """Quando summary vem vazio mas text existe, _send_opportunity_email chama _summarize_with_openrouter."""
    from api.app.routes import _send_opportunity_email

    monkeypatch.setenv("SCRAPY_MAIL_USER", "sender@test.com")
    monkeypatch.setenv("SCRAPY_MAIL_PASS", "pass123")
    monkeypatch.setenv("API_BASE_URL", "https://meu-app.vercel.app")

    sent_messages = []
    mock_server = MagicMock()
    mock_server.__enter__ = lambda s: s
    mock_server.__exit__ = MagicMock(return_value=False)

    def fake_sendmail(sender, recipients, msg_str):
        sent_messages.append((sender, recipients, msg_str))

    mock_server.sendmail = fake_sendmail

    with patch("smtplib.SMTP", return_value=mock_server), \
         patch("api.app.routes.get_unsubscribe_token_by_email", return_value="tok_123"), \
         patch("api.app.routes.SMTP_USER", "sender@test.com"), \
         patch("api.app.routes.SMTP_PASS", "pass123"), \
         patch("api.app.routes.APP_BASE_URL", "https://meu-app.vercel.app"), \
         patch("api.app.routes._summarize_with_openrouter", return_value="Resumo automático via API") as mock_ai:
        _send_opportunity_email(
            email="user@test.com",
            edital_url="https://example.com/edital/777",
            matched_keywords=["ia"],
            summary="",
            text="Texto de edital extenso...",
        )

    mock_ai.assert_called_once_with("Texto de edital extenso...")
    assert len(sent_messages) == 1
    _, _, msg_raw = sent_messages[0]
    import email
    msg_obj = email.message_from_string(msg_raw)
    payload_bytes = msg_obj.get_payload(decode=True)
    msg_decoded = payload_bytes.decode("utf-8") if payload_bytes else msg_raw
    assert "Resumo automático via API" in msg_decoded




