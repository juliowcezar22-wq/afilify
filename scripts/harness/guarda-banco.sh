#!/usr/bin/env bash
# GUARDA DO BANCO — D35: a worktree NUNCA aponta para o banco da operação.
#
# Produção roda em VPS/EasyPanel desde 22/08/2026 (serviços worker, painel e
# db). Este script recusa qualquer execução cujo DATABASE_URL/SQLITE_PATH
# aponte para lá, e é chamado antes de subir motor ou painel na worktree.
#
# Uso:  scripts/harness/guarda-banco.sh   (lê o ambiente atual)
set -uo pipefail

PROIBIDOS_URL=(
  "afilify-db"        # nome do banco em produção
  "julio_db"          # host interno do EasyPanel
  "177.39.18.206"     # IP da VPS
  "easypanel.host"
)

FALHAS=0
ALVO="${DATABASE_URL:-}"

if [ -n "$ALVO" ]; then
  for p in "${PROIBIDOS_URL[@]}"; do
    case "$ALVO" in
      *"$p"*)
        echo "✗ DATABASE_URL aponta para a operação em produção (contém \"$p\")."
        FALHAS=1
        ;;
    esac
  done
fi

# SQLite: o banco congelado da virada também não é alvo de escrita da worktree.
CAMINHO="${SQLITE_PATH:-}"
if [ -n "$CAMINHO" ]; then
  case "$(cd "$(dirname "$CAMINHO")" 2>/dev/null && pwd)/$(basename "$CAMINHO")" in
    */GRUPO-PROMOCOES/dados/*)
      echo "✗ SQLITE_PATH aponta para os dados do projeto principal — use um banco próprio."
      FALHAS=1
      ;;
  esac
fi

if [ -z "$ALVO" ] && [ -z "$CAMINHO" ]; then
  echo "! nenhum banco configurado (DATABASE_URL/SQLITE_PATH vazios)"
  exit 0
fi

if [ "$FALHAS" -ne 0 ]; then
  echo "── guarda-banco: BLOQUEADO — configure o banco de validação (quickstart.md) ──"
  exit 1
fi
echo "✓ guarda-banco ok (banco de validação, fora da operação)"
