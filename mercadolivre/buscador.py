"""
BUSCADOR — de onde saem as ofertas
==================================

FONTE 1  a vitrine /ofertas (sem login, tem os badges relâmpago/do dia)
FONTE 2  a busca lista.mercadolivre.com.br (exige cookie, é o volume)

E o BLOCO 2, que transforma a URL do produto no seu link de afiliado.
"""

from __future__ import annotations

from __future__ import annotations
import argparse
import fcntl
import gzip
import html as _html
import json
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
from datetime import datetime, timedelta, timezone

from nucleo.comum import *  # noqa: F401,F403
from nucleo import nicho
from mercadolivre.config import *  # noqa: F401,F403
from nucleo.comum import (
    AZUL, CINZA, FIM, VERDE, VERMELHO, AMARELO,
)

# BLOCO 1 — BUSCA E EXTRAÇÃO DAS OFERTAS
# ══════════════════════════════════════════════════════════════════════
RE_TITULO = re.compile(r'class="poly-component__title".*?>(.*?)</a>', re.S)
RE_TAGS = re.compile(r"<.*?>", re.S)
RE_HREF = re.compile(r'href="(.*?)"', re.S)
# O ML usa três formatos de id e o fluxo original só pegava o primeiro:
#   /MLB-3994439565-nome...   anúncio avulso
#   /p/MLB6139411             produto de catálogo (às vezes só 6-7 dígitos)
#   /up/MLBU3402023514        catálogo unificado (tem letra no meio)
RE_ID_CATALOGO = re.compile(r"/(?:p|up)/(MLBU?\d+)", re.I)
RE_ID_ANUNCIO = re.compile(r"\bMLB-?(\d{8,15})\b", re.I)
RE_FRACAO = re.compile(r'class="andes-money-amount__fraction".*?>(.*?)</span>', re.S)
RE_CENTAVOS = re.compile(r'class="andes-money-amount__cents".*?>(.*?)</span>', re.S)
RE_ANTERIOR = re.compile(
    r'<s class=".*?andes-money-amount--previous.*?>(.*?)</s>', re.S
)
RE_ATUAL = re.compile(r'<div class="poly-price__current".*?>(.*?)</div>', re.S)
RE_IMG_POLY = re.compile(r'<img.*?class="poly-component__picture".*?src="(.*?)"', re.S)
RE_IMG_LAZY = re.compile(
    r'<img[^>]*class="poly-component__picture"[^>]*data-src="(.*?)"', re.S
)
RE_IMG_QUALQUER = re.compile(r'<img.*?src="(.*?)"', re.S)
RE_HIGHLIGHT = re.compile(r'class="poly-component__highlight".*?>(.*?)</span>', re.S)
RE_VOLUME_ML = re.compile(r"\b(\d{2,4})\s?ML\b", re.I)
RE_EDP_EDT = re.compile(r"\b(EDP|EDT)\b")


def limpar_texto(bruto: str) -> str:
    return _html.unescape(RE_TAGS.sub("", bruto)).strip()


def extrair_id(url_limpa: str) -> str:
    """MLB_ID a partir do caminho da URL (sem query — lá tem `deal:MLB779362`)."""
    m = RE_ID_CATALOGO.search(url_limpa)
    if m:
        return m.group(1).upper()
    m = RE_ID_ANUNCIO.search(url_limpa)
    return "MLB" + m.group(1) if m else ""


def escolher_link(bloco: str) -> tuple[str, str]:
    """(url_limpa, mlb_id) do primeiro href que é mesmo um produto.

    O card abre com âncoras de campanha (`#poly_black_friday`); pegar o href
    #1, como o fluxo do n8n fazia, derrubava a maioria das ofertas.
    """
    for href in RE_HREF.findall(bloco):
        href = _html.unescape(href.strip())
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = "https://www.mercadolivre.com.br" + href
        elif not href.startswith("http"):
            continue
        limpa = limpar_url(href)
        mlb_id = extrair_id(limpa)
        if mlb_id:
            return limpa, mlb_id
    return "", ""


def extrair_preco(bloco: str) -> float:
    """'R$ 1.234' + '56' → 1234.56. Devolve 0.0 quando não achou."""
    if not bloco:
        return 0.0
    m_fracao = RE_FRACAO.search(bloco)
    if not m_fracao:
        return 0.0
    inteiro = re.sub(r"\D", "", limpar_texto(m_fracao.group(1)))
    if not inteiro:
        return 0.0
    m_cent = RE_CENTAVOS.search(bloco)
    centavos = re.sub(r"\D", "", limpar_texto(m_cent.group(1))) if m_cent else ""
    centavos = (centavos + "00")[:2] if centavos else "00"
    return float(f"{inteiro}.{centavos}")


def imagem_grande(url: str) -> str:
    """Miniatura do ML na versão 2X, quando disponível."""
    if not IMAGEM_ALTA_RESOLUCAO or not url:
        return url
    if "D_NQ_NP_" in url and "D_NQ_NP_2X_" not in url:
        return url.replace("D_NQ_NP_", "D_NQ_NP_2X_", 1)
    return url


