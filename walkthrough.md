# Walkthrough: Serviço de Subscrição de Editais (Arquitetura API-Centric)

## O que foi implementado

### Arquivos Novos
| Arquivo | Descrição |
|---|---|
| [`app.py`](file:///c:/Users/mathe/govOportunidadesScraping/app.py) | API FastAPI completa com endpoints públicos e internos |
| [`api/index.py`](file:///c:/Users/mathe/govOportunidadesScraping/api/index.py) | Ponto de entrada serverless para a Vercel |
| [`vercel.json`](file:///c:/Users/mathe/govOportunidadesScraping/vercel.json) | Configuração de rotas serverless |
| [`tests/test_api.py`](file:///c:/Users/mathe/govOportunidadesScraping/tests/test_api.py) | 12 testes dos endpoints da API |
| [`tests/test_pipeline.py`](file:///c:/Users/mathe/govOportunidadesScraping/tests/test_pipeline.py) | 8 testes do novo pipeline Scrapy |

### Arquivos Modificados
| Arquivo | Alteração |
|---|---|
| [`pipelines.py`](file:///c:/Users/mathe/govOportunidadesScraping/govoportunidades/pipelines.py) | Nova classe `SubscriberNotificationPipeline` |
| [`settings.py`](file:///c:/Users/mathe/govOportunidadesScraping/govoportunidades/settings.py) | Novas settings `API_BASE_URL` e `API_SECRET_KEY` |
| [`.github/workflows/job.yml`](file:///c:/Users/mathe/govOportunidadesScraping/.github/workflows/job.yml) | Remove cache SQLite; adiciona `API_BASE_URL` / `API_SECRET_KEY` |
| [`requirements.txt`](file:///c:/Users/mathe/govOportunidadesScraping/requirements.txt) | Adicionado FastAPI, uvicorn, psycopg2-binary, httpx |
| [`.env.example`](file:///c:/Users/mathe/govOportunidadesScraping/.env.example) | Novas variáveis documentadas |

---

## Endpoints da API

### Públicos
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/subscribe` | Cadastra email + palavras-chave |
| `GET` | `/api/unsubscribe?token=...` | Cancela assinatura |
| `GET` | `/api/health` | Health check |

### Internos (requerem `X-API-Key`)
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/internal/subscribers` | Lista assinantes ativos |
| `POST` | `/api/internal/notifications/check-dedup` | Verifica se edital já foi enviado |
| `POST` | `/api/internal/notifications/log` | Registra notificação enviada |

---

## Resultados dos Testes

```
20 passed, 1 warning in 0.60s
```

Todos os 20 testes passaram, incluindo:
- ✅ Endpoints públicos (subscribe, unsubscribe, health)
- ✅ Autenticação por `X-API-Key` nas rotas internas
- ✅ Lógica de dedup (check + log)
- ✅ `open_spider` do pipeline carrega assinantes da API
- ✅ `process_item` filtra por keywords, verifica dedup e envia e-mail
- ✅ Resiliência a falhas SMTP e de conexão com a API

---

## Próximos Passos para Deploy

> [!IMPORTANT]
> Para ativar o pipeline de assinantes, descomente `SubscriberNotificationPipeline` em `settings.py` e configure os secrets abaixo.

### Secrets necessários no GitHub Actions
```
API_BASE_URL      → URL do deploy na Vercel (ex: https://gov-oportunidades.vercel.app)
API_SECRET_KEY    → Chave secreta forte (compartilhada entre Vercel e GitHub Actions)
```

### Variáveis de ambiente na Vercel
```
DATABASE_URL      → Connection string do PostgreSQL (Supabase / Neon)
API_SECRET_KEY    → Mesma chave do GitHub Actions
SCRAPY_MAIL_*     → Configurações SMTP para e-mails de confirmação
API_BASE_URL      → URL do próprio deploy
```

### Ativar o Pipeline
Em `govoportunidades/settings.py`, descomentar:
```python
"govoportunidades.pipelines.SubscriberNotificationPipeline": 350,
```
