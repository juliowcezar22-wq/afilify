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
    ABERTAS=$(grep -c '^- \[ \] T' "$TAREFAS" 2>/dev/null || true)
    echo "════ ciclo · $ABERTAS tarefa(s) abertas no total ════"

    # Fecha TODA fase completa ainda não registrada — não só a corrente.
    # Marcar as tarefas já move a "fase atual" adiante, então olhar apenas
    # para ela deixaria a recém-concluída sem verificação nenhuma.
    REGISTRO="$RAIZ/.harness/fases-fechadas"
    COMPLETAS=$(python3 - "$TAREFAS" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
fase = None; fases = {}
for linha in s.splitlines():
    m = re.match(r"^## Fase (\d+) — ", linha)
    if m: fase = m.group(1); fases[fase] = [0, 0]
    if fase and re.match(r"^- \[[ x]\] ", linha):
        fases[fase][0 if linha.startswith("- [x]") else 1] += 1
print(" ".join(n for n, (feito, falta) in fases.items() if feito and not falta))
PY
)
    for N in $COMPLETAS; do
      if grep -q "^Fase $N fechada" "$REGISTRO" 2>/dev/null; then continue; fi
      echo "→ Fase $N completa e ainda não verificada"
      if "$RAIZ/scripts/harness/fase.sh" fechar "$N" >/dev/null 2>&1; then
        echo "✓ Fase $N fechada"
      else
        echo "✗ Fase $N NÃO fecha — a verificação completa falhou"
        "$RAIZ/scripts/harness/verify-nucleo.sh" 2>&1 | tail -12
        exit 1
      fi
    done

    FASE=$("$RAIZ/scripts/harness/fase.sh" atual)
    if [ -z "$FASE" ]; then
      echo "════ todas as fases concluídas ════"
      exit 0
    fi
    echo
    proxima_tarefa
    ;;
  *) echo "uso: ciclo.sh [ciclo|proxima]"; exit 1 ;;
esac
