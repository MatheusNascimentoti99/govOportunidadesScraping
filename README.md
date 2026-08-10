# govOportunidadesScraping

Coletor (Scrapy) para identificar oportunidades governamentais (editais) no portal do SIGEPE, extrair links e texto de PDFs, filtrar por palavras‑chave e notificar por e‑mail. Possui deduplicação entre execuções (SQLite) e agendamento via cron.

![alt text](docs/usage.png)

## Visão geral
- Spider `edital` acessa a página inicial, segue para páginas de edital e baixa o PDF associado.
- O texto do PDF é extraído (pdfplumber) e então filtrado por palavras definidas em `.env` (KEY_WORDS).
- Itens que casarem são persistidos em SQLite e enviados por e‑mail (MailSender do Scrapy).
- Um controle de “vistos” evita reprocessar PDFs já lidos entre execuções.

## Recursos
- Scrapy + pdfplumber para extrair texto de PDFs.
- Filtro por palavras‑chave configurável via `.env`.
- Deduplicação de notificação (não envia novamente para o mesmo URL).
- Persistência em SQLite:
  - `matching_editais` (itens que casaram com palavras-chave)
- Agendamento via cron (script pronto com lock e logs).

## Estrutura do projeto
```
. 
├─ govoportunidades/
│  ├─ spiders/
│  │  └─ edital.py          # Spider principal
│  ├─ items.py               # Itens: EditalExtractor (url, text)
│  ├─ pipelines.py           # Pipelines: dedupe, SQLite, notificação
│  └─ settings.py            # Settings (dotenv, e-mail, keywords, pipelines)
├─ requirements.txt          # Dependências
├─ dockerfile                # Build e execução do spider no container
├─ scripts/
│  └─ run_crawl.sh           # Script para cron (lock, logs, export)
├─ CRON.md                   # Guia de agendamento no cron
└─ README.md                 # Este arquivo
```

## Requisitos
- Python 3.10+
- Linux/macOS (Windows via WSL/Docker)

## Como começar (Instalação local)

1. **Clone ou faça um fork do repositório:**
```bash
git clone https://github.com/SEU_USUARIO/govOportunidadesScraping.git
cd govOportunidadesScraping
```

2. **Crie e ative um ambiente virtual:**
```bash
python -m venv .venv

# No Linux/macOS
source .venv/bin/activate

# No Windows
.venv\Scripts\activate
```

3. **Instale as dependências:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Configuração (.env):**
Copie o arquivo de exemplo para criar o seu arquivo `.env`:
```bash
# No Linux/macOS
cp .env.example .env

# No Windows
copy .env.example .env
```

Abra o arquivo `.env` recém-criado e preencha-o com suas informações (como palavras-chave, credenciais de e-mail e API do OpenRouter, se for usar sumarização). O arquivo `.env.example` já possui comentários explicando cada variável e dados de exemplo.

## Executando
- Execução simples (exporta JSON para `saida.json`):
```fish
scrapy crawl edital -O saida.json -L INFO
```

Observações importantes:
- Por padrão `ROBOTSTXT_OBEY = True`. Se a origem bloquear o scraping via robots.txt, o spider respeitará.
- O `NotificationDedupPipeline` descarta itens cujo URL já está em `matching_editais` (evita reenvio de e-mail).

## GitHub Actions (Execução automatizada e gratuita)

O projeto já inclui um workflow (`.github/workflows/job.yml`) para rodar o coletor de forma automática no GitHub Actions.

