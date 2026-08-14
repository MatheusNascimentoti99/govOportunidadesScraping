#!/usr/bin/env bash
# scripts/dev_down.sh
# Para e remove todos os contêineres do ambiente local.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
step() { echo -e "${CYAN}▶  $*${NC}"; }
ok()   { echo -e "${GREEN}✓  $*${NC}"; }

step "Parando serviços..."
docker compose down

ok "Todos os contêineres parados."
echo ""
echo "  Os dados do PostgreSQL ficam preservados no volume 'postgres_data'."
echo "  Para remover também os dados: docker compose down -v"
