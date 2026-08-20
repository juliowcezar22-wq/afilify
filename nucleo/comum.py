"""
NÚCLEO — compartilhado por todos os marketplaces
================================================

Nada aqui sabe o que é Mercado Livre ou Shopee. Contém o que vale para
qualquer origem de oferta:

    marcas          whitelist, famílias, contratipo
    mensagem        headlines, formato, limpeza de título
    banco           fila, dedup, status de envio
    ritmo           plano do dia, cadência, cota
    whatsapp        uazapi
    infra           .env, log, HTTP, trava de instância única

A configuração específica de cada marketplace fica no módulo dele:
    mercadolivre/config.py   categoria, termos de busca, cookie
    shopee/config.py         credenciais da API, filtros de loja
"""

from __future__ import annotations

from __future__ import annotations
import argparse
import fcntl
import gzip
import html as _html
import json
import math
import os
import random
import re
import signal
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field

from nucleo import nicho, perfil
from nucleo.nicho import normalizar
from datetime import datetime, timedelta, timezone

# ══════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO — mexa aqui
# ══════════════════════════════════════════════════════════════════════

DESCONTO_MINIMO = 10          # % — abaixo disso não é oferta
# O fluxo do n8n só exigia "tem mL no título", o que deixa passar frasco de
# 10ml (decant). 0 mantém o comportamento antigo; 50 corta os decants.
VOLUME_MINIMO_ML = 0

# ══════════════════════════════════════════════════════════════════════
# MARCAS — só publica o que estiver aqui
# ══════════════════════════════════════════════════════════════════════
# A marca vem do rótulo que o PRÓPRIO ML põe no card, não de regex no título.
# É bem mais confiável: "Perfume Sedutor Árabe Sabah 100ml" não cita marca
# nenhuma no nome, mas o ML rotula como AL WATANIAH.
# Quando o card não tem rótulo, cai para o título. E card sem rótulo costuma
# ser exatamente a paralela que você não quer (Bacarati, 512 Vip Balck…).
#
# Para curar a lista com dado real, rode:  python3 agente_ml.py marcas

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

# Você citou os três — mantive só o que é inequivocamente conhecido.
# Tire ou acrescente à vontade.
MARCAS_NACIONAIS = [
    "Natura", "O Boticário", "Boticário", "Boticario", "Eudora",
    "Avon", "Jequiti", "Granado", "Phebo", "Mahogany", "O.U.i", "OUI",
    "Racco", "Ciclo",
    # vistas no grupo do MAENO — em alta
    "Paris Elysees", "Paris Elysées", "Lescent", "L'Acqua di Fiori",
    "Água de Cheiro", "Agua de Cheiro",
]

# Casas nacionais cujo contratipo você aceita. É AQUI que os termos
# "inspirado / contratipo / referência olfativa" são permitidos — em
# qualquer outra marca eles derrubam o anúncio.
# Só pus as duas que você nomeou: chutar marca aqui é publicar paralela
# no grupo com a sua tag.
MARCAS_CASAS_NACIONAIS = [
    "Lab 8", "Lab8", "Lab 8 Fragrances", "Inthebox", "In The Box",
]

MARCAS_PERMITIDAS = (
    MARCAS_IMPORTADAS + MARCAS_ARABES + MARCAS_NACIONAIS + MARCAS_CASAS_NACIONAIS
)

# Grafias diferentes da mesma marca, para não virarem duas na listagem.
# marca normalizada → família, para a proporção de envio
def _familias() -> dict:
    mapa = {}
    for lista, familia in (
        (MARCAS_IMPORTADAS, "importada"),
        (MARCAS_ARABES, "arabe"),
        (MARCAS_NACIONAIS, "nacional"),
        (MARCAS_CASAS_NACIONAIS, "casa"),
    ):
        for m in lista:
            mapa.setdefault(m, familia)
    return mapa


MARCAS_FAMILIA = _familias()
FAMILIAS_IMPORTADAS = ("importada", "arabe")

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

# Contratipo só passa se a marca estiver em MARCAS_CASAS_NACIONAIS.
TERMOS_CONTRATIPO = [
    "contratipo", "contra tipo", "inspirado", "inspirada", "inspiração",
    "similar ao", "similar a", "referencia olfativa", "referência olfativa",
    "equivalente a", "no estilo", "tipo importado", "replica", "réplica",
]

# BLOCO 1 roda nestas horas (hora cheia, fuso de TIMEZONE)
# Com o clonador ligado, o buscador vira RESERVA: o MAENO publica ~126/dia e
# o clone aproveita ~93%, o que já enche a cota sozinho. Duas coletas por dia
# bastam para (a) cobrir se o rival parar e (b) trazer o que ele não achou —
# que é o único conteúdo que diferencia o seu grupo do dele.
# Sem clonador, volte para [7, 12, 17, 22].
BUSCA_HORAS = [7, 15]

# BLOCO 3
# ── o plano do dia ───────────────────────────────────────────────────
# Sorteado UMA VEZ por dia, na primeira vez que o agente olha o relógio.
# Grupo de verdade não posta 70 ofertas todo dia entre 08:00 e 22:00 cravado:
# um dia manda 62, outro 81, começa 8h40, termina 22h20. Estes três sorteios
# são o que tira o engessamento.
ENVIOS_POR_DIA = (95, 135)        # OFERTAS por dia — o MAENO fez 95..135
ENVIO_INICIO_JANELA = (8.75, 9.5) # início sorteado — o MAENO abre ~09:09
ENVIO_FIM_JANELA = (22.0, 22.75)  # fim sorteado — o MAENO fecha ~22:27

ENVIO_POR_EXECUCAO = 1        # ofertas por rodada. 0 = todas as pendentes
PAUSA_HUMANIZADA = (5, 15)    # segundos antes de cada envio

