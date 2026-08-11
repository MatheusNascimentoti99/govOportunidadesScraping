"""
Ponto de entrada serverless para a Vercel.
A Vercel procura por uma variável `app` (ASGI) neste módulo.
"""
from api.app.app import app  # noqa: F401  – re-exporta para a Vercel encontrar
