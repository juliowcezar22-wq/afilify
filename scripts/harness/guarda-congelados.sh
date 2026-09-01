#!/usr/bin/env bash
# GUARDA DOS CONGELADOS — nesta rodada o motor É alterado (é a essência do
# trabalho), então a proteção deixa de ser "não toque no motor" e passa a ser
# cirúrgica: o Clonador e o que a workstream paralela edita ficam intocados.
#
# Base: constitution (princípio V) e D26/D34.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ" || exit 1

# Arquivos que esta rodada NÃO pode alterar, em nenhuma hipótese.
CONGELADOS=(
  "mercadolivre/clonador.py"
  "db/0007_clone_literal.sql"
  "db/0008_webhook.sql"
)

FALHAS=0
BASE="$(git merge-base HEAD main 2>/dev/null || echo main)"

for arq in "${CONGELADOS[@]}"; do
  if ! git diff --quiet "$BASE" -- "$arq" 2>/dev/null; then
    echo "✗ arquivo congelado alterado: $arq"
    echo "   (Clonador é dependência congelada — reverta com: git checkout $BASE -- $arq)"
    FALHAS=1
  fi
done

# A tabela rival_mensagens é do monitoramento: nenhuma migração nova pode mexer nela.
NOVAS_MIGR=$(git diff --name-only "$BASE" -- 'db/*.sql' | grep -vE 'db/000[1-8]_' || true)
if [ -n "$NOVAS_MIGR" ]; then
  if grep -lE '\brival_mensagens\b' $NOVAS_MIGR 2>/dev/null | grep -q .; then
    echo "✗ migração nova mexe em rival_mensagens (tabela do monitoramento congelado):"
    grep -lE '\brival_mensagens\b' $NOVAS_MIGR
    FALHAS=1
  fi
fi

if [ "$FALHAS" -ne 0 ]; then
  echo "── guarda-congelados: FALHOU ──"
  exit 1
fi
echo "✓ guarda-congelados ok (Clonador e monitoramento intocados)"