# Falha de envio não pode matar a oferta: a uazapi engasga, a rede cai. A
# oferta volta para a fila com espera crescente e só vira ERRO definitivo
# depois de esgotar as tentativas.
ENVIO_TENTATIVAS = 3
ENVIO_ESPERA_TENTATIVA = 15   # minutos × número da tentativa

# ── ritmo dos envios ─────────────────────────────────────────────────
# ADAPTATIVO: o intervalo médio sai de "quanto falta" dividido por "quantas
# ofertas restam" — fila cheia acelera, fila curta desacelera, e o dia é
# sempre preenchido de ponta a ponta.
#
# A FORMA da distribuição é copiada do grupo do MAENO, medida em 400
# mensagens ao longo de 4 dias: mediana 5min, média 7min, 13% saindo em
# menos de 2min e uma cauda fina até ~70min. Isso é um lognormal com
# sigma 0.82 — testado bucket a bucket contra o real.
#
# Por que lognormal e não "sorteio uniforme + rajada": o modelo de rajada
# deixava um vazio entre 3 e 5min, justo onde o MAENO concentra 31% dos
# envios. O lognormal produz as rajadas naturalmente, sem remendo.
ENVIO_ADAPTATIVO = True
ENVIO_DISPERSAO = 0.82              # sigma. Maior = mais rajada e mais cauda
ENVIO_INTERVALO_LIMITES = (1, 90)   # trava de segurança, não o ritmo
ENVIO_INTERVALO_FIXO = (30, 55)     # usado só se ENVIO_ADAPTATIVO = False
VALIDADE_HORAS = 48           # não envia oferta capturada há mais que isso. 0 = desliga
ORDEM_ENVIO = "novas"         # "novas" | "antigas" | "maior_desconto"

# Importado (inclusive árabe) vende mais que nacional: é o que o pessoal quer
# e não compra por causa do preço de loja. A fila é servida para manter esta
# proporção ao longo do dia — se os importados já passaram da cota, entra
# nacional; se estão atrás, importado fura na frente.
PROPORCAO_IMPORTADOS = 0.70   # 0.70 = 7 de cada 10 envios. 0 desliga

# Sem piso de preço: você prefere deixar passar oferta muito barata.
# Efeito colateral conhecido: falsificação de grife (tipo 'Creed Aventus
# 25ml a R$ 65') volta a passar, porque o ML rotula ela como CREED mesmo.
PRECO_MINIMO_FAMILIA: dict[str, float] = {}



# ── filtros de título (portados do node "Code: Extrair Dados das Ofertas") ──
KEYWORDS_OBRIGATORIAS = [
    "PERFUME", "COLÔNIA", "COLONIA", "PARFUM",
    "EAU DE TOILETTE", "EAU DE PARFUM",
    "BODY SPLASH", "BODY MIST",
    "FRAGRÂNCIA", "FRAGRANCIA",
]

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

# ══════════════════════════════════════════════════════════════════════
# MENSAGEM
# ══════════════════════════════════════════════════════════════════════
# Formato:
#     O FAMOSINHO DO GRUPO NO PRECINHO      ← headline sorteada
#
#     Club De Nuit Intense Men 105ml
#
#     De ~R$ 319,00~ ❌
#     Por *R$ 242,00* ✅
#
#     Loja Oficial Lipx no ML               ← só quando o ML confirma
#     🔗 https://meli.la/2MHbcXj

MENSAGEM_BASE = """*{headline}*

*{nome}*

De ~R$ {preco_original}~ ❌
Por *R$ {preco_promocional}* ✅
{linha_loja}🔗 {link}"""

# Linha da loja. Sai só quando o ML marca a loja como oficial no card —
# não inventamos selo que o ML não deu.
LINHA_LOJA_OFICIAL = "\nLoja Oficial {loja} no ML\n"
LINHA_LOJA_COMUM = "\nVendido por {loja} no ML\n"
MOSTRAR_LOJA_COMUM = False     # True mostra também vendedor não-oficial

# Sai no fim da mensagem. Vazio = igual ao print que você mandou.
# Link de afiliado é publicidade; se quiser sinalizar, ponha algo como
# "_#publicidade · link de afiliado_" aqui.
RODAPE_MENSAGEM = ""

# Headlines sorteadas. O agente escolhe o grupo pelo contexto da oferta
# (badge e tamanho do desconto) e sorteia dentro dele, sem repetir a última.
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

DESCONTO_ALTO = 45            # % a partir do qual usa as headlines de choque
DESCONTO_MEDIO = 25

# O título do ML vem entulhado de SEO: "Perfume Ted Lapidus Pour Homme Edt M
# 100ml Novo Lacrado Original Homem". No grupo isso polui. A limpeza tira o
# prefixo "Perfume ..." e as palavras de vitrine do fim — nunca o miolo, e
# nunca se sobrar menos de 3 palavras.
LIMPAR_TITULO = True
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

# ── mensagens antigas por badge (do n8n) — não usadas no formato novo ──
# WhatsApp usa UM til para tachado (~texto~). O fluxo usava dois, que saem
# literais na tela.
MENSAGENS = {
    "OFERTA DO DIA": """⏰ *OFERTA VÁLIDA SÓ HOJE!*

📦 {nome}

💰 De ~R$ {preco_original}~ por *R$ {preco_promocional}*

⚡ Corre que acaba rápido!

🔗 {link}""",

    "OFERTA RELÂMPAGO": """⚡ *RELÂMPAGO - ESTOQUE LIMITADO!*

📦 {nome}

🔥 *R$ {preco_promocional}*

💥 Aproveita antes que esgote!

🔗 {link}""",

    "MAIS VENDIDO": """🏆 *BEST SELLER EM PROMOÇÃO*

📦 {nome}

💰 ~R$ {preco_original}~ → *R$ {preco_promocional}*

✅ Produto mais vendido da categoria!

🔗 {link}""",

    "PROMOÇÃO GERAL": """🔥 *PROMOÇÃO IMPERDÍVEL*

📦 {nome}

💰 De R$ {preco_original} por *R$ {preco_promocional}*

🔗 {link}""",
}


