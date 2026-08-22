#!/usr/bin/env bash
# Stop hook — guardrail de conclusão (Parte 19 da spec).
# Bloqueia (exit 2) enquanto houver tasks abertas OU a última verificação
# completa não valer para o estado atual da árvore. Anti-loop: no máximo
# 2 bloqueios consecutivos (o 3º libera com aviso) — guardrail, não motor.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENTRADA=$(cat 2>/dev/null || true)   # JSON do hook (stop_hook_active etc.)

# grep -c imprime 0 E sai com 1 quando não há match — capturar só o stdout
ABERTAS=$(grep -c '^- \[ \]' "$RAIZ/TASKS_AFILIFY_REDESIGN.md" 2>/dev/null || true)
ABERTAS=${ABERTAS:-0}

# assinatura sensível a CONTEÚDO: HEAD + diff das rastreadas + hash das
# não-rastreadas (status --porcelain sozinho ignora edições em arquivo já sujo)
assinatura_arvore() {
  cd "$RAIZ" || return 1
  {
    git rev-parse HEAD
    git status --porcelain
    git diff HEAD
    git ls-files --others --exclude-standard -z | xargs -0 shasum 2>/dev/null
  } | shasum | cut -d' ' -f1
}
ASSINATURA=$(assinatura_arvore)
MARCADOR=$(cat "$RAIZ/.harness/last-verify-ok" 2>/dev/null || echo "nunca")

if [ "$ABERTAS" -eq 0 ] && [ "$MARCADOR" = "$ASSINATURA" ]; then
  rm -f "$RAIZ/.harness/stop-blocks" 2>/dev/null
  exit 0   # tudo verificado — pode encerrar
fi

# anti-loop: contador de bloqueios consecutivos (independente da árvore,
# que muda a cada atualização de PROGRESS); honra stop_hook_active
CONTA=$(cat "$RAIZ/.harness/stop-blocks" 2>/dev/null || echo 0)
case "$CONTA" in *[!0-9]*) CONTA=0 ;; esac
ATIVO=0
case "$ENTRADA" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) ATIVO=1 ;; esac
if [ "$CONTA" -ge 2 ] || { [ "$ATIVO" -eq 1 ] && [ "$CONTA" -ge 1 ]; }; then
  echo "AVISO stop-guard: liberando após $CONTA bloqueios — revise manualmente ($ABERTAS tasks abertas)." >&2
  rm -f "$RAIZ/.harness/stop-blocks" 2>/dev/null
  exit 0
fi
mkdir -p "$RAIZ/.harness"
echo "$((CONTA + 1))" > "$RAIZ/.harness/stop-blocks"

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
