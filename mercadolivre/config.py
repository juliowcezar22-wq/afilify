"""
Configuração do agente do Mercado Livre.

O que é genérico (marcas, mensagem, ritmo, banco) mora em nucleo/comum.py.
Aqui fica só o que é do ML.
"""

import os

from nucleo.comum import RAIZ

CATEGORIA_ID = "MLB6284"      # Perfumes
PAGINAS_MAX = 100             # teto de páginas da vitrine (o ML diz o real)
PAGINAS_VAZIAS_ATE_PARAR = 2  # páginas seguidas sem oferta = fim do catálogo
PAUSA_ENTRE_PAGINAS = (1.0, 2.5)   # segundos, sorteado — não martelar o ML

# ── FONTE 2: a busca ──────────────────────────────────────────────────
# A vitrine /ofertas tem ~54 anúncios e é pobre de marca. A busca tem
# centenas por termo e é de onde saem Rabanne, Dior, Natura, Lattafa.
# Cada termo = 1 requisição e até 60 produtos.
#
# EXIGE o cookie de sessão (.mlcookie): sem ele o ML devolve a página de
# verificação. Sem cookie o agente pula a busca e usa só a vitrine.
#
# Atenção ao escolher termo: em algumas consultas o ML responde em streaming
# e o payload não vem na primeira resposta. 'boticario' funciona,
# 'perfume boticario' devolve casca vazia. Valide com `agente_ml.py termos`.
TERMOS_BUSCA = [
    # genéricos — pegam o topo do ranking, muita sobreposição entre si
    "perfumes",
    "perfumaria",
    "perfume importado",
    "perfume original lacrado",
    "eau de parfum",
    # com volume: rendem quase o dobro, o "100ml" já filtra decant e sachê
    "perfume 100ml",
    "perfume masculino 100ml",
    "perfume feminino 100ml",
    "perfume arabe 100ml",
    # segmento
    "perfume masculino",
    "perfume feminino",
    "perfume arabe",
    # nacionais que você nomeou
    "perfume natura",
    "boticario",
    "eudora",
]
PAUSA_ENTRE_BUSCAS = (4.0, 8.0)   # a busca é mais sensível que a vitrine


# ── afiliado (sessão da própria conta) ───────────────────────────────
ML_AFFILIATE_TAG = os.environ.get("ML_AFFILIATE_TAG", "").strip()
ARQUIVO_COOKIE = os.environ.get("ML_COOKIE_FILE", os.path.join(RAIZ, ".mlcookie"))

# ── foto ─────────────────────────────────────────────────────────────
IMAGEM_ALTA_RESOLUCAO = True
IMAGEM_TAMANHO = "O"
FOTO_ESTRATEGIA = "card"
FOTO_INDICE_GALERIA = 1
FOTO_SO_IMPORTADAS = True