def classificar_badge(bloco: str) -> str:
    m = RE_HIGHLIGHT.search(bloco)
    texto = limpar_texto(m.group(1)).upper() if m else ""
    if "OFERTA DO DIA" in texto:
        return "OFERTA DO DIA"
    if "RELÂMPAGO" in texto or "RELAMPAGO" in texto:
        return "OFERTA RELÂMPAGO"
    if "MAIS VENDIDO" in texto:
        return "MAIS VENDIDO"
    if "CUPOM" in texto:
        return "CUPOM"
    return "PROMOÇÃO GERAL"


def extrair_ofertas(pagina_html: str, vistos: set[str]) -> tuple[list[Oferta], dict[str, int]]:
    """Aplica os 6 filtros do node de extração. Devolve (aprovadas, contagem_recusas)."""
    recusas: dict[str, int] = {}

    def recusar(motivo: str) -> None:
        recusas[motivo] = recusas.get(motivo, 0) + 1

    ofertas: list[Oferta] = []
    for bloco in pagina_html.split('class="andes-card poly-card')[1:]:
        m_titulo = RE_TITULO.search(bloco)
        titulo = limpar_texto(m_titulo.group(1)) if m_titulo else ""
        if not titulo:
            continue
        # 1, 2, 3 — keyword de perfume, blacklist e volume
        motivo = filtrar_titulo(titulo)
        if motivo:
            recusar(motivo)
            continue

        # 3b — marca. Aqui só existe o título: o HTML não traz o rótulo.
        marca, motivo, _ = filtrar_marca("", titulo)
        if motivo:
            recusar(motivo)
            continue
        motivo = filtrar_volume(titulo)     # sem rótulo aqui: sempre exige
        if motivo:
            recusar(motivo)
            continue

        # link + MLB_ID
        link, mlb_id = escolher_link(bloco)
        if not mlb_id:
            recusar("sem link de produto")
            continue

        # 4 — dedup dentro da mesma execução
        if mlb_id in vistos:
            continue
        vistos.add(mlb_id)

        # preços
        m_ant = RE_ANTERIOR.search(bloco)
        preco_original = extrair_preco(m_ant.group(1) if m_ant else "")
        m_atual = RE_ATUAL.search(bloco)
        preco_promocional = extrair_preco(m_atual.group(1) if m_atual else "")

        # 5 e 6 — desconto real e acima do mínimo
        desconto = (
            round((preco_original - preco_promocional) / preco_original * 100)
            if preco_original > preco_promocional > 0
            else 0
        )
        motivo = filtrar_preco(preco_original, preco_promocional, desconto)
        if motivo:
            recusar(motivo)
            continue

        # imagem (o ML entrega placeholder em src e a real em data-src)
        m_img = RE_IMG_POLY.search(bloco)
        imagem = m_img.group(1) if m_img else ""
        if not imagem or imagem.startswith("data:"):
            m_lazy = RE_IMG_LAZY.search(bloco)
            if m_lazy:
                imagem = m_lazy.group(1)
        if not imagem or imagem.startswith("data:"):
            m_qualquer = RE_IMG_QUALQUER.search(bloco)
            imagem = m_qualquer.group(1) if m_qualquer else ""
        if imagem.startswith("//"):
            imagem = "https:" + imagem
        if imagem.startswith("data:"):
            imagem = ""

        ofertas.append(
            Oferta(
                mlb_id=mlb_id,
                nome=titulo,
                url=link,
                imagem=imagem_grande(imagem),
                preco_original=preco_original,
                preco_promocional=preco_promocional,
                desconto_pct=desconto,
                badge=classificar_badge(bloco),
                marca=marca,
            )
        )

    return ofertas, recusas


# ── fonte primária: o estado que o ML já renderiza dentro da página ──
# Muito melhor que os regexes: preço exato (o HTML perde os centavos), badge,
# vendedor, nota, total de páginas. É o mesmo dado que alimenta os cards.
RE_CONTEXTO = re.compile(
    r'<script id="__NORDIC_RENDERING_CTX__"[^>]*>(.*?)</script>', re.S
)


def extrair_contexto(pagina_html: str) -> dict | None:
    m = RE_CONTEXTO.search(pagina_html)
    if not m:
        return None
    corpo = m.group(1)
    igual = corpo.find("=")
    if igual == -1:
        return None
    try:
        raiz, _ = json.JSONDecoder().raw_decode(corpo[igual + 1 :].lstrip())
    except (json.JSONDecodeError, ValueError):
        return None
    dados = ((raiz.get("appProps") or {}).get("pageProps") or {}).get("data")
    return dados if isinstance(dados, dict) and dados.get("items") else None


