# Execução via cron

Este projeto inclui um script para executar o spider `edital` de forma segura em cron, com lock e logs.

## Script
- Arquivo: `scripts/run_crawl.sh`
- Faz:
  - Lock para evitar concorrência (`.crawl.lock`)
  - Carrega `.env`
  - Usa `mp_env/` se existir, senão `scrapy` global
  - Salva export em `out/saida_YYYYMMDDTHHMMSSZ.json`
  - Log em `logs/cron/crawl.log`

## Cron (exemplos)
Edite o crontab do usuário:

```
crontab -e
```

Execute a cada 2 horas (UTC) e com timeout de 30min via `systemd-run` opcional:

```
0 */2 * * * /bin/bash -lc 'cd caminho/para/projeto && chmod +x scripts/run_crawl.sh && ./scripts/run_crawl.sh'
```

Executar diariamente às 08:05 (hora local):
```
5 8 * * * /bin/bash -lc 'cd caminho/para/projeto && chmod +x scripts/run_crawl.sh && ./scripts/run_crawl.sh'
```

> Dica: use caminhos absolutos e `bash -lc` para garantir variáveis de ambiente e PATH corretos.

## Variáveis de ambiente
- Configure `.env` na raiz com, por exemplo:
```
SCRAPY_KEY_WORDS="engenharia,civil,TI,contrato"
SCRAPY_MAIL_TO="alguem@exemplo.com"
SCRAPY_MAIL_HOST="smtp.seu-provedor.com"
SCRAPY_MAIL_PORT="587"
SCRAPY_MAIL_USER="usuario@seu-provedor.com"
SCRAPY_MAIL_PASS="senha"
SCRAPY_MAIL_FROM="usuario@seu-provedor.com"
```
