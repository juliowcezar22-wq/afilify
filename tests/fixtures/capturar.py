"""Re-captura as fixtures com HTML fresco do ML.

Rodar da raiz quando o layout mudar:  python3 tests/fixtures/capturar.py
"""
import sys, os, gzip
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from mercadolivre import buscador as b

AQUI = os.path.dirname(os.path.abspath(__file__))
html = b.baixar_pagina(1)
assert b.extrair_contexto(html), "vitrine sem estado embutido — não salvo"
gzip.open(os.path.join(AQUI, "vitrine.html.gz"), "wt", encoding="utf-8").write(html)
h2 = b.baixar_busca("perfume masculino")
assert b.contexto_da_busca(h2), "busca sem payload — rode de novo"
gzip.open(os.path.join(AQUI, "busca.html.gz"), "wt", encoding="utf-8").write(h2)
print("fixtures atualizadas")
