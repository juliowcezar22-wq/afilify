"""
NICHO: CASA E MÓVEIS

Mesma estrutura de nichos/perfumes.py. Repare no que MUDA de verdade:

  - não há unidade de medida a exigir (perfume tem mL, sofá não tem)
  - "marca" aqui é muito menos determinante: em casa o comprador não escolhe
    por marca, escolhe por preço e utilidade. Por isso EXIGE_MARCA = False,
    e a whitelist vira reforço, não porteiro.
  - o desconto mínimo é mais alto: casa vive de promoção o ano todo, 10% não
    é notícia.

Isso é o ponto da arquitetura: o motor em nucleo/ não muda nada.
"""

NOME = "casa"
DESCRICAO = "Utilidades, móveis e decoração"

KEYWORDS_OBRIGATORIAS = [
    "PANELA", "FRIGIDEIRA", "JOGO DE", "TALHER", "FACA", "TÁBUA",
    "TOALHA", "LENÇOL", "EDREDOM", "COBERTOR", "TRAVESSEIRO", "COLCHÃO",
    "CORTINA", "TAPETE", "ALMOFADA", "LUMINÁRIA", "ABAJUR",
    "CADEIRA", "MESA", "ESTANTE", "PRATELEIRA", "ARMÁRIO", "SOFÁ",
    "ORGANIZADOR", "CESTO", "POTE", "AIR FRYER", "LIQUIDIFICADOR",
    "CAFETEIRA", "ASPIRADOR", "VENTILADOR", "ESCORREDOR", "VARAL",
]
REGEX_QUALIFICA = ""          # nada além das keywords

BLACKLIST = [
    "USADO", "SEMINOVO", "DEFEITO", "AVARIADO", "SUCATA",
    "APENAS A CAPA", "SÓ A CAPA", "SEM O PRODUTO", "MINIATURA",
    "ADESIVO", "PAPEL DE PAREDE", "AMOSTRA", "BRINDE",
    "CASINHA DE BONECA", "PARA BONECA", "INFANTIL DE BRINQUEDO",
]

# Casa não tem unidade obrigatória. Regex vazio = motor pula a checagem.
UNIDADE_REGEX = ""
UNIDADE_NOME = ""
UNIDADE_MINIMA = 0

DESCONTO_MINIMO = 25          # casa vive de promoção; 10% não é notícia

# ── marcas ───────────────────────────────────────────────────────────
# Em casa o comprador não escolhe por marca. A whitelist aqui serve para
# DESTACAR o que é bom, não para barrar o resto.
EXIGE_MARCA = False

MARCAS = {
    "importada": [
        "Tramontina", "Brinox", "Electrolux", "Philco", "Mondial",
        "Britânia", "Oster", "Arno", "Cadence", "Multilaser",
        "Rochedo", "Marcbeau", "Le Creuset", "Nadir", "Duralex",
    ],
    "nacional": [
        "Buddemeyer", "Karsten", "Santista", "Teka", "Artex",
        "Corttex", "Camesa", "Altenburg", "Trussardi Casa",
        "Casa Vitra", "Mor", "Utilaço", "Plasútil", "Ordene",
    ],
}
FAMILIAS_PREFERIDAS = ("importada",)
FAMILIAS_CONTRATIPO = ()
MARCAS_APELIDOS = {"Britania": "Britânia"}
TERMOS_CONTRATIPO = []        # não se aplica

# ── limpeza do título ────────────────────────────────────────────────
TITULO_PREFIXOS = ["kit", "conjunto", "jogo de", "combo"]
TITULO_RUIDO = [
    "frete gratis", "frete grátis", "envio imediato", "pronta entrega",
    "promocao", "promoção", "oferta", "barato", "novo", "original",
    "com nota fiscal", "nf-e", "lançamento", "lancamento",
]

# ── copy ─────────────────────────────────────────────────────────────
HEADLINES = {
    "desconto_alto": [
        "🔥 PELA METADE DO PREÇO",
        "🔥 CAIU MUITO DE PREÇO",
        "🔥 PREÇO DE ERRO NESSE",
    ],
    "desconto_medio": [
        "🏠 PRA DEIXAR A CASA MAIS BONITA",
        "🏠 ACHADINHO PRA CASA",
        "🏠 ISSO AQUI FAZ FALTA EM CASA",
        "💸 BAIXOU BONITO",
    ],
    "geral": [
        "🏠 OLHA O PRECINHO DESSE",
        "🏠 SEPAREI PRA VOCÊS",
        "🏠 TÁ NA PROMO AGORA",
    ],
    "mais_vendido": [
        "🏆 O QUERIDINHO DA CASA BAIXOU",
        "🏆 CAMPEÃO DE VENDAS EM PROMOÇÃO",
    ],
    "oferta_do_dia": ["⏰ SÓ HOJE NESSE PREÇO"],
    "relampago": ["⚡ RELÂMPAGO! ACABA A QUALQUER MOMENTO"],
}

# ── onde procurar ────────────────────────────────────────────────────
MERCADOLIVRE = {
    "categoria": "MLB1574",        # Casa, Móveis e Decoração
    "termos": [
        "panela antiaderente", "jogo de panelas", "air fryer",
        "jogo de cama", "toalha de banho", "organizador",
        "luminária", "tapete sala", "cadeira escritório",
    ],
}
SHOPEE = {
    "termos": [
        "utensilios cozinha", "organizador casa", "jogo de cama",
        "toalha banho", "panela", "air fryer", "luminaria",
        "tapete", "porta temperos", "cesto organizador",
    ],
}
