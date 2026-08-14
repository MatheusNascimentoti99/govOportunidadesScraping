"""
app.py – Ponto de entrada da aplicação FastAPI com documentação OpenAPI completa.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

tags_metadata = [
    {
        "name": "Público - Inscrições",
        "description": "Endpoints para usuários finais realizarem cadastro de interesse em palavras-chave ou cancelamento de assinatura.",
    },
    {
        "name": "Interno - Scraper",
        "description": "Endpoints consumidos pelo crawler Scrapy (GitHub Actions) para consulta de assinantes ativos.",
    },
    {
        "name": "Interno - Notificações",
        "description": "Endpoints protegidos por API Key para envio assíncrono de notificações, deduplicação e auditoria.",
    },
    {
        "name": "Sistema",
        "description": "Monitoramento de integridade e disponibilidade da API.",
    },
]

app = FastAPI(
    title="GovOportunidades – Subscription & Notification API",
    description="""
API RESTful para gestão de assinaturas e disparo de alertas de editais governamentais coletados pelo robô Scrapy.

### Autenticação
* **Endpoints Públicos**: Não exigem autenticação.
* **Endpoints Internos**: Requerem o cabeçalho HTTP `X-API-Key: <sua_chave_secreta>`.

### Documentação
* **Swagger UI (Interativa)**: `/docs`
* **ReDoc (Documentação em tela cheia)**: `/redoc`
* **OpenAPI JSON Schema**: `/openapi.json`
""",
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)

