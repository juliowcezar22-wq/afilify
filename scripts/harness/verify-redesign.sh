#!/usr/bin/env bash
# FULL CHECK — verificação completa do redesign (fim de milestone).
#   lint + typecheck (fast-check) → build de produção → linguagem →
#   integridade do motor (allowlist) → tasks abertas.
#
# Sucesso grava .harness/last-verify-ok com a assinatura da árvore — o
# Stop hook usa isso para saber se a verificação vale para o estado atual.
#
# Flags:
#   --sem-build   pula o build (uso interativo rápido; NÃO grava marcador)
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PAINEL="$RAIZ/painel"
SEM_BUILD=0
[ "${1:-}" = "--sem-build" ] && SEM_BUILD=1

FALHAS=()

echo "════ verify-redesign ════"

# 1. fast checks
if ! "$RAIZ/scripts/harness/fast-check.sh"; then
  FALHAS+=("lint/typecheck")
fi

# 2. build de produção
if [ "$SEM_BUILD" -eq 0 ]; then
  echo "→ build de produção"
  if ! (cd "$PAINEL" && pnpm build >/tmp/afilify-build.log 2>&1); then
    echo "✗ build falhou:"
    tail -40 /tmp/afilify-build.log
    FALHAS+=("build")
  else
    echo "✓ build ok"
  fi
fi

# 3. linguagem de produto
if ! "$RAIZ/scripts/harness/check-linguagem.sh"; then
  FALHAS+=("linguagem")
fi

# 4. motor intocado (D1) — ALLOWLIST: qualquer arquivo fora das áreas do
# redesign é violação (um diretório novo do motor fica protegido por padrão)
FORA=$(cd "$RAIZ" && git diff --name-only main | grep -vE \
  '^(painel/|docs/|scripts/harness/|\.claude/|CLAUDE\.md|README\.md|TASKS_AFILIFY_REDESIGN\.md|PROGRESS_AFILIFY_REDESIGN\.md|\.gitignore)' || true)
if [ -n "$FORA" ]; then
  echo "✗ arquivos fora do escopo do redesign alterados (D1):"
  echo "$FORA"
  FALHAS+=("motor-intocado")
else
  echo "✓ motor intocado (diff vs main restrito a painel/docs/harness)"
fi

# 5. tasks abertas (grep -c imprime 0 E sai 1 sem match — capturar stdout)
ABERTAS=$(grep -c '^- \[ \]' "$RAIZ/TASKS_AFILIFY_REDESIGN.md" 2>/dev/null || true)
ABERTAS=${ABERTAS:-0}
echo "· tasks abertas: $ABERTAS"

echo "═════════════════════════"
if [ "${#FALHAS[@]}" -gt 0 ]; then
  echo "RESULTADO: FALHOU → ${FALHAS[*]}"
  exit 1
fi

if [ "$SEM_BUILD" -eq 0 ]; then
  mkdir -p "$RAIZ/.harness"
  ASSINATURA=$(cd "$RAIZ" && {
    git rev-parse HEAD
    git status --porcelain
    git diff HEAD
    git ls-files --others --exclude-standard -z | xargs -0 shasum 2>/dev/null
  } | shasum | cut -d' ' -f1)
  echo "$ASSINATURA" > "$RAIZ/.harness/last-verify-ok"
fi

if [ "$ABERTAS" -gt 0 ]; then
  echo "RESULTADO: checks OK · $ABERTAS task(s) ainda abertas em TASKS_AFILIFY_REDESIGN.md"
  exit 0   # checks passam; conclusão do PROJETO é decidida pelo Stop hook
fi
echo "RESULTADO: OK — checks passam e não há tasks abertas"
