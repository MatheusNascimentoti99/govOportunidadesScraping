"""
Testes da API FastAPI – govoportunidades/tests/test_api.py
==========================================================
Testa os endpoints públicos e a autenticação das rotas internas.
Usa o TestClient do FastAPI (httpx) com banco de dados mockado via pytest fixtures.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    """Configura variáveis de ambiente mínimas para os testes."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@localhost/fakedb")
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("SCRAPY_MAIL_HOST", "")
    monkeypatch.setenv("SCRAPY_MAIL_USER", "")
    monkeypatch.setenv("SCRAPY_MAIL_PASS", "")


def _make_mock_conn(fetchone_result=None, fetchall_result=None):
    """Cria um mock de conexão psycopg2 reutilizável."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = fetchone_result
    mock_cursor.fetchall.return_value = fetchall_result or []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


@pytest.fixture
def client():
    """Retorna um TestClient da aplicação com DB mockado."""
    from app import app, get_db

    def override_get_db():
        conn, _ = _make_mock_conn(
            fetchone_result=None,
            fetchall_result=[],
        )
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
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert "Inscrição realizada" in data["message"]


def test_subscribe_invalid_email(client):
    resp = client.post(
        "/api/subscribe",
        json={"email": "not-an-email", "keywords": "engenharia"},
    )
    assert resp.status_code == 422


def test_subscribe_empty_keywords(client):
    resp = client.post(
        "/api/subscribe",
        json={"email": "user@example.com", "keywords": "   "},
    )
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/unsubscribe
# ─────────────────────────────────────────────────────────────────────────────

def test_unsubscribe_invalid_token(client):
    """Token inválido deve retornar 404."""
    from app import app, get_db

    def override_get_db_not_found():
        conn, cursor = _make_mock_conn(fetchone_result=None)
        yield conn

    app.dependency_overrides[get_db] = override_get_db_not_found
    with TestClient(app) as c:
        resp = c.get("/api/unsubscribe?token=invalid-token-xyz")
    app.dependency_overrides.clear()
    assert resp.status_code == 404


def test_unsubscribe_valid_token():
    """Token válido deve cancelar a assinatura."""
    from app import app, get_db

    def override_get_db_found():
        conn, cursor = _make_mock_conn(fetchone_result=("user@example.com",))
        yield conn

    app.dependency_overrides[get_db] = override_get_db_found
    with TestClient(app) as c:
        resp = c.get("/api/unsubscribe?token=valid-token-abc")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert "cancelada" in resp.json()["message"]


# ─────────────────────────────────────────────────────────────────────────────
# Autenticação das rotas internas
# ─────────────────────────────────────────────────────────────────────────────

def test_internal_requires_api_key(client):
    """Rotas internas sem X-API-Key devem retornar 422 (campo obrigatório ausente)."""
    resp = client.get("/api/internal/subscribers")
    # FastAPI retorna 422 quando um Header obrigatório está ausente
    assert resp.status_code == 422


def test_internal_wrong_api_key(client):
    resp = client.get(
        "/api/internal/subscribers",
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 403


def test_internal_correct_api_key():
    """X-API-Key correta deve retornar 200 com a lista de assinantes."""
    from app import app, get_db

    def override_get_db():
        conn, cursor = _make_mock_conn(
            fetchall_result=[("a@b.com", "engenharia,civil"), ("c@d.com", "TI")]
        )
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        resp = c.get(
            "/api/internal/subscribers",
            headers={"X-API-Key": "test-secret-key"},
        )
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
    from app import app, get_db

    def override():
        conn, _ = _make_mock_conn(fetchone_result=None)
        yield conn

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        resp = c.post(
            "/api/internal/notifications/check-dedup",
            headers={"X-API-Key": "test-secret-key"},
            json={"edital_url": "https://example.com/edital/1", "subscriber_email": "a@b.com"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["already_sent"] is False


def test_check_dedup_already_sent():
    from app import app, get_db

    def override():
        conn, _ = _make_mock_conn(fetchone_result=(1,))
        yield conn

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
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
    from app import app, get_db

    def override():
        conn, _ = _make_mock_conn()
        yield conn

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        resp = c.post(
            "/api/internal/notifications/log",
            headers={"X-API-Key": "test-secret-key"},
            json={"edital_url": "https://example.com/edital/1", "subscriber_email": "a@b.com"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert "registrada" in resp.json()["message"]