def resolver_texto(no: dict) -> str:
    """'{label} por KID'S LIFE {icon}' + values → 'AL WATANIAH por KID'S LIFE'."""
    texto = no.get("text") or ""
    for v in no.get("values") or []:
        tipo = v.get("type")
        if tipo == "label":
            troca = (v.get("label") or {}).get("text") or ""
        elif tipo == "pill":
            troca = (v.get("pill") or {}).get("text") or ""
        else:
            troca = ""
        texto = texto.replace("{" + str(v.get("key")) + "}", troca)
    return re.sub(r"\s+", " ", re.sub(r"\{[^}]*\}", "", texto)).strip()


def montar_imagem(card: dict, contexto: dict) -> str:
    fotos = (card.get("pictures") or {}).get("pictures") or []
    if not fotos or not fotos[0].get("id"):
        return ""
    pc = contexto.get("polycardContext") or {}
    modelo = pc.get("picture_template") or (
        "https://http2.mlstatic.com/D_{square}_NP{2x}_{id}-{size}{sanitized_title}.webp"
    )
    return (
        modelo.replace("{square}", (card.get("pictures") or {}).get("square") or "Q")
        .replace("{2x}", "_2X" if IMAGEM_ALTA_RESOLUCAO else "")
        .replace("{id}", fotos[0]["id"])
        .replace("{size}", IMAGEM_TAMANHO or pc.get("picture_size_default") or "AB")
        .replace(
            "{sanitized_title}", (card.get("pictures") or {}).get("sanitized_title") or ""
        )
    )


def marca_do_card(comps: dict) -> str:
    """O rótulo de marca que o ML põe no card — 'AL WATANIAH', 'NATURA'.

    No template '{label} por KID'S LIFE', o label é a MARCA e o resto é a
    loja. Card sem esse rótulo quase sempre é anúncio de paralela.
    """
    seller = (comps.get("seller") or {}).get("seller") or {}
    for v in seller.get("values") or []:
        if v.get("type") == "label":
            return (v.get("label") or {}).get("text") or ""
    return ""


RE_VENDIDO_POR = re.compile(r"\bpor\s+(.+)$", re.I | re.S)


def titulo_bonito(nome: str) -> str:
    """'KID'S LIFE' → 'Kid's Life'. Deixa 'B.Stories' e 'Lipx' em paz."""
    if not nome or not nome.isupper():
        return nome
    return re.sub(
        r"[A-ZÀ-Ý][A-ZÀ-Ý']*",
        lambda m: m.group(0)[0] + m.group(0)[1:].lower(),
        nome,
    )


def loja_do_card(comps: dict) -> tuple[str, bool]:
    """(nome da loja, é loja oficial).

    O ML monta esse campo de quatro jeitos:
      '{label} por Lipx {icon_cockade}'  → marca LATTAFA, loja Lipx, oficial
      '{label} {icon_cockade}'           → a própria marca é a loja oficial
      'Gota Brasil {icon_cockade}'       → loja oficial sem marca no rótulo
      '{label}'                          → vendedor comum, não oficial
    """
    seller = (comps.get("seller") or {}).get("seller") or {}
    if not seller:
        return "", False

    oficial = any(
        v.get("type") == "icon"
        and (
            "cockade" in str((v.get("icon") or {}).get("icon_id") or "")
            or "loja oficial" in str((v.get("icon") or {}).get("alt_text") or "").lower()
        )
        for v in seller.get("values") or []
    )

    texto = resolver_texto(seller)          # já sem os {placeholders}
    m = RE_VENDIDO_POR.search(texto)
    return titulo_bonito((m.group(1) if m else texto).strip()), oficial


def badge_do_card(card: dict) -> str:
    rotulos = []
    for w in card.get("widget_components") or []:
        if w.get("id") != "highlight":
            continue
        comp = w.get("poly_label_component") or {}
        rotulos += [resolver_texto(lb) for lb in comp.get("labels") or []]
    texto = " ".join(r for r in rotulos if r).upper()
    if "OFERTA DO DIA" in texto:
        return "OFERTA DO DIA"
    if "RELÂMPAGO" in texto or "RELAMPAGO" in texto:
        return "OFERTA RELÂMPAGO"
    if "MAIS VENDIDO" in texto:
        return "MAIS VENDIDO"
    if "CUPOM" in texto:
        return "CUPOM"
    # rótulo de campanha (ex.: "OFERTA IMPERDÍVEL" na Black Friday). Guardamos
    # o texto: se você criar um modelo com esse nome em MENSAGENS, ele é usado.
    return texto.strip() or "PROMOÇÃO GERAL"


def precos_do_card(preco: dict) -> tuple[float, float, int, str]:
    """(original, promocional, desconto%, condição)."""
    promocional = float((preco.get("current_price") or {}).get("value") or 0)

    original = 0.0
    for rotulo in preco.get("price_labels") or []:
        for v in rotulo.get("values") or []:
            p = v.get("price") or {}
            if v.get("type") == "price" and (
                p.get("previous") or v.get("key") == "previous_price"
            ):
                original = max(original, float(p.get("value") or 0))

    # o % que o cliente vê no site ganha do calculado — evita o grupo
    # anunciar 46% onde a página mostra 45%
    desconto = 0
    for v in (preco.get("discount_polylabel") or {}).get("values") or []:
        m = re.search(r"(\d{1,3})\s*%", (v.get("pill") or {}).get("text") or "")
        if m:
            desconto = int(m.group(1))
            break
    if not desconto and original > promocional > 0:
        desconto = round((original - promocional) / original * 100)

    return original, promocional, desconto, (preco.get("unit_description") or {}).get(
        "text", ""
    ).strip()


