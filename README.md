# govOportunidadesScraping

Coletor inteligente (Scrapy) e API RESTful (FastAPI) para monitorar oportunidades governamentais (editais) no portal do SIGEPE, extrair conteúdo de PDFs, gerar resumos com IA (OpenRouter), cruzar palavras-chave e notificar assinantes por e-mail com controle de desinscrição e deduplicação.

[![Vercel Deployment](https://img.shields.io/badge/API%20Docs-Vercel%20Live-0070F3?style=for-the-badge&logo=vercel&logoColor=white)](https://gov-oportunidades-scraping.vercel.app/docs)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Scrapy](https://img.shields.io/badge/Scrapy-2.11+-red?style=for-the-badge&logo=scrapy)](https://scrapy.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-28%20passed-success?style=for-the-badge)](tests/)

<img width="1372" height="432" alt="image" src="https://github.com/user-attachments/assets/8eaef6de-88de-4976-8d78-5b6ee6178a31" />

---

## 🌐 Acesso em Produção (Live Demo)

A API RESTful está publicada e em execução na **Vercel Serverless**:

- 🚀 **Swagger UI (Interativo)**: [https://gov-oportunidades-scraping.vercel.app/docs](https://gov-oportunidades-scraping.vercel.app/docs)
- 📑 **ReDoc**: [https://gov-oportunidades-scraping.vercel.app/redoc](https://gov-oportunidades-scraping.vercel.app/redoc)
- 📋 **OpenAPI JSON Schema**: [https://gov-oportunidades-scraping.vercel.app/openapi.json](https://gov-oportunidades-scraping.vercel.app/openapi.json)

---

## 💡 Visão Geral da Arquitetura

O sistema opera de forma desacoplada em duas frentes complementares:

```
┌────────────────────────────────────────────────────────┐
│                   PORTAL SIGEPE                        │
└──────────────────────────┬─────────────────────────────┘
                           │ (Crawling & PDF download)
                           ▼
┌────────────────────────────────────────────────────────┐
│               SCRAPY SPIDER (Crawler)                  │
│  - Extração de texto de PDFs via pdfplumber            │
│  - Busca de assinantes na API                          │
│  - Matching de palavras-chave                          │
│  - Dispatch de notificações via API                    │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP POST (X-API-Key)
                           ▼
┌────────────────────────────────────────────────────────┐
│             FASTAPI REST API (Vercel)                  │
│  - Gestão de Assinaturas (Subscribe / Unsubscribe)     │
│  - Resumos automáticos com IA (OpenRouter / LLM)       │
│  - Deduplicação e registro de histórico (PostgreSQL)   │
│  - Disparo de e-mails via SMTP com link de descadastro │
└────────────────────────────────────────────────────────┘
```

1. **Gestão de Assinantes**: Usuários cadastram e-mail e palavras-chave de interesse através do endpoint público `/api/subscribe`.
2. **Coleta de Editais**: O robô Scrapy acessa a página inicial do SIGEPE, identifica novos editais publicados e efetua o download dos documentos PDF.
3. **Extração e Inteligência Artificial**: O texto do PDF é extraído via `pdfplumber` e, caso configurado, é sintetizado em um resumo executivo por LLM via **OpenRouter**.
4. **Matching & Deduplicação**: O pipeline cruza o texto com as palavras-chave cadastradas pelos assinantes e consulta a API para evitar envios duplicados para o mesmo edital/usuário.
5. **Notificação por E-mail**: Notificações personalizadas são disparadas via SMTP, contendo o resumo gerado pela IA, link do edital e token exclusivo para descadastro com 1 clique.
6. **Automação Contínua**: Execução periódica automatizada via **GitHub Actions** (sem custos) ou agendamento local via **Cron**.

---

## 📖 Endpoints da API

A documentação interativa completa com possibilidade de testes diretos pode ser acessada em [https://gov-oportunidades-scraping.vercel.app/docs](https://gov-oportunidades-scraping.vercel.app/docs).

### 🟢 Endpoints Públicos

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/subscribe` | Cadastra ou atualiza assinatura com e-mail e palavras-chave. Envia e-mail de confirmação. |
| `GET` | `/api/unsubscribe` | Cancela a assinatura usando o token único recebido por e-mail (`?token=...`). |
| `GET` | `/api/health` | Verifica a integridade e disponibilidade da API e conexão com banco de dados. |

### 🔒 Endpoints Internos (Autenticação via `X-API-Key`)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/internal/subscribers` | Retorna a lista de assinantes ativos e suas respectivas palavras-chave. |
| `POST` | `/api/internal/notifications/send` | Dispara e-mail de oportunidade para o assinante com resumo de IA. |
| `POST` | `/api/internal/notifications/check-dedup` | Verifica se um edital já foi notificado para determinado usuário. |
| `POST` | `/api/internal/notifications/log` | Registra histórico de envio para fins de auditoria e controle de deduplicação. |

---

## 💻 Exemplo de Uso da API

### Cadastrar interesse em palavras-chave:

```bash
curl -X POST "https://gov-oportunidades-scraping.vercel.app/api/subscribe" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seu.email@exemplo.com",
    "keywords": ["tecnologia", "desenvolvimento", "inteligencia artificial"]
  }'
```

**Resposta:**
```json
{
  "status": "success",
  "message": "Inscrição realizada com sucesso. Um e-mail de confirmação foi enviado.",
  "email": "seu.email@exemplo.com",
  "keywords": ["tecnologia", "desenvolvimento", "inteligencia artificial"]
}
```

---

## 📁 Estrutura do Projeto

```
. 
├── api/                          # Aplicação FastAPI (Vercel Serverless / Docker)
│   ├── app/
│   │   ├── app.py                # Configuração do FastAPI, OpenAPI tags e CORS
│   │   ├── routes.py             # Endpoints públicos e protegidos + IA OpenRouter
│   │   ├── schemas.py            # Schemas Pydantic com validação de dados
│   │   ├── models.py             # Camada de banco de dados PostgreSQL
│   │   └── settings.py           # Variáveis de ambiente da API
│   └── index.py                  # Ponto de entrada ASGI para Vercel
├── govoportunidades/             # Scraper Scrapy
│   ├── spiders/
│   │   └── edital.py             # Spider para o portal de editais SIGEPE
│   ├── items.py                  # Definição de itens do Scrapy
│   ├── pipelines.py              # Pipelines de deduplicação, SQLite e API dispatch
│   └── settings.py               # Configurações do Scrapy
├── tests/                        # Bateria de testes automatizados (pytest)
│   ├── test_api.py               # Testes de integração da API
│   └── test_pipeline.py          # Testes dos pipelines Scrapy
├── scripts/
│   └── run_crawl.sh              # Script de execução para cron com locks e logs
├── .github/workflows/
│   └── job.yml                   # Execução automatizada diária via GitHub Actions
├── docker-compose.yml            # PostgreSQL + API FastAPI para ambiente local
├── Dockerfile                    # Container Docker para a API e Scraper
├── vercel.json                   # Configuração de build serverless para Vercel
├── requirements.txt              # Dependências Python
└── README.md                     # Este arquivo
```

---

## 🛠️ Como Executar Localmente

### Pré-requisitos
- Python 3.10+
- Docker & Docker Compose (opcional, para rodar API e PostgreSQL locais)

### 1. Clonar o repositório

```bash
git clone https://github.com/MatheusNascimentoti99/govOportunidadesScraping.git
cd govOportunidadesScraping
```

### 2. Configurar o ambiente virtual

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente (`.env`)

Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

Edite o `.env` preenchendo suas configurações (veja a seção [Variáveis de Ambiente](#-variáveis-de-ambiente)).

---

### 4. Executando com Docker Compose (API + PostgreSQL)

Para subir o banco de dados PostgreSQL e a API FastAPI localmente:

```bash
docker compose up -d
```

Acesse a documentação local em: `http://localhost:8000/docs`

---

### 5. Executando o Crawler (Scrapy)

Para rodar o spider localmente e exportar o resultado para um arquivo JSON:

```bash
scrapy crawl edital -O saida.json -L INFO
```

---

### 6. Executando os Testes Automatizados

O projeto conta com suite de testes completa cobrindo endpoints, autenticação e pipelines:

```bash
python -m pytest
```

---

## ⚙️ Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|---|---|---|
| `DATABASE_URL` | String de conexão do PostgreSQL | `postgresql://govuser:govpassword@localhost:5432/govdb` |
| `API_BASE_URL` | URL base da API (local ou produção) | `https://gov-oportunidades-scraping.vercel.app` |
| `API_SECRET_KEY` | Chave secreta compartilhada para rotas internas (`X-API-Key`) | `gerar_chave_secreta_forte` |
| `SCRAPY_MAIL_HOST` | Host SMTP para envio de e-mails | `smtp.gmail.com` |
| `SCRAPY_MAIL_PORT` | Porta SMTP | `587` |
| `SCRAPY_MAIL_USER` | Usuário/E-mail remetente | `seu.email@gmail.com` |
| `SCRAPY_MAIL_PASS` | Senha de App SMTP | `SENHA_APP_16_DIGITOS` |
| `SCRAPY_MAIL_FROM` | E-mail exibido como remetente | `seu.email@gmail.com` |
| `OPENROUTER_API_KEY` | *(Opcional)* Chave de API da OpenRouter para resumo com IA | `sk-or-v1-...` |
| `OPENROUTER_MODEL` | *(Opcional)* Modelo de IA para resumos | `deepseek/deepseek-r1-0528:free` |
| `OPENROUTER_MAX_TEXT_LENGTH` | *(Opcional)* Limite de caracteres enviados ao LLM | `4000` |

---

## 🤖 Automação no GitHub Actions

O repositório inclui um workflow configurado (`.github/workflows/job.yml`) para executar o coletor diariamente às 10:00 (BRT):

1. Faça o fork ou clone do repositório.
2. No GitHub, vá em **Settings** > **Secrets and variables** > **Actions**.
3. Adicione os segredos:
   - `API_BASE_URL` (ex: `https://gov-oportunidades-scraping.vercel.app`)
   - `API_SECRET_KEY` (chave secreta para comunicação interna)
   - Credenciais SMTP e OpenRouter (se aplicável).
4. O robô coletará os editais, consultará a API na Vercel e notificará os assinantes cadastrados.

---

## 📧 Configuração de E-mail (Gmail SMTP)

Para usar uma conta Gmail como remetente:
1. Acesse sua [Conta Google > Segurança](https://myaccount.google.com/security).
2. Ative a **Verificação em 2 etapas**.
3. Em [Senhas de App](https://myaccount.google.com/apppasswords), crie uma nova senha de aplicativo (ex: nomeie como `GovOportunidades`).
4. Utilize a senha de 16 caracteres gerada na variável `SCRAPY_MAIL_PASS`.

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para obter mais informações.