# ══════════════════════════════════════════════════════════════════════
# .env
# ══════════════════════════════════════════════════════════════════════
# Este arquivo vive em nucleo/; credenciais e dados ficam na raiz do projeto,
# um nível acima, compartilhados por todos os marketplaces.
RAIZ_MODULO = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(RAIZ_MODULO)
DADOS = os.path.join(RAIZ, "dados")
os.makedirs(DADOS, exist_ok=True)


def carregar_env(caminho: str = "") -> None:
    caminho = caminho or os.path.join(RAIZ, ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()

# ── perfil ativo ─────────────────────────────────────────────────────
# Define o nicho, o grupo de destino e o ritmo. Tudo abaixo lê daqui, e é
# por isso que dois grupos podem dividir o mesmo banco e o mesmo processo.
PERFIL = perfil.ativo()
PERFIL_ATIVO = PERFIL.nome
nicho.usar(PERFIL.nicho)

UAZAPI_GRUPO = (PERFIL.grupo_whatsapp
                or os.environ.get("UAZAPI_GRUPO", "").strip())

# O PERFIL É QUEM MANDA. As constantes homônimas lá em cima são os defaults
# documentados; estas reatribuições vêm depois e vencem no import. (Um passe
# de dedup em 19/08 comentou estas linhas por engano — mascarado porque os
# valores do perfil de perfumes coincidiam com as constantes. Teste cobre.)
ENVIOS_POR_DIA = PERFIL.envios_por_dia
ENVIO_INICIO_JANELA = PERFIL.inicio_janela
ENVIO_FIM_JANELA = PERFIL.fim_janela
ENVIO_DISPERSAO = PERFIL.dispersao
PROPORCAO_IMPORTADOS = PERFIL.proporcao_preferidas
BUSCA_HORAS = PERFIL.busca_horas
VALIDADE_HORAS = PERFIL.validade_horas
FAMILIAS_IMPORTADAS = tuple(nicho.ativo().familias_preferidas)

# Re-promoção (blueprint §10): oferta JÁ ENVIADA cujo preço caiu de novo em
# relação ao preço DA ÉPOCA DO ENVIO volta à fila como novidade. Comparar com
# o preço enviado (não com a última coleta) evita ping-pong em oscilação.
QUEDA_REPUBLICA_PCT = 15      # % de queda que justifica republicar. 0 desliga

BANCO = os.environ.get("ML_BANCO", os.path.join(DADOS, "ofertas.db"))

UAZAPI_URL = os.environ.get("UAZAPI_URL", "https://pessoal.uazapi.com").rstrip("/")
UAZAPI_TOKEN = os.environ.get("UAZAPI_TOKEN", "").strip()
# UAZAPI_GRUPO: definido pelo perfil, acima


# ── fuso: a VPS quase sempre está em UTC, o grupo não ──
def _fuso():
    nome = os.environ.get("TIMEZONE", "America/Sao_Paulo")
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome)
    except Exception:
        # imagem enxuta sem tzdata — cai no horário de Brasília fixo
        return timezone(timedelta(hours=-3), "America/Sao_Paulo")


TZ = _fuso()


def agora() -> datetime:
    return datetime.now(TZ)


# ══════════════════════════════════════════════════════════════════════
# log
# ══════════════════════════════════════════════════════════════════════
_COR = sys.stdout.isatty()
VERDE, VERMELHO, AMARELO, CINZA, AZUL, FIM = (
    ("\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[36m", "\033[0m")
    if _COR else ("", "", "", "", "", "")
)


def _log(marca: str, cor: str, msg: str) -> None:
    prefixo = os.environ.get("LOG_PREFIXO", "")
    print(f"{CINZA}{agora():%d/%m %H:%M:%S}{FIM} {prefixo}{cor}{marca}{FIM} {msg}", flush=True)


def info(msg: str) -> None:
    _log("·", CINZA, msg)


def ok(msg: str) -> None:
    _log("✓", VERDE, msg)


def aviso(msg: str) -> None:
    _log("!", AMARELO, msg)


def erro(msg: str) -> None:
    _log("✗", VERMELHO, msg)


# ══════════════════════════════════════════════════════════════════════
# HTTP
# ══════════════════════════════════════════════════════════════════════
UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
)


class HttpErro(RuntimeError):
    def __init__(self, codigo: int, detalhe: str):
        super().__init__(f"HTTP {codigo}: {detalhe}")
        self.codigo = codigo
        self.detalhe = detalhe


def _descomprimir(bruto: bytes, encoding: str) -> bytes:
    if encoding == "gzip":
        return gzip.decompress(bruto)
    if encoding == "deflate":
        try:
            return zlib.decompress(bruto)
        except zlib.error:
            return zlib.decompress(bruto, -zlib.MAX_WBITS)
    return bruto


def requisitar(
    url: str,
    *,
    metodo: str = "GET",
    corpo: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 40,
) -> str:
    req = urllib.request.Request(url, data=corpo, headers=headers or {}, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            bruto = _descomprimir(resp.read(), resp.headers.get("Content-Encoding", ""))
            return bruto.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            detalhe = _descomprimir(
                e.read(), e.headers.get("Content-Encoding", "")
            ).decode("utf-8", "replace")[:400]
        except Exception:
            detalhe = e.reason or ""
        raise HttpErro(e.code, detalhe) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"falha de rede: {e.reason}") from e


def requisitar_json(url: str, **kw) -> dict:
    texto = requisitar(url, **kw)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"resposta não é JSON: {texto[:200]}") from e


