"""
NICHO: PERFUMES

Um nicho descreve O QUE É uma oferta válida — nada além disso. Não sabe de
marketplace, de WhatsApp, nem de horário.

Para criar outro nicho, copie este arquivo e troque o conteúdo. O motor em
nucleo/ não muda uma linha.
"""

NOME = "perfumes"
DESCRICAO = "Perfumaria importada, árabe e nacional de marca conhecida"

# Precisa de pelo menos uma destas no título para ser do nicho.
KEYWORDS_OBRIGATORIAS = [
    "PERFUME", "COLÔNIA", "COLONIA", "PARFUM",
    "EAU DE TOILETTE", "EAU DE PARFUM",
    "BODY SPLASH", "BODY MIST",
    "FRAGRÂNCIA", "FRAGRANCIA",
]

# Além das keywords: regex que também qualifica (EDP/EDT no caso de perfume).
REGEX_QUALIFICA = r"\b(EDP|EDT)\b"

# Se aparecer no título, descarta.
BLACKLIST = [
    "SACHÊ", "SACHE", "DIFUSOR", "AROMATIZADOR",
    "VELA", "AMBIENTE", "TECIDO", "AUTOMOTIVO",
    "CARRO", "CHEIRINHO", "PAPEL", "GAVETA",
    "AROMA DE AMBIENTE", "HOME SPRAY",
    "SABONETE", "CREME PERFUMADO", "HIDRATANTE",
    "LOÇÃO PERFUMADA", "LOCAO PERFUMADA",
    "SHAMPOO", "CONDICIONADOR", "DESODORANTE",
    "ANTITRANSPIRANTE", "TALCO",
    "AMOSTRA", "DECANT", "MINIATURA", "TESTER",
    "POTE VAZIO", "FRASCO VAZIO", "PARA REVENDA",
]

# ── unidade de medida do nicho ───────────────────────────────────────
# Em perfume é mL e serve para barrar decant. Num nicho de móveis isso não
# existe — basta deixar REGEX vazio que o motor pula a checagem.
UNIDADE_REGEX = r"\b(\d{2,4})\s?ML\b"
UNIDADE_NOME = "mL"
UNIDADE_MINIMA = 0        # 0 = só exige que exista, não impõe mínimo

DESCONTO_MINIMO = 10      # %

# ── marcas aceitas, por família ──────────────────────────────────────
MARCAS_IMPORTADAS = [
    "Dior", "Christian Dior", "Chanel", "Paco Rabanne", "Rabanne",
    "Carolina Herrera", "Giorgio Armani", "Armani", "Emporio Armani",
    "Jean Paul Gaultier", "Versace", "Lacoste", "Hugo Boss", "Boss",
    "Calvin Klein", "Dolce & Gabbana", "Dolce Gabbana",
    "Yves Saint Laurent", "Saint Laurent", "Givenchy", "Guerlain",
    "Bvlgari", "Bulgari", "Montblanc", "Mont Blanc", "Azzaro", "Kenzo",
    "Issey Miyake", "Mugler", "Thierry Mugler", "Prada", "Gucci",
    "Burberry", "Tommy Hilfiger", "Ralph Lauren", "Diesel", "Moschino",
    "Jimmy Choo", "Marc Jacobs", "Narciso Rodriguez", "Viktor & Rolf",
    "Cacharel", "Nina Ricci", "Salvatore Ferragamo", "Ferragamo",
    "Trussardi", "Antonio Banderas", "Banderas", "Shakira",
    "Gabriela Sabatini", "Britney Spears", "Animale", "Ferrari",
    "Ted Lapidus", "Lapidus", "Playboy", "Puma", "Adidas", "Benetton",
    "Coach", "Michael Kors", "Elizabeth Arden", "Lancome", "Cartier",
    "Hermes", "Tom Ford", "Creed", "Amouage", "Byredo",
    "Parfums de Marly", "Roberto Cavalli", "Escada", "Chopard",
    "Davidoff", "Jaguar", "Mercedes-Benz", "Bentley", "Lamborghini",
    "Police", "Guess", "DKNY", "Donna Karan", "Vera Wang",
    "Paris Hilton", "Jennifer Lopez", "Katy Perry", "Nautica",
    "Perry Ellis", "Aramis", "Clinique", "Estee Lauder", "Kouros",
]

