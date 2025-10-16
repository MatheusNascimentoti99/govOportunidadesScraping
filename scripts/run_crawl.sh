#!/usr/bin/env bash
set -euo pipefail

# Config
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/mp_env"
LOG_DIR="$PROJECT_DIR/logs/cron"
OUT_DIR="$PROJECT_DIR/out"
LOCK_FILE="$PROJECT_DIR/.crawl.lock"
SPIDER_NAME="edital"
# Ajuste se quiser saída exportada
FEED_URI="$OUT_DIR/saida_$(date -u +%Y%m%dT%H%M%SZ).json"

mkdir -p "$LOG_DIR" "$OUT_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[$(date -Is)] Outro processo está em execução; saindo." >> "$LOG_DIR/crawl.log"
  exit 0
fi


# Preferir venv local se existir
if [ -x "$VENV_DIR/bin/scrapy" ]; then
  SCRAPY_BIN="$VENV_DIR/bin/scrapy"
else
  SCRAPY_BIN="scrapy"
fi

# Executa o crawl
"$SCRAPY_BIN" crawl "$SPIDER_NAME" \
  -s LOG_LEVEL=INFO \
  -s EDITAIS_DB_PATH="$PROJECT_DIR/editais.db" \
  -O "$FEED_URI" \
  >> "$LOG_DIR/crawl.log" 2>&1