def extrair_ofertas_json(
    contexto: dict, vistos: set[str]
) -> tuple[list[Oferta], dict[str, int]]:
    recusas: dict[str, int] = {}
    ofertas: list[Oferta] = []
    prefixo = (contexto.get("polycardContext") or {}).get("url_prefix") or "https://"

    for item in contexto.get("items") or []:
        card = item.get("card") or {}
        comps = {c.get("type"): c for c in card.get("components") or []}
        meta = card.get("metadata") or {}

        titulo = ((comps.get("title") or {}).get("title") or {}).get("text") or ""
        if not titulo:
            continue

        motivo = filtrar_titulo(titulo)
        if motivo:
            recusas[motivo] = recusas.get(motivo, 0) + 1
            continue

        marca, motivo, de_onde = filtrar_marca(marca_do_card(comps), titulo)
        if motivo:
            recusas[motivo] = recusas.get(motivo, 0) + 1
            continue

        # marca veio do rótulo do ML: não precisa do "ml" no título
        if de_onde != "rotulo":
            motivo = filtrar_volume(titulo)
            if motivo:
                recusas[motivo] = recusas.get(motivo, 0) + 1
                continue

        url = meta.get("url") or ""
        if not url:
            recusas["sem link de produto"] = recusas.get("sem link de produto", 0) + 1
            continue
        if not url.startswith("http"):
            url = prefixo + url
        url = limpar_url(url)
        # sem URL de produto não há link de afiliado nem mensagem: os
        # patrocinados da busca vêm como pixel de anúncio e morrem aqui
        mlb_id = extrair_id(url) if url else ""
        if not mlb_id:
            recusas["sem link de produto"] = recusas.get("sem link de produto", 0) + 1
            continue

        # dedup por id E por título: o mesmo perfume aparece em anúncio
        # avulso e em catálogo, com ids diferentes — e o grupo veria duas vezes
        chave_titulo = "t:" + normalizar(titulo)
        if mlb_id in vistos or chave_titulo in vistos:
            continue
        vistos.update((mlb_id, chave_titulo))

        original, promocional, desconto, condicao = precos_do_card(
            (comps.get("price") or {}).get("price") or {}
        )
        motivo = filtrar_preco(original, promocional, desconto)
        if motivo:
            recusas[motivo] = recusas.get(motivo, 0) + 1
            continue

        piso = PRECO_MINIMO_FAMILIA.get(familia_da_marca(marca), 0.0)
        if piso and promocional < piso:
            motivo = f"preço suspeito para {familia_da_marca(marca)}"
            recusas[motivo] = recusas.get(motivo, 0) + 1
            continue

        avaliacao, vendidos = 0.0, ""
        review = (comps.get("review_compacted") or {}).get("review_compacted") or {}
        if review:
            m = re.search(r"([\d]+[.,][\d]+)", review.get("alt_text") or "")
            if m:
                avaliacao = float(m.group(1).replace(",", "."))
            m = re.search(r"([+\d][\w.]*)\s*vendidos", resolver_texto(review), re.I)
            if m:
                vendidos = m.group(1)

        ofertas.append(
            Oferta(
                mlb_id=mlb_id,
                nome=titulo,
                url=url,
                imagem=montar_imagem(card, contexto),
                preco_original=original,
                preco_promocional=promocional,
                desconto_pct=desconto,
                badge=badge_do_card(card),
                condicao=condicao,
                marca=marca,
                loja=loja_do_card(comps)[0],
                loja_oficial=loja_do_card(comps)[1],
                vendedor=resolver_texto(
                    (comps.get("seller") or {}).get("seller") or {}
                ),
                avaliacao=avaliacao,
                vendidos=vendidos,
            )
        )

    return ofertas, recusas


