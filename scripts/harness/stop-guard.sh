#!/usr/bin/env bash
# Stop hook — guardrail de conclusão (Parte 19 da spec).
# Bloqueia (exit 2) enquanto houver tasks abertas OU a última verificação
# completa não valer para o estado atual da árvore. Anti-loop: no máximo
# 2 bloqueios consecutivos (o 3º libera com aviso) — guardrail, não motor.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENTRADA=$(cat 2>/dev/null || true)   # JSON do hook (stop_hook_active etc.)

# grep -c imprime 0 E sai com 1 quando não há match — capturar só o stdout
ABERTAS=$(grep -c '^- \[ \] T' "$RAIZ/specs/001-afilify-saas-core/tasks.md" 2>/dev/null || true)
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
# que muda a cada atualização de PROGRESS); honra stop_hook_active.
# O teto é alto de propósito — o trabalho é longo e o dono pediu que ele não
# pare a cada fase — mas existe: guardrail, não motor perpétuo.
CONTA=$(cat "$RAIZ/.harness/stop-blocks" 2>/dev/null || echo 0)
case "$CONTA" in *[!0-9]*) CONTA=0 ;; esac
ATIVO=0
case "$ENTRADA" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) ATIVO=1 ;; esac
if [ "$CONTA" -ge 8 ] || { [ "$ATIVO" -eq 1 ] && [ "$CONTA" -ge 6 ]; }; then
  echo "AVISO stop-guard: liberando após $CONTA bloqueios — revise manualmente ($ABERTAS tasks abertas)." >&2
  rm -f "$RAIZ/.harness/stop-blocks" 2>/dev/null
  exit 0
fi
mkdir -p "$RAIZ/.harness"
echo "$((CONTA + 1))" > "$RAIZ/.harness/stop-blocks"

{
  echo "Trabalho do núcleo SaaS ainda não concluído:"
  if [ "$ABERTAS" -gt 0 ]; then
    echo "· $ABERTAS tarefa(s) abertas em specs/001-afilify-saas-core/tasks.md:"
    grep -n '^- \[ \] T' "$RAIZ/specs/001-afilify-saas-core/tasks.md" | head -8
  fi
  if [ "$MARCADOR" != "$ASSINATURA" ]; then
    echo "· verificação completa não corresponde ao estado atual — rode scripts/harness/verify-nucleo.sh"
  fi
  echo
  "$RAIZ/scripts/harness/ciclo.sh" proxima 2>/dev/null
  echo
  echo "Ciclo: implementar → validar com dado real → registrar prova → marcar → próxima."
  echo "Ao esvaziar a fase: scripts/harness/fase.sh fechar N (roda a verificação completa)."
} >&2
exit 2
