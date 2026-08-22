#!/usr/bin/env bash
# FAST CHECK — roda durante as tarefas (lint + typecheck). Sem build.
# Uso: scripts/harness/fast-check.sh   (de qualquer cwd dentro do repo)
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PAINEL="$RAIZ/painel"
FALHAS=0

echo "── fast-check · painel ──"

if [ ! -d "$PAINEL/node_modules" ]; then
  echo "✗ node_modules ausente — rode: (cd painel && pnpm install)"
  exit 1
fi

echo "→ lint"
if ! (cd "$PAINEL" && pnpm lint >/tmp/afilify-lint.log 2>&1); then
  echo "✗ lint falhou:"
  tail -40 /tmp/afilify-lint.log
  FALHAS=1
else
  echo "✓ lint ok"
fi

echo "→ typecheck (next typegen + tsc --noEmit)"
if ! (cd "$PAINEL" && npx next typegen >/tmp/afilify-typegen.log 2>&1 \
      && npx tsc --noEmit >/tmp/afilify-tsc.log 2>&1); then
  echo "✗ typecheck falhou:"
  tail -20 /tmp/afilify-typegen.log 2>/dev/null
  tail -40 /tmp/afilify-tsc.log 2>/dev/null
  FALHAS=1
else
  echo "✓ typecheck ok"
fi

if [ "$FALHAS" -ne 0 ]; then
  echo "── fast-check: FALHOU ──"
  exit 1
fi
echo "── fast-check: OK ──"