def total_de_paginas(contexto: dict, teto: int) -> int:
    """O ML diz quantas ofertas existem — não faz sentido varrer 50 páginas."""
    paginacao = contexto.get("paging") or {}
    total = int(paginacao.get("total") or 0)
    por_pagina = int(paginacao.get("limit") or 0)
    if total <= 0 or por_pagina <= 0:
        return teto
    return max(1, min(teto, -(-total // por_pagina)))


def _categoria() -> str:
    """Categoria do ML para o nicho ativo."""
    return nicho.ativo().config("mercadolivre").get("categoria", "")


# Critérios da Fonte em vigor nesta execução. Vazio = comportamento de
# sempre (termos do nicho). Preenchido = o usuário configurou a fonte na
# tela, e é ela quem manda.
CRITERIOS_DA_FONTE: dict = {}


def usar_criterios(criterios: dict) -> None:
    """Passa a coletar segundo o que o usuário pediu na tela."""
    global CRITERIOS_DA_FONTE
    CRITERIOS_DA_FONTE = criterios or {}


def _termos() -> list:
    if CRITERIOS_DA_FONTE.get("palavras_chave"):
        return list(CRITERIOS_DA_FONTE["palavras_chave"])
    return nicho.ativo().config("mercadolivre").get("termos", [])


def baixar_pagina(pagina: int) -> str:
    url = (
        "https://www.mercadolivre.com.br/ofertas?"
        + urllib.parse.urlencode(
            {"category": _categoria(), "page": pagina}
        )
    )
    return requisitar(
        url,
        headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "accept-encoding": "gzip, deflate",
            "user-agent": UA_CHROME,
        },
    )


# ══════════════════════════════════════════════════════════════════════
# FONTE 2 — A BUSCA (lista.mercadolivre.com.br)
# ══════════════════════════════════════════════════════════════════════
# É a fonte que o actor do Mercado Livre na Apify usa, e a razão de ele
# devolver Rabanne/Dior/Lancôme que a vitrine nunca mostra.
#
# Três diferenças em relação à vitrine, todas tratadas aqui:
#   1. exige sessão — sem cookie o ML serve `gz-account-verification-index`
#   2. o estado não vem em __NORDIC_RENDERING_CTX__, e sim em
#      `_n.ctx.s.q("0:{…}")` — JSON escapado dentro de uma string JS
#   3. esse JSON tem referências a variáveis JS (`"state":u`), então não dá
#      para json.loads() o payload inteiro
# Por (3), em vez de parsear tudo, recortamos cada objeto "polycard" com um
# scanner de chaves balanceadas. O card em si é JSON válido e tem exatamente
# a mesma forma da vitrine — daí extrair_ofertas_json() servir sem alteração.

RE_CHUNK_BUSCA = re.compile(r'_n\.ctx\.s\.q\("((?:[^"\\]|\\.)*)"\)', re.S)
RE_SCRIPT = re.compile(r"<script[^>]*>(.*?)</script>", re.S)
RE_POLYCARD = re.compile(r'"polycard"\s*:\s*(?=\{)')
RE_TOTAL_BUSCA = re.compile(r'"total":(\d+)')


def objeto_balanceado(texto: str, inicio: int) -> str:
    """Recorta o objeto JSON que começa em `inicio`, respeitando strings."""
    profundidade = 0
    em_string = escapado = False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if em_string:
            if escapado:
                escapado = False
            elif c == "\\":
                escapado = True
            elif c == '"':
                em_string = False
        elif c == '"':
            em_string = True
        elif c == "{":
            profundidade += 1
        elif c == "}":
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio : i + 1]
    return ""


def payload_da_busca(pagina_html: str) -> str:
    """O JSON (como texto) escondido na string JS da página de busca."""
    for m in RE_SCRIPT.finditer(pagina_html):
        corpo = m.group(1)
        if "polycard" not in corpo:
            continue
        for escapado in RE_CHUNK_BUSCA.findall(corpo):
            try:
                bruto = json.loads('"' + escapado + '"')
            except (json.JSONDecodeError, ValueError):
                continue
            if '"polycard"' in bruto:
                return bruto
    return ""


# Sinais de que o Mercado Livre respondeu com bloqueio em vez de resultado.
# Sem isto, a página de captcha vira "0 ofertas encontradas" — e o usuário
# passa horas mexendo nos critérios para consertar algo que não é dele.
SINAIS_DE_BLOQUEIO = (
    "abuse-captcha",
    "captcha/wall",
    "abuse-china-wall",
    "gz-account-verification",
)


class BuscaBloqueada(RuntimeError):
    """O Mercado Livre recusou a consulta (verificação anti-robô).

    Erro próprio porque a saída é diferente de qualquer outra falha: não
    adianta mexer nos critérios nem tentar de novo já — é preciso esperar,
    e às vezes renovar a sessão.
    """

    mensagem_usuario = (
        "O Mercado Livre bloqueou a busca temporariamente. "
        "Isso costuma passar sozinho em alguns minutos.")


def foi_bloqueada(pagina_html: str) -> bool:
    baixo = pagina_html[:20000].lower()
    return any(sinal in baixo for sinal in SINAIS_DE_BLOQUEIO)


def contexto_da_busca(pagina_html: str) -> dict | None:
    """Devolve os cards no mesmo formato que extrair_ofertas_json() espera."""
    if foi_bloqueada(pagina_html):
        raise BuscaBloqueada("resposta é a página de verificação do Mercado Livre")

    bruto = payload_da_busca(pagina_html)
    if not bruto:
        return None

    cards = []
    for m in RE_POLYCARD.finditer(bruto):
        texto = objeto_balanceado(bruto, m.end())
        if not texto:
            continue
        try:
            cards.append(json.loads(texto))
        except (json.JSONDecodeError, ValueError):
            continue
    if not cards:
        return None

    m_total = RE_TOTAL_BUSCA.search(bruto)
    return {
        "items": [{"card": c} for c in cards],
        "paging": {"total": int(m_total.group(1)) if m_total else len(cards)},
        "polycardContext": {
            "picture_template": (
                "https://http2.mlstatic.com/D_{square}_NP{2x}_{id}"
                "-{size}{sanitized_title}.webp"
            ),
            "picture_size_default": "AB",
            "url_prefix": "https://",
        },
    }


def baixar_busca(termo: str) -> str:
    # minúsculas obrigatório: "Asad-Elixir" devolve casca vazia (streaming),
    # "asad-elixir" devolve os cards. Levei um tempo para achar essa.
    url = "https://lista.mercadolivre.com.br/" + urllib.parse.quote(
        re.sub(r"\s+", "-", termo.strip().lower())
    )
    return requisitar(
        url,
        headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "accept-encoding": "gzip, deflate",
            "user-agent": UA_CHROME,
            "referer": "https://www.mercadolivre.com.br/",
            "cookie": cookie_ml(),
            **HEADERS_NAVEGADOR,
        },
    )