MARCAS_ARABES = [
    "Lattafa", "Lataffa", "Afnan", "Armaf", "Rasasi", "Al Haramain",
    "Haramain", "Maison Alhambra", "Alhambra", "Ard Al Zaafaran",
    "Swiss Arabian", "Al Wataniah", "Wataniah", "Rayhaan", "Khadlaj",
    "Nusuk", "Bharara", "Orientica", "French Avenue", "Fragrance World",
    "Emper", "Zimaya", "Riiffs", "Paris Corner", "Al Rehab", "Ajmal",
    "Asdaaf", "Anfar", "My Perfumes", "Abdul Samad Al Qurashi",
    # vistas no grupo do MAENO — em alta.
    # Só entra o que o ML rotula como MARCA no card, conferido um a um:
    #   Elliur é perfume da Bidaya · Turathi é da Afnan · Al Wesal é da
    #   Al Wataniah · Wathiq e Al Fares não são marca. Ficaram de fora.
    "Bidaya", "Mawwal", "Grandeur", "Al Khaleej", "Maison Asrar",
    "Stella & Dustin", "Stella Dustin", "Maison Salem",
    # Não são marca de verdade, entram por decisão sua:
    #   Sabah Al Ward é linha da Al Wataniah, mas alguns vendedores viram
    #   "marca" no rótulo do ML. É específico, não abre brecha.
    #   Lipx é LOJA, e o ML rotula como marca — ela revende Lattafa, Armaf
    #   e Al Wataniah, então o risco é baixo.
    "Sabah Al Ward", "Lipx",
]

MARCAS_NACIONAIS = [
    "Natura", "O Boticário", "Boticário", "Boticario", "Eudora",
    "Avon", "Jequiti", "Granado", "Phebo", "Mahogany", "O.U.i", "OUI",
    "Racco", "Ciclo",
    # vistas no grupo do MAENO — em alta
    "Paris Elysees", "Paris Elysées", "Lescent", "L'Acqua di Fiori",
    "Água de Cheiro", "Agua de Cheiro",
]

MARCAS_CASAS_NACIONAIS = [
    "Lab 8", "Lab8", "Lab 8 Fragrances", "Inthebox", "In The Box",
]

# família → lista. O motor usa isso para a proporção de envio.
MARCAS = {
    "importada": MARCAS_IMPORTADAS,
    "arabe": MARCAS_ARABES,
    "nacional": MARCAS_NACIONAIS,
    "casa": MARCAS_CASAS_NACIONAIS,
}
# quais famílias contam como "importado" na PROPORCAO_IMPORTADOS
FAMILIAS_PREFERIDAS = ("importada", "arabe")
# famílias onde contratipo é aceito
FAMILIAS_CONTRATIPO = ("casa",)

MARCAS_APELIDOS = {
    "Lab8": "Lab 8", "Lab 8 Fragrances": "Lab 8",
    "In The Box": "Inthebox",
    "Boticario": "O Boticário", "Boticário": "O Boticário",
    "Lataffa": "Lattafa",
    "Rabanne": "Paco Rabanne",
    "Armani": "Giorgio Armani", "Emporio Armani": "Giorgio Armani",
    "Christian Dior": "Dior",
    "Saint Laurent": "Yves Saint Laurent",
    "Bulgari": "Bvlgari", "Mont Blanc": "Montblanc",
    "Boss": "Hugo Boss", "Banderas": "Antonio Banderas",
    "Haramain": "Al Haramain", "Alhambra": "Maison Alhambra",
    "Wataniah": "Al Wataniah", "Ferragamo": "Salvatore Ferragamo",
    "Lapidus": "Ted Lapidus", "Dolce Gabbana": "Dolce & Gabbana",
    "OUI": "O.U.i",
}

TERMOS_CONTRATIPO = [
    "contratipo", "contra tipo", "inspirado", "inspirada", "inspiração",
    "similar ao", "similar a", "referencia olfativa", "referência olfativa",
    "equivalente a", "no estilo", "tipo importado", "replica", "réplica",
]

