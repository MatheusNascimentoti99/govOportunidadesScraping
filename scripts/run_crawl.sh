#!/usr/bin/env bash
# scripts/run_crawl.sh
# Executa o spider Scrapy localmente apontando para a API rodando via Docker.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/mp_env"
LOG_DIR="$PROJECT_DIR/logs/cron"
OUT_DIR="$PROJECT_DIR/out"
LOCK_FILE="$PROJECT_DIR/.crawl.lock"
SPIDER_NAME="edital"
FEED_URI="$OUT_DIR/saida_$(date -u +%Y%m%dT%H%M%SZ).json"

mkdir -p "$LOG_DIR" "$OUT_DIR"

# Previne execuções simultâneas
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[$(date -Is)] Outro processo está em execução; saindo." >> "$LOG_DIR/crawl.log"
  exit 0
fi

# ── Verificar se a API está no ar ─────────────────────────────────
if ! curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
  echo "[$(date -Is)] API não está respondendo em http://localhost:8000. Execute: bash scripts/dev_up.sh" \
    | tee -a "$LOG_DIR/crawl.log"
  exit 1
fi

# ── Selecionar binário do Scrapy ──────────────────────────────────
if [ -x "$VENV_DIR/bin/scrapy" ]; then
  SCRAPY_BIN="$VENV_DIR/bin/scrapy"
else
  SCRAPY_BIN="scrapy"
fi

echo "[$(date -Is)] Iniciando crawl → $FEED_URI" >> "$LOG_DIR/crawl.log"

# ── Executar o crawl ──────────────────────────────────────────────
"$SCRAPY_BIN" crawl "$SPIDER_NAME" \
  -s LOG_LEVEL=INFO \
  -O "$FEED_URI" \
  >> "$LOG_DIR/crawl.log" 2>&1

echo "[$(date -Is)] Crawl concluído." >> "$LOG_DIR/crawl.log"
