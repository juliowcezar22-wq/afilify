#!/usr/bin/env bash
# FULL CHECK da rodada do núcleo SaaS.
#
#   fast-check (lint + typecheck) → build → linguagem → anti-mock →
#   congelados → testes do motor → tarefas abertas
#
# Fonte de verdade das tarefas: specs/001-afilify-saas-core/tasks.md
# (uma lista só — o harness não mantém cópia que possa divergir).
#
# Sucesso grava .harness/last-verify-ok com a assinatura da árvore; o Stop
# hook usa isso para saber se a verificação vale para o estado atual.
#
# Flags: --sem-build   pula o build (uso interativo; NÃO grava marcador)
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PAINEL="$RAIZ/painel"
TAREFAS="$RAIZ/specs/001-afilify-saas-core/tasks.md"
SEM_BUILD=0
[ "${1:-}" = "--sem-build" ] && SEM_BUILD=1

FALHAS=()
echo "════ verify-nucleo ════"

# 1. lint + typecheck
"$RAIZ/scripts/harness/fast-check.sh" || FALHAS+=("lint/typecheck")

# 2. build de produção
if [ "$SEM_BUILD" -eq 0 ]; then
  echo "→ build"
  if ! (cd "$PAINEL" && pnpm build >/tmp/afilify-build.log 2>&1); then
    echo "✗ build falhou:"; tail -40 /tmp/afilify-build.log
    FALHAS+=("build")
  else
    echo "✓ build ok"
  fi
fi

# 3. linguagem de produto
"$RAIZ/scripts/harness/check-linguagem.sh" || FALHAS+=("linguagem")

# 4. nada simulado no caminho de produção
"$RAIZ/scripts/harness/check-mock.sh" || FALHAS+=("anti-mock")

# 5. Clonador e monitoramento intocados
"$RAIZ/scripts/harness/guarda-congelados.sh" || FALHAS+=("congelados")

# 6. suíte do motor — roda em banco temporário e recusa banco real
echo "→ testes do motor"
if ! (cd "$RAIZ" && python3 -m unittest discover -s tests -t . >/tmp/afilify-py.log 2>&1); then
  echo "✗ testes do motor falharam:"; tail -30 /tmp/afilify-py.log
  FALHAS+=("testes-motor")
else
  echo "✓ testes do motor ok ($(grep -oE 'Ran [0-9]+ tests' /tmp/afilify-py.log | tail -1))"
fi

# 7. QA de navegador — console, rede e layout nas rotas do fluxo comum.
# Só roda quando há painel de pé: subir um aqui tornaria o gate lento demais
# para o uso normal.
if curl -s -m 3 -o /dev/null "${QA_BASE:-http://localhost:3105}/api/health" 2>/dev/null; then
  echo "→ QA de navegador"
  if ! node "$RAIZ/scripts/harness/qa-browser.mjs" "${QA_BASE:-http://localhost:3105}" "${QA_COOKIE:-}" >/tmp/afilify-qa.log 2>&1; then
    echo "✗ QA de navegador falhou:"; tail -20 /tmp/afilify-qa.log
    FALHAS+=("qa-navegador")
  else
    echo "✓ QA de navegador ok"
  fi
else
  echo "· QA de navegador pulado (nenhum painel respondendo em ${QA_BASE:-http://localhost:3105})"
fi

# 8. tarefas abertas (grep -c sai 1 sem match — capturar só o stdout)
ABERTAS=$(grep -c '^- \[ \] T' "$TAREFAS" 2>/dev/null || true)
ABERTAS=${ABERTAS:-0}
echo "· tarefas abertas: $ABERTAS"

echo "═══════════════════════"
if [ "${#FALHAS[@]}" -gt 0 ]; then
  echo "RESULTADO: FALHOU → ${FALHAS[*]}"
  exit 1
fi

if [ "$SEM_BUILD" -eq 0 ]; then
  mkdir -p "$RAIZ/.harness"
  (cd "$RAIZ" && {
    git rev-parse HEAD
    git status --porcelain
    git diff HEAD
    git ls-files --others --exclude-standard -z | xargs -0 shasum 2>/dev/null
  } | shasum | cut -d' ' -f1) > "$RAIZ/.harness/last-verify-ok"
fi

if [ "$ABERTAS" -gt 0 ]; then
  echo "RESULTADO: checks OK · $ABERTAS tarefa(s) abertas"
  exit 0
fi
echo "RESULTADO: OK — checks passam e não há tarefas abertas"
