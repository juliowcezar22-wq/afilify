#!/usr/bin/env bash
# CICLO — o motor do trabalho contínuo.
#
# Responde, em uma chamada: onde estou, o que falta, e posso avançar?
# Quando a fase corrente não tem mais tarefa aberta, roda a verificação
# completa e a fecha sozinho — e já aponta a próxima.
#
#   ciclo.sh          situação + tenta fechar a fase corrente se puder
#   ciclo.sh proxima  só imprime a próxima tarefa a fazer
#
# O que ele NÃO faz: escrever código. O avanço depende de trabalho real
# entrando; o ciclo só garante que nada seja dado por concluído sem prova.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAREFAS="$RAIZ/specs/001-afilify-saas-core/tasks.md"

proxima_tarefa() {
  python3 - "$TAREFAS" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
fase = None
for linha in s.splitlines():
    m = re.match(r"^## (Fase \d+) — (.+?)(?: \(|$)", linha)
    if m: fase, titulo = m.group(1), m.group(2)
    if fase and linha.startswith("- [ ] T"):
        texto = re.sub(r"^- \[ \] (\[P\] )?", "", linha)
        print(f"{fase} ({titulo})\n  próxima: {texto}")
        break
else:
    print("nada aberto — todas as fases concluídas")
PY
}

case "${1:-ciclo}" in
  proxima) proxima_tarefa ;;
  ciclo)
    FASE=$("$RAIZ/scripts/harness/fase.sh" atual)
    if [ -z "$FASE" ]; then
      echo "════ todas as fases concluídas ════"
      "$RAIZ/scripts/harness/verify-nucleo.sh"
      exit $?
    fi
    N=$(echo "$FASE" | grep -oE '[0-9]+')
    ABERTAS=$(grep -c '^- \[ \] T' "$TAREFAS" 2>/dev/null || true)
    echo "════ ciclo · $FASE · $ABERTAS tarefa(s) abertas no total ════"
    if "$RAIZ/scripts/harness/fase.sh" fechar "$N" >/dev/null 2>&1; then
      echo "✓ $FASE fechada — avançando"
      echo
      proxima_tarefa
    else
      echo "· $FASE ainda aberta"
      echo
      proxima_tarefa
    fi
    ;;
  *) echo "uso: ciclo.sh [ciclo|proxima]"; exit 1 ;;
esac