# ── galeria do produto (opcional) ────────────────────────────────────
RE_FIGURA_GALERIA = re.compile(
    r'<figure[^>]*class="ui-pdp-gallery__figure"[^>]*>.*?</figure>', re.S
)
RE_SRC_FIGURA = re.compile(r'(?:data-zoom|src)="(https://http2[^"]+)"')


def galeria_do_produto(url: str) -> list[str]:
    """Fotos da galeria da página do produto. Exige o cookie de sessão."""
    try:
        html = requisitar(
            url,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept-language": "pt-BR,pt;q=0.9",
                "accept-encoding": "gzip, deflate",
                "user-agent": UA_CHROME,
                "referer": "https://www.mercadolivre.com.br/",
                "cookie": cookie_ml(),
            },
        )
    except (HttpErro, RuntimeError):
        return []

    fotos: list[str] = []
    for figura in RE_FIGURA_GALERIA.findall(html):
        m = RE_SRC_FIGURA.search(figura)
        if not m:
            continue
        u = m.group(1).replace("-F.webp", "-O.webp").replace("-F.jpg", "-O.jpg")
        if u not in fotos:
            fotos.append(u)
    return fotos


def foto_para_envio(linha: sqlite3.Row) -> str:
    """A imagem que vai no WhatsApp, conforme FOTO_ESTRATEGIA."""
    if "clone_imagem" in linha.keys() and linha["clone_imagem"]:
        return linha["clone_imagem"]      # clone literal: a foto que o rival mandou
    padrao = linha["imagem"]
    if FOTO_ESTRATEGIA != "galeria" or FOTO_INDICE_GALERIA <= 0:
        return padrao
    if FOTO_SO_IMPORTADAS and linha["familia"] not in FAMILIAS_IMPORTADAS:
        return padrao
    fotos = galeria_do_produto(linha["url"])
    if len(fotos) > FOTO_INDICE_GALERIA:
        return fotos[FOTO_INDICE_GALERIA]
    return padrao



def _passa_nos_criterios(oferta) -> tuple:
    """Filtro do USUÁRIO (desconto, faixa de preço, exclusões).

    Roda depois da curadoria do nicho, que já derrubou o que não é oferta
    boa. São barreiras independentes de propósito: uma protege o grupo de
    produto ruim, a outra atende ao que este usuário quer ver.
    """
    if not CRITERIOS_DA_FONTE:
        return True, ""
    from nucleo import fonte_busca
    return fonte_busca.aceita(oferta, CRITERIOS_DA_FONTE)


def registrar(
    con: sqlite3.Connection, ofertas: list[Oferta], seco: bool
) -> tuple[int, int]:
    """Grava (ou só mostra) as ofertas. Devolve (novas, já conhecidas)."""
    novas = conhecidas = 0
    for o in ofertas:
        passa, _motivo = _passa_nos_criterios(o)
        if not passa:
            continue
        if seco:
            print(
                f"  {VERDE}{o.desconto_pct:>3}%{FIM} {o.nome[:66]}\n"
                f"       {CINZA}{reais(o.preco_original)} → {FIM}"
                f"{VERDE}{reais(o.preco_promocional)}"
                f"{(' ' + o.condicao) if o.condicao else ''}{FIM}"
                f"  {AZUL}{o.marca}{FIM}  {CINZA}{o.badge} · {o.mlb_id}{FIM}"
            )
            novas += 1
        elif salvar_oferta(con, o):
            novas += 1
        else:
            conhecidas += 1
    if not seco:
        con.commit()
    return novas, conhecidas


def somar(destino: dict[str, int], origem: dict[str, int]) -> None:
    for motivo, n in origem.items():
        destino[motivo] = destino.get(motivo, 0) + n


