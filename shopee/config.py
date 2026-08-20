"""
Configuração do agente da Shopee.

Marcas, mensagem, ritmo e banco vêm de nucleo/comum.py — são os mesmos do
Mercado Livre. Aqui fica só o que é da Shopee.
"""

import os

# ── API de afiliados (open-api.affiliate.shopee.com.br) ──────────────
# Diferente do ML: é API oficial, com credencial permanente. Não tem
# cookie para vencer, não tem scraping, e o offerLink já vem pronto com
# o seu código de afiliado — não existe passo "gerar link".
SHOPEE_APP_ID = os.environ.get("SHOPEE_APP_ID", "").strip()
SHOPEE_SECRET = os.environ.get("SHOPEE_SECRET", "").strip()
SHOPEE_ENDPOINT = os.environ.get(
    "SHOPEE_ENDPOINT", "https://open-api.affiliate.shopee.com.br/graphql"
)

# ── ANTIFALSIFICAÇÃO ─────────────────────────────────────────────────
# O catálogo de perfume da Shopee é MUITO pior que o do ML nesse aspecto.
# Medido em 200 anúncios: "Perfume Yara Lattafa 100ml" a R$ 21,90 quando o
# original custa R$ 180+. Havia dezenas assim.
#
# O sinal que separa é shopType: 1 = Loja Oficial (Shopee Mall).
# Nos oficiais apareceram Natura a R$ 96,90 e Paco Rabanne de R$ 310 a
# R$ 1.150 — preços de verdade. Fora deles, falsificação em série.
#
# Deixar isto em False enche o grupo de réplica com a sua tag de afiliado.
SOMENTE_LOJA_OFICIAL = True
SHOP_TYPE_OFICIAL = 1

# Rede de segurança para quando SOMENTE_LOJA_OFICIAL = False.
NOTA_MINIMA = 4.5
VENDAS_MINIMAS = 20

# ── busca ────────────────────────────────────────────────────────────
TERMOS_BUSCA = [
    "perfume importado",
    "perfume masculino",
    "perfume feminino",
    "perfume arabe",
    "perfume natura",
    "perfume boticario",
    "perfume eudora",
    "eau de parfum",
]
ITENS_POR_PAGINA = 50
PAGINAS_POR_TERMO = 2
PAUSA_ENTRE_BUSCAS = (1.0, 2.5)   # API oficial aguenta mais que scraping

# sortType 2 = maior venda; 4 = maior comissão
ORDENACAO = 2