# ══════════════════════════════════════════════════════════════════════
# BANCO — substitui a planilha do Google
# ══════════════════════════════════════════════════════════════════════
SCHEMA = """
CREATE TABLE IF NOT EXISTS ofertas (
    mlb_id            TEXT PRIMARY KEY,
    nome              TEXT NOT NULL,
    url               TEXT NOT NULL,
    imagem            TEXT NOT NULL DEFAULT '',
    preco_original    REAL,
    preco_promocional REAL,
    desconto_pct      INTEGER,
    badge             TEXT NOT NULL DEFAULT 'PROMOÇÃO GERAL',
    condicao          TEXT NOT NULL DEFAULT '',
    marca             TEXT NOT NULL DEFAULT '',
    familia           TEXT NOT NULL DEFAULT '',
    origem            TEXT NOT NULL DEFAULT 'busca',
    perfil            TEXT NOT NULL DEFAULT 'perfumes-ml',
    rival_nome        TEXT NOT NULL DEFAULT '',
    rival_preco       REAL,
    rival_link        TEXT NOT NULL DEFAULT '',
    titulo_norm       TEXT NOT NULL DEFAULT '',
    vendedor          TEXT NOT NULL DEFAULT '',
    loja              TEXT NOT NULL DEFAULT '',
    loja_oficial      INTEGER NOT NULL DEFAULT 0,
    avaliacao         REAL NOT NULL DEFAULT 0,
    vendidos          TEXT NOT NULL DEFAULT '',
    link_afiliado     TEXT NOT NULL DEFAULT '',
    status_envio      TEXT NOT NULL DEFAULT 'PENDENTE',
    erro              TEXT NOT NULL DEFAULT '',
    tentativas        INTEGER NOT NULL DEFAULT 0,
    proxima_tentativa TEXT,
    criado_em         TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL,
    enviado_em        TEXT
);
CREATE INDEX IF NOT EXISTS idx_ofertas_status ON ofertas(status_envio);
CREATE INDEX IF NOT EXISTS idx_ofertas_titulo ON ofertas(titulo_norm);
CREATE TABLE IF NOT EXISTS estado (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS config (
    perfil        TEXT NOT NULL,
    chave         TEXT NOT NULL,
    valor         TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY (perfil, chave)
);
CREATE TABLE IF NOT EXISTS entregas (
    mlb_id        TEXT NOT NULL,
    canal         TEXT NOT NULL,
    perfil        TEXT NOT NULL DEFAULT 'perfumes-ml',
    status        TEXT NOT NULL DEFAULT 'enviando',
    tentativa     INTEGER NOT NULL DEFAULT 1,
    id_externo    TEXT NOT NULL DEFAULT '',
    erro          TEXT NOT NULL DEFAULT '',
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY (mlb_id, canal)
);
"""


# colunas acrescentadas depois da v1 — bancos antigos recebem via ALTER
COLUNAS_NOVAS = {
    "condicao": "TEXT NOT NULL DEFAULT ''",
    "marca": "TEXT NOT NULL DEFAULT ''",
    "familia": "TEXT NOT NULL DEFAULT ''",
    "origem": "TEXT NOT NULL DEFAULT 'busca'",
    "perfil": "TEXT NOT NULL DEFAULT 'perfumes-ml'",
    "rival_nome": "TEXT NOT NULL DEFAULT ''",
    "rival_preco": "REAL",
    "rival_link": "TEXT NOT NULL DEFAULT ''",
    "titulo_norm": "TEXT NOT NULL DEFAULT ''",
    "preco_enviado": "REAL",
    "vendedor": "TEXT NOT NULL DEFAULT ''",
    "loja": "TEXT NOT NULL DEFAULT ''",
    "loja_oficial": "INTEGER NOT NULL DEFAULT 0",
    "tentativas": "INTEGER NOT NULL DEFAULT 0",
    "proxima_tentativa": "TEXT",
    "avaliacao": "REAL NOT NULL DEFAULT 0",
    "vendidos": "TEXT NOT NULL DEFAULT ''",
}