def varrer_vitrine(
    con: sqlite3.Connection,
    paginas: int,
    vistos: set[str],
    recusas_total: dict[str, int],
    seco: bool,
) -> tuple[int, int]:
    """FONTE 1 — /ofertas. Sem autenticação. É de onde vêm os badges
    OFERTA DO DIA e RELÂMPAGO, que a busca não tem."""
    info(f"fonte 1/2 · vitrine de ofertas · categoria {_categoria()}")
    novas = conhecidas = vazias_seguidas = pagina = 0

    while pagina < paginas:
        pagina += 1
        try:
            html_pagina = baixar_pagina(pagina)
        except (HttpErro, RuntimeError) as e:
            aviso(f"vitrine página {pagina}: {e}")
            break

        contexto = extrair_contexto(html_pagina)
        if contexto:
            ofertas, recusas = extrair_ofertas_json(contexto, vistos)
            if pagina == 1:
                paginas = min(paginas, total_de_paginas(contexto, paginas))
                total = (contexto.get("paging") or {}).get("total")
                info(f"  o ML declara {total} oferta(s) na vitrine → {paginas} página(s)")
        elif 'class="andes-card poly-card' in html_pagina:
            # o estado embutido sumiu — cai no regex de HTML do fluxo antigo
            aviso(f"vitrine página {pagina}: sem estado embutido, usando o parser de HTML")
            ofertas, recusas = extrair_ofertas(html_pagina, vistos)
        else:
            aviso(
                "vitrine: nem JSON nem cards — o layout do ML mudou"
                if pagina == 1 else f"vitrine página {pagina}: vazia, fim do catálogo"
            )
            break

        somar(recusas_total, recusas)
        if not ofertas:
            vazias_seguidas += 1
            if vazias_seguidas >= PAGINAS_VAZIAS_ATE_PARAR:
                break
        else:
            vazias_seguidas = 0

        n, c = registrar(con, ofertas, seco)
        novas, conhecidas = novas + n, conhecidas + c
        info(f"  página {pagina}: {len(ofertas)} aprovada(s)")
        if pagina < paginas:
            time.sleep(random.uniform(*PAUSA_ENTRE_PAGINAS))

    return novas, conhecidas


def varrer_busca(
    con: sqlite3.Connection,
    vistos: set[str],
    recusas_total: dict[str, int],
    seco: bool,
) -> tuple[int, int]:
    """FONTE 2 — a busca. É de onde saem Rabanne, Dior, Natura e Lattafa."""
    termos = _termos()
    if not termos:
        return 0, 0
    if not cookie_ml():
        aviso("busca exige o cookie de sessão — pulando (a vitrine já rodou)")
        return 0, 0

    info(f"fonte 2/2 · busca · {len(termos)} termo(s)")
    novas = conhecidas = 0

    for i, termo in enumerate(termos):
        # o ML devolve a tela de verificação de vez em quando; uma segunda
        # tentativa mais lenta costuma passar
        contexto = None
        for tentativa in (1, 2):
            try:
                contexto = contexto_da_busca(baixar_busca(termo))
            except (HttpErro, RuntimeError) as e:
                aviso(f"  busca {termo!r}: {e}")
                break
            if contexto:
                break
            if tentativa == 1:
                time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS) * 2)

        if not contexto:
            aviso(
                f"  busca {termo!r}: sem resultados — "
                "verificação do ML ou sessão expirada"
            )
            time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS))
            continue

        ofertas, recusas = extrair_ofertas_json(contexto, vistos)
        somar(recusas_total, recusas)
        n, c = registrar(con, ofertas, seco)
        novas, conhecidas = novas + n, conhecidas + c
        total = (contexto.get("paging") or {}).get("total")
        info(
            f"  {termo!r}: {len(contexto['items'])} card(s) de {total} → "
            f"{len(ofertas)} aprovada(s)"
        )
        if i < len(termos) - 1:
            time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS))

    return novas, conhecidas


def bloco1_buscar(con: sqlite3.Connection, paginas: int, seco: bool = False) -> int:
    info("BLOCO 1 — coletando ofertas")
    vistos: set[str] = set()          # dedup entre as duas fontes
    recusas_total: dict[str, int] = {}

    nv, cv = varrer_vitrine(con, paginas, vistos, recusas_total, seco)
    nb, cb = varrer_busca(con, vistos, recusas_total, seco)

    if recusas_total:
        resumo = " · ".join(
            f"{n} {m}" for m, n in sorted(recusas_total.items(), key=lambda x: -x[1])
        )
        info(f"recusados: {resumo}")
    ok(
        f"BLOCO 1 — {nv + nb} nova(s), {cv + cb} já conhecida(s) "
        f"(vitrine {nv} · busca {nb})"
    )
    return nv + nb


# ══════════════════════════════════════════════════════════════════════
# BLOCO 2 — LINK DE AFILIADO (sessão da sua própria conta)
# ══════════════════════════════════════════════════════════════════════
ML_CREATE_LINK = (
    "https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink"
)
RE_MCLICS = re.compile(r"^https?://click\d\.mercadolivre\.com\.br/mclics/.*url=", re.I)


