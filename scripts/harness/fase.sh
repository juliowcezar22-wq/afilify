#!/usr/bin/env bash
# GATE DE FASE — uma fase só fecha quando não sobra tarefa nela E todos os
# gates passam. Enquanto isso, o trabalho continua na fase corrente.
#
#   fase.sh              situação de todas as fases
#   fase.sh atual        a primeira fase com tarefa aberta
#   fase.sh fechar N     tenta fechar a fase N (roda a verificação completa)
#
# Fechar grava .harness/fases-fechadas — é o registro de que aquela fase
# passou por verificação completa, não só por marcação de tarefa.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAREFAS="$RAIZ/specs/001-afilify-saas-core/tasks.md"
REGISTRO="$RAIZ/.harness/fases-fechadas"

situacao() {
  python3 - "$TAREFAS" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
fase = None; fases = {}
for linha in s.splitlines():
    m = re.match(r"^## (Fase \d+) — (.+?)(?: \(|$)", linha)
    if m:
        fase = m.group(1); fases[fase] = [m.group(2), 0, 0, []]
    if fase and re.match(r"^- \[[ x]\] ", linha):
        feito = linha.startswith("- [x]")
        fases[fase][2 if not feito else 1] += 1
        if not feito:
            fases[fase][3].append(re.search(r"(T\d+)", linha).group(1))
for nome, (titulo, feito, falta, abertas) in fases.items():
    marca = "✓" if falta == 0 and feito else "·"
    extra = f"  → {', '.join(abertas[:6])}" + ("…" if len(abertas) > 6 else "") if abertas else ""
    print(f"{marca} {nome}: {titulo[:44]:46} {feito:>3} feito  {falta:>3} falta{extra}")
PY
}

atual() {
  python3 - "$TAREFAS" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
fase = None
for linha in s.splitlines():
    m = re.match(r"^## (Fase \d+) — ", linha)
    if m: fase = m.group(1)
    if fase and linha.startswith("- [ ] T"):
        print(fase); break
PY
}

abertas_da_fase() {
  python3 - "$TAREFAS" "$1" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
alvo = f"Fase {sys.argv[2]}"; fase = None; n = 0
for linha in s.splitlines():
    m = re.match(r"^## (Fase \d+) — ", linha)
    if m: fase = m.group(1)
    if fase == alvo and linha.startswith("- [ ] T"): n += 1
print(n)
PY
}

case "${1:-situacao}" in
  situacao)
    echo "════ situação das fases ════"; situacao
    echo; echo "fase corrente: $(atual || echo 'nenhuma — tudo fechado')"
    if [ -f "$REGISTRO" ]; then echo; echo "fases já fechadas com verificação completa:"; cat "$REGISTRO"; fi
    ;;
  atual) atual ;;
  fechar)
    N="${2:?uso: fase.sh fechar N}"
    ABERTAS=$(abertas_da_fase "$N")
    if [ "$ABERTAS" -ne 0 ]; then
      echo "✗ Fase $N tem $ABERTAS tarefa(s) aberta(s) — não fecha."
      exit 1
    fi
    echo "→ Fase $N sem tarefas abertas. Rodando verificação completa…"
    if ! "$RAIZ/scripts/harness/verify-nucleo.sh"; then
      echo "✗ Fase $N NÃO fecha: a verificação completa falhou."
      exit 1
    fi
    mkdir -p "$RAIZ/.harness"
    echo "Fase $N fechada em $(date '+%Y-%m-%d %H:%M')" >> "$REGISTRO"
    echo "✓ Fase $N fechada."
    ;;
  *) echo "uso: fase.sh [situacao|atual|fechar N]"; exit 1 ;;
esac
