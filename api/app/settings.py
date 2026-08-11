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
