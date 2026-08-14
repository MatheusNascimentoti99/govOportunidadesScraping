#!/usr/bin/env bash
# scripts/dev_up.sh
# Sobe o ambiente local completo (PostgreSQL + API FastAPI) via Docker.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# ── Cores ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step()  { echo -e "${CYAN}▶  $*${NC}"; }
ok()    { echo -e "${GREEN}✓  $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠  $*${NC}"; }
fail()  { echo -e "${RED}✗  $*${NC}"; exit 1; }

# ── 1. Pré-requisitos ──────────────────────────────────────────────
step "Verificando pré-requisitos..."
command -v docker >/dev/null 2>&1 || fail "Docker não encontrado. Instale em https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1       || fail "Docker daemon não está rodando. Inicie o Docker Desktop e tente novamente."
ok "Docker OK"

# ── 2. Criar .env a partir do exemplo local ────────────────────────
if [ ! -f "$PROJECT_DIR/.env" ]; then
  step "Criando .env a partir de .env.local.example..."
  cp "$PROJECT_DIR/.env.local.example" "$PROJECT_DIR/.env"
  warn ".env criado. Edite-o se precisar ajustar SMTP ou OpenRouter antes de continuar."
else
  ok ".env já existe"
fi

# ── 3. Build + up ─────────────────────────────────────────────────
step "Construindo imagens e subindo serviços..."
docker compose up --build -d

# ── 4. Aguardar API ficar pronta ───────────────────────────────────
step "Aguardando API estar pronta em http://localhost:8000..."
MAX=30; COUNT=0
until curl -sf http://localhost:8000/api/health >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  [ "$COUNT" -ge "$MAX" ] && fail "API não respondeu após ${MAX}s. Execute: docker compose logs api"
  printf '.'
  sleep 1
done
echo ""
ok "API pronta"

# ── Resumo ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN} Ambiente local no ar!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo "  API  → http://localhost:8000"
echo "  Docs → http://localhost:8000/docs"
echo "  DB   → postgresql://govuser:govpassword@localhost:5432/govdb"
echo ""
echo -e "${YELLOW}  Para parar:${NC}  bash scripts/dev_down.sh"
echo -e "${YELLOW}  Para crawl:${NC}  bash scripts/run_crawl.sh"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
