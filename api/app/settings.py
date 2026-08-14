"""
settings.py – Configurações carregadas das variáveis de ambiente.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ── Banco de Dados ─────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# ── Segurança ──────────────────────────────────────────────────────
API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "")

# ── SMTP ───────────────────────────────────────────────────────────
SMTP_HOST: str = os.getenv("SCRAPY_MAIL_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SCRAPY_MAIL_PORT", "587"))
SMTP_USER: str = os.getenv("SCRAPY_MAIL_USER", "")
SMTP_PASS: str = os.getenv("SCRAPY_MAIL_PASS", "")
SMTP_FROM: str = os.getenv("SCRAPY_MAIL_FROM", os.getenv("SCRAPY_MAIL_USER", ""))

# ── App ────────────────────────────────────────────────────────────
APP_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── OpenRouter (Resumo com LLM) ────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free").strip()
OPENROUTER_MAX_TEXT_LENGTH: int = int(os.getenv("OPENROUTER_MAX_TEXT_LENGTH", "4000"))