def abrir_banco():
    """O banco da operação. STORAGE=postgres muda o motor, não o contrato:
    quem chama continua recebendo execute/commit/close e linhas por nome."""
    if os.environ.get("STORAGE", "sqlite").lower() in ("postgres", "pg"):
        from nucleo import storage
        return storage.conectar_pg()

    con = sqlite3.connect(BANCO, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    existentes = {c["name"] for c in con.execute("PRAGMA table_info(ofertas)")}
    for coluna, tipo in COLUNAS_NOVAS.items():
        if coluna not in existentes:
            con.execute(f"ALTER TABLE ofertas ADD COLUMN {coluna} {tipo}")
    # índices que dependem de coluna migrada vêm DEPOIS do ALTER
    con.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_perfil ON ofertas(perfil)")
    con.commit()
    return con


def ler_estado(con: sqlite3.Connection, chave: str) -> str:
    """Estado é POR PERFIL: dois grupos não podem dividir plano do dia,
    contagem de envio nem histórico do clonador."""
    linha = con.execute(
        "SELECT valor FROM estado WHERE chave = ?", (f"{PERFIL_ATIVO}:{chave}",)
    ).fetchone()
    return linha["valor"] if linha else ""


def gravar_estado(con: sqlite3.Connection, chave: str, valor: str) -> None:
    con.execute(
        "INSERT INTO estado (chave, valor) VALUES (?, ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (f"{PERFIL_ATIVO}:{chave}", valor),
    )
    con.commit()


def reais(valor: float | None) -> str:
    if not valor:
        return "—"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def uazapi_configurado() -> bool:
    return bool(UAZAPI_URL and UAZAPI_TOKEN and UAZAPI_GRUPO)


def uazapi_grupo_info(jid: str = "") -> dict:
    """Nome e dados do grupo de destino. Confirma que você está mirando certo."""
    return requisitar_json(
        UAZAPI_URL + "/group/info",
        metodo="POST",
        corpo=json.dumps({"groupjid": jid or UAZAPI_GRUPO}).encode("utf-8"),
        headers={"Content-Type": "application/json", "token": UAZAPI_TOKEN},
    )


def uazapi_grupos() -> list[dict]:
    dados = requisitar_json(
        UAZAPI_URL + "/group/list", headers={"token": UAZAPI_TOKEN}
    )
    return dados.get("groups") or []


def mensagens_do_grupo(jid: str, limite: int = 20) -> list[dict]:
    dados = requisitar_json(
        UAZAPI_URL + "/message/find",
        metodo="POST",
        corpo=json.dumps({"chatid": jid, "limit": limite}).encode("utf-8"),
        headers={"Content-Type": "application/json", "token": UAZAPI_TOKEN},
    )
    return dados.get("messages") or []


def uazapi_enviar(texto: str, imagem: str = "") -> str:
    headers = {"Content-Type": "application/json", "token": UAZAPI_TOKEN}
    if imagem:
        rota, corpo = "/send/media", {
            "number": UAZAPI_GRUPO,
            "type": "image",
            "file": imagem,
            "text": texto,
        }
    else:
        # o seu fluxo sempre manda imagem; isto só entra se a oferta vier sem
        rota, corpo = "/send/text", {"number": UAZAPI_GRUPO, "text": texto}

    resposta = requisitar_json(
        UAZAPI_URL + rota,
        metodo="POST",
        corpo=json.dumps(corpo, ensure_ascii=False).encode("utf-8"),
        headers=headers,
    )
    return str(resposta.get("id") or resposta.get("messageid") or "enviada")


# ══════════════════════════════════════════════════════════════════════
# OFERTA, MARCAS E FILTROS — valem para qualquer marketplace
# ══════════════════════════════════════════════════════════════════════
RE_VOLUME_ML = re.compile(r"\b(\d{2,4})\s?ML\b", re.I)
RE_EDP_EDT = re.compile(r"\b(EDP|EDT)\b")

@dataclass
class Oferta:
    mlb_id: str
    nome: str
    url: str
    imagem: str = ""
    preco_original: float = 0.0
    preco_promocional: float = 0.0
    desconto_pct: int = 0
    badge: str = "PROMOÇÃO GERAL"
    condicao: str = ""      # "no Pix" — o preço às vezes só vale nessa forma
    marca: str = ""
    vendedor: str = ""
    loja: str = ""
    loja_oficial: bool = False
    avaliacao: float = 0.0
    vendidos: str = ""
    link_afiliado: str = ""
    recusa: str = field(default="", compare=False)


# ── marcas ──────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════
# FILTROS — a REGRA é fixa, o CONTEÚDO vem do nicho ativo
# ══════════════════════════════════════════════════════════════════════
# Nada abaixo sabe o que é perfume. Tudo que é específico (keywords,
# blacklist, marcas, unidade de medida) vem de nichos/<nome>.py através de
# nucleo.nicho.ativo(). Trocar de nicho não toca em nenhuma linha daqui.


def contem_expressao(texto_norm: str, expressao_norm: str) -> bool:
    """Casa palavra inteira: 'brand' não casa dentro de 'brand collection'."""
    return re.search(rf"(?<!\w){re.escape(expressao_norm)}(?!\w)", texto_norm) is not None


def achar_marca(rotulo: str, titulo: str) -> tuple[str, bool, str]:
    """(marca, aceita_contratipo, de_onde). Marca mais longa vence, para
    'Jean Paul Gaultier' não virar 'Paul'."""
    n = nicho.ativo()
    for de_onde, origem in (("rotulo", normalizar(rotulo)),
                            ("titulo", normalizar(titulo))):
        if not origem:
            continue
        for chave in sorted(n.marcas_norm, key=len, reverse=True):
            if contem_expressao(origem, chave):
                nome = n.marcas_norm[chave]
                familia = n.familia_por_marca.get(chave, "")
                return (n.apelidos.get(nome, nome),
                        familia in n.familias_contratipo,
                        de_onde)
    return "", False, ""


def familia_da_marca(marca: str) -> str:
    """A família da marca no nicho ativo — usada na proporção de envio."""
    if not marca:
        return ""
    n = nicho.ativo()
    alvo = normalizar(marca)
    familia = n.familia_por_marca.get(alvo)
    if familia:
        return familia
    # a marca canônica pode ter vindo de um apelido
    for chave, nome in n.marcas_norm.items():
        if normalizar(n.apelidos.get(nome, nome)) == alvo:
            return n.familia_por_marca.get(chave, "")
    return ""


def filtrar_marca(rotulo: str, titulo: str) -> tuple[str, str, str]:
    """(marca, motivo_recusa, de_onde_veio_a_marca).

    Nicho com exige_marca=False (casa, por exemplo) não recusa por marca:
    a whitelist ali serve para destacar, não para barrar.
    """
    n = nicho.ativo()
    marca, aceita_contratipo, de_onde = achar_marca(rotulo, titulo)
    if not marca:
        return ("", "marca não conhecida", "") if n.exige_marca else ("", "", "")

    if not aceita_contratipo and n.contratipo_norm:
        titulo_norm = normalizar(titulo)
        for termo in n.contratipo_norm:
            if contem_expressao(titulo_norm, termo):
                return marca, "contratipo de marca não autorizada", de_onde
    return marca, "", de_onde


def filtrar_titulo(titulo: str) -> str:
    """Título é do nicho? Devolve o motivo da recusa, ou ''."""
    n = nicho.ativo()
    titulo_maiusculo = titulo.upper()
    tem_keyword = any(k in titulo_maiusculo for k in n.keywords)
    if not tem_keyword and n.re_qualifica:
        tem_keyword = bool(n.re_qualifica.search(titulo_maiusculo))
    if not tem_keyword:
        return f"não é {n.nome}"
    if any(k in titulo_maiusculo for k in n.blacklist):
        return "blacklist"
    return ""


def filtrar_volume(titulo: str) -> str:
    """Unidade de medida do nicho.

    Em perfume é mL e serve para barrar decant. Nicho sem unidade (casa,
    eletrônico) deixa UNIDADE_REGEX vazio e esta checagem some — não é
    desligada por flag, simplesmente não existe para aquele nicho.
    """
    n = nicho.ativo()
    if not n.re_unidade:
        return ""
    achados = [int(v) for v in n.re_unidade.findall(titulo)]
    if not achados:
        return f"sem volume em {n.unidade_nome}"
    if n.unidade_minima and max(achados) < n.unidade_minima:
        return f"volume < {n.unidade_minima}{n.unidade_nome}"
    return ""


def filtrar_preco(original: float, promocional: float, desconto: int) -> str:
    if not promocional or not original:
        return "sem preço de/por"
    if original <= promocional:
        return "sem desconto"
    minimo = nicho.ativo().desconto_minimo
    if desconto < minimo:
        return f"desconto < {minimo}%"
    return ""


def salvar_oferta(con: sqlite3.Connection, o: Oferta) -> bool:
    """Insere ou atualiza por MLB_ID. Devolve True se a oferta é nova.

    Igual ao appendOrUpdate do n8n: numa oferta já conhecida, atualiza os
    dados do produto mas preserva link de afiliado e status de envio.
    """
    ts = agora().isoformat(timespec="seconds")
    existente = con.execute(
        "SELECT status_envio, preco_enviado FROM ofertas "
        "WHERE mlb_id = ? AND perfil = ?", (o.mlb_id, PERFIL_ATIVO)
    ).fetchone()
    ja_existe = existente is not None

    # ── re-promoção: caiu de preço depois de enviada? volta à fila ──
    if (ja_existe and QUEDA_REPUBLICA_PCT
            and existente["status_envio"] == "ENVIADO"
            and (existente["preco_enviado"] or 0) > 0
            and o.preco_promocional > 0):
        base = existente["preco_enviado"]
        queda = (base - o.preco_promocional) / base * 100
        if queda >= QUEDA_REPUBLICA_PCT:
            con.execute(
                "UPDATE ofertas SET status_envio='PENDENTE', tentativas=0, "
                "proxima_tentativa=NULL, erro='', atualizado_em=? WHERE mlb_id=?",
                (ts, o.mlb_id),
            )
            # libera a trava de entrega — sem isto a idempotência (correta
            # contra duplicata) bloquearia a republicação legítima
            con.execute("DELETE FROM entregas WHERE mlb_id=? AND perfil=?",
                        (o.mlb_id, PERFIL_ATIVO))
            ok(f"re-promoção: {o.nome[:44]} caiu de "
               f"{reais(base)} para {reais(o.preco_promocional)} (−{queda:.0f}%)")

    # o mesmo perfume com outro MLB_ID (avulso vs catálogo) já na fila:
    # não cria segunda linha, senão o grupo recebe a oferta duas vezes
    if not ja_existe and con.execute(
        "SELECT 1 FROM ofertas WHERE titulo_norm = ? AND mlb_id != ? AND perfil = ?",
        (normalizar(o.nome), o.mlb_id, PERFIL_ATIVO),
    ).fetchone():
        return False
    con.execute(
        """
        INSERT INTO ofertas (mlb_id, nome, url, imagem, preco_original,
                             preco_promocional, desconto_pct, badge, condicao,
                             marca, familia, vendedor, loja, loja_oficial, avaliacao,
                             perfil, link_afiliado,
                             vendidos, titulo_norm, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mlb_id) DO UPDATE SET
            nome              = excluded.nome,
            url               = excluded.url,
            imagem            = excluded.imagem,
            preco_original    = excluded.preco_original,
            preco_promocional = excluded.preco_promocional,
            desconto_pct      = excluded.desconto_pct,
            badge             = excluded.badge,
            condicao          = excluded.condicao,
            marca             = excluded.marca,
            familia           = excluded.familia,
            titulo_norm       = excluded.titulo_norm,
            vendedor          = excluded.vendedor,
            loja              = excluded.loja,
            loja_oficial      = excluded.loja_oficial,
            avaliacao         = excluded.avaliacao,
            vendidos          = excluded.vendidos,
            link_afiliado     = CASE WHEN excluded.link_afiliado != ''
                                     THEN excluded.link_afiliado
                                     ELSE ofertas.link_afiliado END,
            atualizado_em     = excluded.atualizado_em
        """,
        (o.mlb_id, o.nome, o.url, o.imagem, o.preco_original, o.preco_promocional,
         o.desconto_pct, o.badge, o.condicao, o.marca, familia_da_marca(o.marca),
         o.vendedor, o.loja,
         int(o.loja_oficial), o.avaliacao, PERFIL_ATIVO, o.link_afiliado,
         o.vendidos, normalizar(o.nome), ts, ts),
    )
    return not ja_existe


# ══════════════════════════════════════════════════════════════════════
# MENSAGEM — formato fixo, conteúdo do nicho
# ══════════════════════════════════════════════════════════════════════
def limpar_titulo(nome: str) -> str:
    """Tira o SEO do título do ML sem mexer no miolo do produto."""
    n = nicho.ativo()
    if not nome:
        return nome
    limpo = re.sub(r"\s+", " ", nome).strip(" -–,")

    # prefixo: o mais longo primeiro, para "perfume arabe" ganhar de "perfume"
    for prefixo in sorted(n.titulo_prefixos, key=len, reverse=True):
        if normalizar(limpo).startswith(prefixo + " "):
            candidato = limpo[len(prefixo):].strip(" -–,")
            if len(candidato.split()) >= 3:
                limpo = candidato
            break

    # ruído no fim, uma palavra por vez
    mudou = True
    while mudou:
        mudou = False
        for ruido in sorted(n.titulo_ruido, key=len, reverse=True):
            atual = normalizar(limpo)
            if atual.endswith(" " + ruido):
                candidato = limpo[: len(limpo) - len(ruido)].strip(" -–,")
                if len(candidato.split()) >= 3:
                    limpo, mudou = candidato, True
                    break
        # tirar "mulher" de "... Para Mulher" deixa "Para" pendurado
        conectores = ("para", "pra", "de", "da", "do", "com", "e", "em", "no", "na")
        palavras = limpo.split()
        if len(palavras) > 3 and normalizar(palavras[-1]) in conectores:
            limpo, mudou = " ".join(palavras[:-1]).strip(" -–,"), True
    return limpo or nome


def grupo_de_headline(linha: sqlite3.Row) -> str:
    """Qual pool de headline combina com esta oferta."""
    badge = (linha["badge"] or "").upper()
    if "RELÂMPAGO" in badge or "RELAMPAGO" in badge:
        return "relampago"
    if "OFERTA DO DIA" in badge:
        return "oferta_do_dia"
    if "MAIS VENDIDO" in badge:
        return "mais_vendido"
    desconto = linha["desconto_pct"] or 0
    if desconto >= DESCONTO_ALTO:
        return "desconto_alto"
    if desconto >= DESCONTO_MEDIO:
        return "desconto_medio"
    return "geral"


def sortear_headline(con: sqlite3.Connection | None, linha: sqlite3.Row) -> str:
    """Sorteia uma headline do pool, evitando repetir a última usada."""
    hl = config_json(con, "headlines", nicho.ativo().headlines)
    pool = hl.get(grupo_de_headline(linha)) or hl.get("geral") or ["🔥 OFERTA"]
    ultima = ler_estado(con, "ultima_headline") if con is not None else ""
    opcoes = [h for h in pool if h != ultima] or list(pool)
    escolhida = random.choice(opcoes)
    if con is not None:
        gravar_estado(con, "ultima_headline", escolhida)
    return escolhida


def linha_da_loja(linha: sqlite3.Row, con=None) -> str:
    loja = (linha["loja"] or "").strip()
    if not loja:
        return "\n"
    if linha["loja_oficial"]:
        cfg = config_json(con, "mensagem", {})
        return (cfg.get("linha_loja_oficial") or LINHA_LOJA_OFICIAL).format(loja=loja)
    return LINHA_LOJA_COMUM.format(loja=loja) if MOSTRAR_LOJA_COMUM else "\n"


def montar_mensagem(linha: sqlite3.Row, con: sqlite3.Connection | None = None) -> str:
    nome = limpar_titulo(linha["nome"])
    # "no Pix" precisa aparecer: o preço do card às vezes só vale nessa forma
    # de pagamento, e o grupo reclama se descobrir só no checkout.
    condicao = (linha["condicao"] or "").strip()
    promocional = reais(linha["preco_promocional"]) + (f" {condicao}" if condicao else "")

    cfg = config_json(con, "mensagem", {})
    modelo = cfg.get("base") or MENSAGEM_BASE
    rodape = cfg.get("rodape") if cfg.get("rodape") is not None else RODAPE_MENSAGEM
    texto = modelo.format(
        headline=sortear_headline(con, linha),
        nome=nome if len(nome) <= 110 else nome[:109] + "…",
        preco_original=reais(linha["preco_original"]),
        preco_promocional=promocional,
        linha_loja=linha_da_loja(linha, con),
        link=linha["link_afiliado"] or linha["url"],
    )
    return f"{texto}\n\n{rodape}" if rodape else texto


# ══════════════════════════════════════════════════════════════════════
# CONFIG DINÂMICA — o painel edita, o motor obedece SEM restart
# ══════════════════════════════════════════════════════════════════════
# JSON por (perfil, chave), lido a cada uso (~1 leitura por envio). Chave
# ausente = valores do nicho/constantes. garantir_config() semeia as chaves
# na subida do daemon com os valores vigentes — ligar isto não muda NADA
# até alguém editar de fato pelo painel.

def config_json(con, chave: str, padrao):
    if con is None:
        return padrao
    try:
        linha = con.execute(
            "SELECT valor FROM config WHERE perfil = ? AND chave = ?",
            (PERFIL_ATIVO, chave)).fetchone()
        return json.loads(linha["valor"]) if linha else padrao
    except Exception:
        return padrao          # config quebrada nunca derruba publicação


def gravar_config(con, chave: str, valor) -> None:
    con.execute(
        "INSERT INTO config (perfil, chave, valor, atualizado_em) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (perfil, chave) DO UPDATE SET valor = excluded.valor, "
        "atualizado_em = excluded.atualizado_em",
        (PERFIL_ATIVO, chave, json.dumps(valor, ensure_ascii=False),
         agora().isoformat(timespec="seconds")))
    con.commit()


def ritmo_cfg(con) -> dict:
    """Ritmo vigente: config do painel por cima dos valores do perfil."""
    padrao = {
        "envios_por_dia": list(ENVIOS_POR_DIA),
        "inicio_janela": list(ENVIO_INICIO_JANELA),
        "fim_janela": list(ENVIO_FIM_JANELA),
        "busca_horas": list(BUSCA_HORAS),
        "validade_horas": VALIDADE_HORAS,
        "proporcao_preferidas": PROPORCAO_IMPORTADOS,
    }
    cfg = config_json(con, "ritmo", {})
    return {**padrao, **{k: v for k, v in cfg.items() if v is not None}}


def garantir_config(con) -> int:
    """Semeia chaves ausentes com os valores vigentes (nicho/constantes)."""
    n_semeadas = 0
    padroes = {
        "headlines": nicho.ativo().headlines,
        "mensagem": {
            "base": MENSAGEM_BASE,
            "linha_loja_oficial": LINHA_LOJA_OFICIAL,
            "rodape": RODAPE_MENSAGEM,
        },
        "ritmo": {
            "envios_por_dia": list(ENVIOS_POR_DIA),
            "inicio_janela": list(ENVIO_INICIO_JANELA),
            "fim_janela": list(ENVIO_FIM_JANELA),
            "busca_horas": list(BUSCA_HORAS),
            "validade_horas": VALIDADE_HORAS,
            "proporcao_preferidas": PROPORCAO_IMPORTADOS,
        },
    }
    for chave, valor in padroes.items():
        existe = con.execute(
            "SELECT 1 FROM config WHERE perfil = ? AND chave = ?",
            (PERFIL_ATIVO, chave)).fetchone()
        if not existe:
            gravar_config(con, chave, valor)
            n_semeadas += 1
    return n_semeadas


# ══════════════════════════════════════════════════════════════════════
# ENTREGAS — idempotência de publicação (blueprint, Parte 8)
# ══════════════════════════════════════════════════════════════════════
# A regra: NENHUM POST sem antes reservar a entrega. A reserva é um INSERT
# com chave (mlb_id, canal); quem não conseguiu inserir não envia. Crash
# entre o POST e o registro deixa a entrega em 'enviando' — a reconciliação
# olha as últimas mensagens do grupo: o link de afiliado é único, então ou
# a mensagem está lá (sela como enviada) ou não está (libera para reenvio).

RECONCILIAR_APOS_MIN = 10


def reservar_entrega(con, mlb_id: str, canal: str = "") -> bool:
    """True = esta execução é dona do envio. False = já feito/em curso."""
    canal = canal or UAZAPI_GRUPO
    ts = agora().isoformat(timespec="seconds")
    cur = con.execute(
        "INSERT INTO entregas (mlb_id, canal, perfil, status, criado_em, atualizado_em) "
        "VALUES (?, ?, ?, 'enviando', ?, ?) "
        "ON CONFLICT (mlb_id, canal) DO NOTHING",
        (mlb_id, canal, PERFIL_ATIVO, ts, ts),
    )
    if cur.rowcount:
        con.commit()
        return True

    linha = con.execute(
        "SELECT status FROM entregas WHERE mlb_id = ? AND canal = ?",
        (mlb_id, canal),
    ).fetchone()
    if linha and linha["status"] == "falhou":
        # falha anterior: reutiliza a reserva para o retry
        con.execute(
            "UPDATE entregas SET status='enviando', tentativa = tentativa + 1, "
            "atualizado_em = ? WHERE mlb_id = ? AND canal = ?",
            (ts, mlb_id, canal),
        )
        con.commit()
        return True
    return False        # 'enviada' ou 'enviando' de outra execução


def concluir_entrega(con, mlb_id: str, id_externo: str, canal: str = "") -> None:
    con.execute(
        "UPDATE entregas SET status='enviada', id_externo=?, atualizado_em=? "
        "WHERE mlb_id = ? AND canal = ?",
        (id_externo, agora().isoformat(timespec="seconds"), mlb_id, canal or UAZAPI_GRUPO),
    )
    con.commit()


def falhar_entrega(con, mlb_id: str, erro_txt: str, canal: str = "") -> None:
    con.execute(
        "UPDATE entregas SET status='falhou', erro=?, atualizado_em=? "
        "WHERE mlb_id = ? AND canal = ?",
        (erro_txt[:300], agora().isoformat(timespec="seconds"),
         mlb_id, canal or UAZAPI_GRUPO),
    )
    con.commit()


def reconciliar_entregas(con, buscar=mensagens_do_grupo) -> int:
    """Resolve entregas presas em 'enviando' (crash no meio do POST).

    Devolve quantas foram resolvidas. `buscar` é injetável para teste.
    """
    corte = (agora() - timedelta(minutes=RECONCILIAR_APOS_MIN)).isoformat(
        timespec="seconds")
    presas = con.execute(
        "SELECT e.mlb_id, e.canal, o.link_afiliado FROM entregas e "
        "JOIN ofertas o ON o.mlb_id = e.mlb_id "
        "WHERE e.status='enviando' AND e.atualizado_em < ? AND e.perfil = ?",
        (corte, PERFIL_ATIVO),
    ).fetchall()
    if not presas:
        return 0

    resolvidas = 0
    por_canal: dict[str, list[str]] = {}
    for p in presas:
        if p["canal"] not in por_canal:
            try:
                msgs = buscar(p["canal"], 50)
            except (HttpErro, RuntimeError):
                continue            # sem rede: tenta na próxima
            por_canal[p["canal"]] = [m.get("text") or "" for m in msgs]
        textos = por_canal[p["canal"]]
        ts = agora().isoformat(timespec="seconds")
        if p["link_afiliado"] and any(p["link_afiliado"] in t for t in textos):
            # a mensagem CHEGOU ao grupo antes do crash: sela tudo
            con.execute("UPDATE entregas SET status='enviada', atualizado_em=? "
                        "WHERE mlb_id=? AND canal=?", (ts, p["mlb_id"], p["canal"]))
            con.execute("UPDATE ofertas SET status_envio='ENVIADO', enviado_em=?, "
                        "atualizado_em=?, preco_enviado=preco_promocional "
                        "WHERE mlb_id=?", (ts, ts, p["mlb_id"]))
            ok(f"entrega recuperada pós-crash: {p['mlb_id']} já estava no grupo")
        else:
            # não chegou: libera a reserva, a oferta volta à fila normalmente
            con.execute("DELETE FROM entregas WHERE mlb_id=? AND canal=?",
                        (p["mlb_id"], p["canal"]))
            aviso(f"entrega presa liberada para reenvio: {p['mlb_id']}")
        resolvidas += 1
    con.commit()
    return resolvidas