def cookie_ml() -> str:
    do_env = os.environ.get("ML_COOKIE", "").strip()
    if do_env:
        return do_env
    if os.path.exists(ARQUIVO_COOKIE):
        with open(ARQUIVO_COOKIE, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def limpar_url(bruta: str) -> str:
    """Porte do node 'Code: Limpar URL do Produto', com a ordem corrigida.

    O fluxo do n8n cortava a query ANTES de procurar o `url=` do mclics —
    e o destino real mora justamente na query. Aquele replace nunca rodava.
    Isso não aparecia na vitrine, mas na busca os patrocinados vêm assim.
    """
    limpa = bruta.strip()
    m = RE_MCLICS.search(limpa)
    if m:
        destino = urllib.parse.unquote(limpa[m.end():])
        if not destino:
            return ""           # pixel de anúncio, sem produto por trás
        limpa = destino
    elif "/mclics/" in limpa:
        return ""               # mclics sem url= — nada a recuperar
    return limpa.split("#")[0].split("?")[0]


def gerar_links(urls: list[str]) -> dict[str, str]:
    """{url_original: short_url}. Erra alto se o cookie expirou."""
    cookie = cookie_ml()
    if not cookie:
        raise RuntimeError(
            f"cookie do Mercado Livre não encontrado em {ARQUIVO_COOKIE}.\n"
            "  F12 → Network → createLink → copie o header Cookie inteiro."
        )
    if not ML_AFFILIATE_TAG:
        raise RuntimeError("defina ML_AFFILIATE_TAG no .env (sua tag de afiliado).")

    try:
        resposta = requisitar_json(
            ML_CREATE_LINK,
            metodo="POST",
            corpo=json.dumps({"tag": ML_AFFILIATE_TAG, "urls": urls}).encode("utf-8"),
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "content-type": "application/json",
                "origin": "https://www.mercadolivre.com.br",
                "referer": "https://www.mercadolivre.com.br/afiliados/linkbuilder#hub",
                "user-agent": UA_CHROME,
                "cookie": cookie,
            },
        )
    except HttpErro as e:
        if e.codigo in (401, 403):
            raise RuntimeError(
                f"sessão do Mercado Livre expirada (HTTP {e.codigo}).\n"
                f"  Atualize o cookie em {ARQUIVO_COOKIE} — ele dura ~30 dias."
            ) from e
        raise

    itens = resposta.get("urls") or []
    saida: dict[str, str] = {}
    for i, item in enumerate(itens):
        if not isinstance(item, dict):
            continue
        curto = item.get("short_url") or ""
        original = item.get("original_url") or (urls[i] if i < len(urls) else "")
        if curto and original:
            saida[original] = curto
    return saida


def bloco2_links(con: sqlite3.Connection, lote: int = 20) -> int:
    pendentes = con.execute(
        "SELECT mlb_id, url FROM ofertas "
        "WHERE link_afiliado = '' AND status_envio NOT IN ('ENVIADO', 'ERRO') "
        "AND mlb_id LIKE 'MLB%'"  # Shopee chega com offerLink pronto; ERRO já desistiu
    ).fetchall()
    if not pendentes:
        return 0

    info(f"BLOCO 2 — gerando link de afiliado para {len(pendentes)} oferta(s)")
    gerados = 0
    for i in range(0, len(pendentes), lote):
        fatia = pendentes[i : i + lote]
        mapa = {r["mlb_id"]: limpar_url(r["url"]) for r in fatia}
        try:
            links = gerar_links(list(mapa.values()))
        except RuntimeError as e:
            erro(f"BLOCO 2: {e}")
            break

        ts = agora().isoformat(timespec="seconds")
        for mlb_id, url_limpa in mapa.items():
            curto = links.get(url_limpa)
            if not curto:
                # a API recusa alguns anúncios silenciosamente (inelegíveis
                # para o programa). 5 recusas = desiste, sem retry eterno.
                con.execute(
                    "UPDATE ofertas SET tentativas = tentativas + 1 WHERE mlb_id=?",
                    (mlb_id,))
                n_rec = con.execute(
                    "SELECT tentativas FROM ofertas WHERE mlb_id=?",
                    (mlb_id,)).fetchone()["tentativas"]
                if n_rec >= 5:
                    con.execute(
                        "UPDATE ofertas SET status_envio='ERRO', "
                        "erro='afiliado: anúncio recusado pelo createLink', "
                        "atualizado_em=? WHERE mlb_id=?", (ts, mlb_id))
                    aviso(f"  {mlb_id}: recusado {n_rec}x pelo createLink — desisto")
                continue
            con.execute(
                "UPDATE ofertas SET link_afiliado = ?, atualizado_em = ? WHERE mlb_id = ?",
                (curto, ts, mlb_id),
            )
            gerados += 1
        con.commit()
        if i + lote < len(pendentes):
            time.sleep(1.5)

    ok(f"BLOCO 2 — {gerados} link(s) de afiliado gerado(s)")
    return gerados