**Passo a passo para ativar:**
1. Faça o **fork** deste repositório para a sua conta do GitHub (caso ainda não o tenha feito).
2. Acesse a aba **Settings** (Configurações) do seu repositório.
3. No menu lateral, acesse **Secrets and variables** > **Actions**.
4. Clique no botão **New repository secret** e cadastre as credenciais do seu projeto (as mesmas do `.env` local):
   - `SCRAPY_KEY_WORDS`
   - `SCRAPY_MAIL_TO`
   - `SCRAPY_MAIL_HOST`
   - `SCRAPY_MAIL_PORT`
   - `SCRAPY_MAIL_USER`
   - `SCRAPY_MAIL_PASS`
   - `SCRAPY_MAIL_FROM`
   - *(Opcional - caso use sumarização)*: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` e `OPENROUTER_MAX_TEXT_LENGTH`.
5. Acesse a aba **Actions** no topo do repositório e confirme a ativação dos fluxos, clicando no botão verde se for solicitado.
6. **Agendamento padrão:** O scraper roda todos os dias às 10:00 da manhã (13:00 UTC).
7. **Execução manual:** Para testar, vá na aba **Actions**, selecione `Scrape Gov Oportunidades`, clique em **Run workflow** e rode.

> **Nota:** O banco de dados SQLite (`editais.db`) será cacheado entre as execuções (evitando envios repetidos). Na página de resultados de cada execução da Action, você poderá baixar o `output.json` e o `editais.db` em **Artifacts**.

## Cron (Execução local)
Há um guia dedicado em `CRON.md` com exemplos. O script `scripts/run_crawl.sh` já implementa:
- Lock (`.crawl.lock`) para evitar concorrência
- Logs em `logs/cron/crawl.log`
- Export para `out/`

Exemplo (a cada 2h):
```cron
0 */2 * * * /bin/bash -lc 'cd /caminho/para/o/projeto && chmod +x scripts/run_crawl.sh && ./scripts/run_crawl.sh'
```

## Banco de dados (SQLite)
- `matching_editais` (no pipeline): armazena URLs/texto/matched_keywords de itens que casaram.
- Caminho configurável por `EDITAIS_DB_PATH` (padrão: `./editais.db`).

## Tutorial: e-mail com Gmail (SMTP)
O Gmail não aceita mais “aplicativos menos seguros”. Para enviar e-mails via SMTP você precisa usar “Senha de app” com 2FA.

Passos:
1) Ative a verificação em duas etapas (2FA) na sua Conta Google:
   - Acesse https://myaccount.google.com/security
   - Em “Como você faz login no Google”, ative “Verificação em duas etapas”.
2) Crie uma Senha de app:
   - Ainda em https://myaccount.google.com/security, em “Como você faz login no Google”, abra “Senhas de app”.
   - Selecione “Aplicativo: Mail” e “Dispositivo: Outro (nomeie, ex.: Scrapy)”.
   - O Google mostrará uma senha de 16 caracteres.
3) Configure o `.env` do projeto:
   - SCRAPY_MAIL_HOST="smtp.gmail.com"
   - SCRAPY_MAIL_PORT="587"
   - SCRAPY_MAIL_USER="seu.email@gmail.com"
   - SCRAPY_MAIL_PASS="SENHA_DE_APP_16_CARACTERES"
   - SCRAPY_MAIL_FROM="seu.email@gmail.com"
   - SCRAPY_MAIL_TO="destino1@exemplo.com,destino2@exemplo.com"
4) TLS/SSL:
   - O projeto usa TLS (porta 587) por padrão nas settings.

Testando envio:
- Rode o spider com `KEY_WORDS` que com certeza casem com seu conteúdo para forçar um e-mail, ou temporariamente ajuste `KEY_WORDS` e/ou um item de teste.
- Verifique `logs/cron/crawl.log` e a caixa de saída do Gmail.

Erros comuns:
- “Username and Password not accepted”: confirme 2FA e Senha de app; não use sua senha normal do Gmail.
- “Connection refused/timeout”: verifique firewall/rede; portas 587 (TLS) liberadas.
- “Daily user sending quota exceeded”: o Gmail impõe limites de envio.

## Dicas e troubleshooting
- pdfplumber não instalado: `pip install pdfplumber` (já consta no requirements.txt).
- Verbosidade de logs: use `-L DEBUG` para maior detalhamento.

## Desenvolvimento
- Formato dos itens (ex.: `EditalExtractor`):
  - `url`: URL da página principal do edital
  - `text`: texto do PDF extraído
- Pipelines e ordem (em `settings.py`):
  - `NotificationDedupPipeline` (150): descarta itens já notificados
  - `SQLitePipeline` (200): persiste matches em `matching_editais`
  - `NotificationPipeline` (300): calcula matches e envia e-mail
