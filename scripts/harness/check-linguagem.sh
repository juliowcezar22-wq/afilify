#!/usr/bin/env bash
# Regressão de linguagem: termos internos/técnicos não podem aparecer em
# texto voltado ao usuário nos componentes do painel.
#
# Falso-positivo legítimo (código, ou copy deliberada em "Detalhes
# técnicos")? Marque a LINHA com o comentário `harness-ok` que ela é
# ignorada — a exceção fica visível no próprio diff.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ALVOS=("$RAIZ/painel/app" "$RAIZ/painel/components")

# Termos proibidos na experiência comum (Parte 28 da spec)
TERMOS=(
  "worker" "Worker"
  "[Uu]azapi" "UAZAPI"
  "JID"
  "LOG_PATH"
  "Postgres" "postgres" "SQLite" "sqlite"
  "perfumes-ml" "casa-ml-shopee" "perfumes_ml"
  "fura a fila"
  "deploy" "restart"
  "EasyPanel"
  "mlcookie"
  "hora decimal"
)

FALHAS=0
for termo in "${TERMOS[@]}"; do
  # exclusões: linhas de código puro (import/env/tipos) e linhas marcadas
  HITS=$(grep -rnE "$termo" "${ALVOS[@]}" --include='*.tsx' --include='*.ts' 2>/dev/null \
    | grep -v "harness-ok" \
    | grep -v "process\.env" \
    | grep -vE "^\S+:[0-9]+:\s*(//|/\*|\*)" \
    | grep -v "import " || true)
  if [ -n "$HITS" ]; then
    echo "✗ termo proibido \"$termo\" em texto do painel:"
    echo "$HITS" | head -10
    FALHAS=1
  fi
done

if [ "$FALHAS" -ne 0 ]; then
  echo "── check-linguagem: FALHOU (traduza para linguagem de produto ou marque harness-ok se for código/Detalhes técnicos) ──"
  exit 1
fi
echo "✓ check-linguagem ok (nenhum termo interno exposto)"
