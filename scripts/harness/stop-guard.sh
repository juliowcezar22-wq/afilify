#!/usr/bin/env bash
# Stop hook — guardrail de conclusão (Parte 19 da spec).
# Bloqueia (exit 2) enquanto houver tasks abertas OU a última verificação
# completa não valer para o estado atual da árvore. Anti-loop: se já
# bloqueou 2x seguidas sem NENHUMA mudança na árvore, libera com aviso —
# guardrail, não motor (a proteção do Claude Code contra bloqueios
# consecutivos continua valendo).
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENTRADA=$(cat 2>/dev/null || true)   # JSON do hook (stop_hook_active etc.)

ABERTAS=$(grep -c '^- \[ \]' "$RAIZ/TASKS_AFILIFY_REDESIGN.md" 2>/dev/null || echo 0)

ASSINATURA=$(cd "$RAIZ" && { git rev-parse HEAD; git status --porcelain; } | shasum | cut -d' ' -f1)
MARCADOR=$(cat "$RAIZ/.harness/last-verify-ok" 2>/dev/null || echo "nunca")

if [ "$ABERTAS" -eq 0 ] && [ "$MARCADOR" = "$ASSINATURA" ]; then
  rm -f "$RAIZ/.harness/stop-blocks" 2>/dev/null
  exit 0   # tudo verificado — pode encerrar
fi

# anti-loop: 2 bloqueios seguidos com árvore idêntica → libera com aviso
ULTIMO=$(cat "$RAIZ/.harness/stop-blocks" 2>/dev/null || echo "")
CONTA=0
if [ "${ULTIMO%%:*}" = "$ASSINATURA" ]; then CONTA="${ULTIMO##*:}"; fi
if [ "$CONTA" -ge 2 ]; then
  echo "AVISO stop-guard: liberando após $CONTA bloqueios sem mudança na árvore — revise manualmente ($ABERTAS tasks abertas)." >&2
  rm -f "$RAIZ/.harness/stop-blocks" 2>/dev/null
  exit 0
fi
mkdir -p "$RAIZ/.harness"
echo "$ASSINATURA:$((CONTA + 1))" > "$RAIZ/.harness/stop-blocks"

{
  echo "Trabalho do redesign ainda não concluído:"
  if [ "$ABERTAS" -gt 0 ]; then
    echo "· $ABERTAS task(s) abertas em TASKS_AFILIFY_REDESIGN.md:"
    grep -n '^- \[ \]' "$RAIZ/TASKS_AFILIFY_REDESIGN.md" | head -8
  fi
  if [ "$MARCADOR" != "$ASSINATURA" ]; then
    echo "· verificação completa não corresponde ao estado atual — rode scripts/harness/verify-redesign.sh"
  fi
  echo "Continue o ciclo: implementar → validar → revisar → marcar task → próxima."
} >&2
exit 2
