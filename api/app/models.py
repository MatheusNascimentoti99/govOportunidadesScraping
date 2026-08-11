"""
models.py – Camada de banco de dados: conexão, schema e dependency get_db.
"""
from __future__ import annotations

from typing import Generator

import psycopg2
from fastapi import HTTPException, status

from .settings import DATABASE_URL


# ─────────────────────────────────────────────────────────────────────────────
# Dependency FastAPI
# ─────────────────────────────────────────────────────────────────────────────

def get_db() -> Generator:
    """Abre uma conexão psycopg2, garante o schema e fecha ao término da request."""
    if not DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL não configurada.",
        )
    conn = psycopg2.connect(DATABASE_URL)
    _ensure_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Schema DDL (idempotente)
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_schema(conn) -> None:
    """Cria tabelas se não existirem."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                id                SERIAL PRIMARY KEY,
                email             TEXT NOT NULL UNIQUE,
                keywords          TEXT NOT NULL,
                unsubscribe_token TEXT NOT NULL UNIQUE,
                active            BOOLEAN NOT NULL DEFAULT TRUE,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_log (
                id               SERIAL PRIMARY KEY,
                edital_url       TEXT NOT NULL,
                subscriber_email TEXT NOT NULL,
                sent_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (edital_url, subscriber_email)
            );
            """
        )
        conn.commit()
