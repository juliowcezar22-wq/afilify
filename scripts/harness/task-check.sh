#!/usr/bin/env bash
# TaskCompleted hook — antes de marcar tarefa como concluída, roda o FAST
# CHECK (lint + typecheck). Falhou → bloqueia a conclusão (exit 2) com o
# motivo no stderr. O FULL CHECK (build etc.) roda no fim de cada
# milestone via verify-redesign.sh — estratégia em camadas (Parte 19).
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cat >/dev/null 2>&1 || true   # consome o JSON do hook

if ! "$RAIZ/scripts/harness/fast-check.sh" >&2; then
  echo "fast-check falhou — corrija lint/typecheck antes de concluir a tarefa." >&2
  exit 2
fi
exit 0