# ── limpeza do título ────────────────────────────────────────────────
TITULO_PREFIXOS = [
    "perfume masculino", "perfume feminino", "perfume unissex",
    "perfume arabe masculino", "perfume arabe feminino", "perfume arabe",
    "perfume importado", "perfume", "deo parfum", "deo colonia",
]

TITULO_RUIDO = [
    "novo", "lacrado", "original", "originais", "importado", "importada",
    "promocao", "promoção", "envio imediato", "pronta entrega", "entrega rapida",
    "frete gratis", "frete grátis", "com nf-e", "com nfe", "nota fiscal",
    "100% original", "oferta", "barato", "masculino", "feminino", "unissex",
    "homem", "mulher", "presente", "kit", "lançamento", "lancamento",
]

# ── copy ─────────────────────────────────────────────────────────────
HEADLINES = {
    "relampago": [
        "⚡ RELÂMPAGO! ACABA A QUALQUER MOMENTO",
        "⚡ CORRE QUE É RELÂMPAGO",
        "⚡ ESTOQUE LIMITADO, VAI VOAR",
        "⚡ PISCOU, PERDEU",
    ],
    "oferta_do_dia": [
        "⏰ SÓ HOJE NESSE PREÇO",
        "⏰ OFERTA DO DIA, AMANHÃ VOLTA",
        "⏰ HOJE É O DIA DESSE AQUI",
    ],
    "mais_vendido": [
        "🏆 O FAMOSINHO DO GRUPO NO PRECINHO",
        "🏆 O QUERIDINHO DE VOCÊS BAIXOU",
        "🏆 CAMPEÃO DE VENDAS EM PROMOÇÃO",
        "🏆 TODO MUNDO PEDIU, TÁ AÍ",
    ],
    "desconto_alto": [        # >= 45%
        "🔥 PELA METADE DO PREÇO",
        "🔥 OLHA O TAMANHO DESSE DESCONTO",
        "🔥 PREÇO DE ERRO, CORRE",
        "🔥 DESABOU DE PREÇO",
        "🔥 ISSO AQUI TÁ QUASE DE GRAÇA",
    ],
    "desconto_medio": [       # >= 25%
        "💸 BAIXOU BONITO",
        "💸 ACHADINHO DO DIA",
        "💸 TÁ VALENDO MUITO A PENA",
        "💸 PREÇO BOM DEMAIS PRA IGNORAR",
        "💸 SEPAREI ESSE PRA VOCÊS",
    ],
    "geral": [
        "✨ OLHA O PRECINHO DESSE",
        "✨ ACHEI E TROUXE PRA VOCÊS",
        "✨ TÁ NA PROMO AGORA",
        "✨ DEU UMA CAÍDA BOA",
        "✨ APROVEITA ENQUANTO TÁ ASSIM",
    ],
}
# ── onde procurar, em cada marketplace ───────────────────────────────
MERCADOLIVRE = {
    "categoria": "MLB6284",           # Perfumes
    "termos": [
        "perfumes", "perfumaria", "perfume importado",
        "perfume original lacrado", "eau de parfum",
        "perfume 100ml", "perfume masculino 100ml",
        "perfume feminino 100ml", "perfume arabe 100ml",
        "perfume masculino", "perfume feminino", "perfume arabe",
        "perfume natura", "boticario", "eudora",
        # busca dirigida por marca: acha muito mais anúncio das casas já
        # aprovadas — o filtro de marcas segue de porteiro na entrada.
        "lattafa", "armaf", "maison alhambra", "afnan perfume",
        "al haramain", "rasasi", "al wataniah", "orientica",
        "bharara", "ard al zaafaran", "perfume malbec",
        "natura essencial", "natura kaiak", "boticario lily",
        "boticario egeo", "eudora impression",
    ],
}
SHOPEE = {
    "termos": [
        "perfume importado", "perfume masculino", "perfume feminino",
        "perfume arabe", "perfume natura", "perfume boticario",
        "perfume eudora", "eau de parfum",
    ],
}
