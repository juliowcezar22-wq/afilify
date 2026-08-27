#!/usr/bin/env bash
# GATE ANTI-MOCK — constitution, princípio III: nada de funcionalidade
# simulada. Dado exibido vem de dado real; estado vem do serviço real.
#
# Procura, no caminho de PRODUÇÃO do painel e do motor:
#   · fixtures/mocks/stubs importados fora de tests/
#   · listas de exemplo embutidas em página ("dadosFalsos", "exemplo = [")
#   · sucesso fabricado (retorno fixo de estado "conectado", "enviada"…)
#
# Falso-positivo legítimo? Marque a linha com `harness-ok` — a exceção fica
# visível no diff, como no check de linguagem.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ALVOS_TS=("$RAIZ/painel/app" "$RAIZ/painel/components" "$RAIZ/painel/lib")
ALVOS_PY=("$RAIZ/nucleo" "$RAIZ/mercadolivre" "$RAIZ/shopee")

PADROES=(
  "mock[A-Za-z]*"
  "[Ff]ixture"
  "dados[Ff]alsos|dadosFake|fakeData"
  "stub[A-Za-z]*"
  "TODO: *conectar (de verdade|real)"
  "placeholder de dados"
  "simula(r|ndo) (sucesso|conex|envio)"
)

FALHAS=0
for p in "${PADROES[@]}"; do
  HITS=$(grep -rnE "$p" "${ALVOS_TS[@]}" --include='*.ts' --include='*.tsx' 2>/dev/null \
    | grep -v "harness-ok" || true)
  HITS_PY=$(grep -rnE "$p" "${ALVOS_PY[@]}" --include='*.py' 2>/dev/null \
    | grep -v "harness-ok" || true)
  TUDO="$HITS
$HITS_PY"
  TUDO=$(echo "$TUDO" | grep -v '^$' || true)
  if [ -n "$TUDO" ]; then
    echo "✗ possível simulação em caminho de produção (\"$p\"):"
    echo "$TUDO" | head -8
    FALHAS=1
  fi
done

if [ "$FALHAS" -ne 0 ]; then
  echo "── check-mock: FALHOU (use dado real, ou mova para tests/, ou marque harness-ok) ──"
  exit 1
fi
echo "✓ check-mock ok (nenhuma simulação no caminho de produção)"
