"""
CLONADOR — monitor da concorrência
==================================

Lê os grupos rivais em que a sua linha já está, descobre QUAL anúncio o
concorrente divulgou e joga na sua fila com o seu link de afiliado.

Roda dentro do mesmo processo do buscador de propósito: quem publica é um
só, então fila, ritmo e trava têm de ser compartilhados. Dois processos
mandando no mesmo grupo quebrariam a cadência e a cota do dia.
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
from mercadolivre.config import *  # noqa: F401,F403
from nucleo.comum import (
    AZUL, CINZA, FIM, VERDE, VERMELHO, AMARELO, clonador_cfg,
    mensagens_do_grupo, uazapi_configurado,
)
from mercadolivre.buscador import (
    RE_ID_ANUNCIO, baixar_busca, contexto_da_busca, extrair_ofertas_json,
    filtrar_marca, normalizar, salvar_oferta,
)

# BLOCO 4 — MONITOR DA CONCORRÊNCIA
# ══════════════════════════════════════════════════════════════════════
# Lê os grupos de promoção em que a sua linha já está, identifica o PRODUTO
# que o concorrente anunciou e republica no seu grupo com o SEU link.
#
# O que ele NÃO faz, de propósito: copiar a foto e o texto deles. A foto de
# vitrine que eles produzem é trabalho autoral — republicar aquilo é usar
# criação de terceiro. O agente pega só a identidade do produto (que é fato
# público no Mercado Livre) e remonta tudo com dado do ML e o seu formato.
# Se você quiser mesmo repassar a mídia original, é mudar CLONE_COPIAR_MIDIA,
# mas aí a decisão é sua.

CLONE_ATIVO = True
CLONE_GRUPOS = [
    "120363406025827790@g.us",     # #101 MAENO PROMOS | PERFUMES
]
CLONE_INTERVALO_SEG = 180          # de quanto em quanto tempo olha os grupos
CLONE_JANELA_MIN = 90              # ignora mensagem mais velha que isso
CLONE_COPIAR_MIDIA = False         # True republica a foto do concorrente
CLONE_TOLERANCIA_PRECO = 0.12      # 12% de diferença ainda casa o produto

# Linha em negrito no meio da mensagem deles = nome do produto.
RE_CLONE_NOME = re.compile(r"\*([^*\n]{8,120})\*")
RE_CLONE_PRECO = re.compile(r"R\$\s*([\d.]+,\d{2}|[\d.]+)", re.I)
RE_CLONE_LINK = re.compile(r"https?://(?:meli\.la|mercadolivre\.com\.br)/\S+", re.I)
# palavras que denunciam que o negrito não é o nome do produto
RE_CLONE_NAO_NOME = re.compile(
    r"^(de|por|loja|link|corre|aproveit|promo|oferta|r\$)", re.I
)


def preco_br(texto: str) -> float:
    """'1.234,56' → 1234.56 · '319,00' → 319.0"""
    limpo = texto.strip().replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def ler_anuncio_rival(texto: str) -> dict | None:
    """Extrai produto e preços da mensagem do concorrente."""
    if not texto or not RE_CLONE_LINK.search(texto):
        return None

    nomes = [
        n.strip()
        for n in RE_CLONE_NOME.findall(texto)
        if not RE_CLONE_NAO_NOME.match(n.strip()) and not RE_CLONE_PRECO.search(n)
    ]
    if not nomes:
        return None

    precos = [preco_br(p) for p in RE_CLONE_PRECO.findall(texto)]
    precos = [p for p in precos if p > 0]
    if not precos:
        return None

    m_link = RE_CLONE_LINK.search(texto)
    return {
        "nome": max(nomes, key=len),
        "preco": min(precos),          # o "por" é sempre o menor
        "preco_de": max(precos) if len(precos) > 1 else 0.0,
        "link": m_link.group(0) if m_link else "",
    }


RE_SO_VOLUME = re.compile(r"^\d{1,4}\s*ml$", re.I)


RE_OG_TITULO = re.compile(r'property="og:title" content="([^"]+)"')
RE_OG_IMAGEM = re.compile(r'(?:property="og:image"|name="image") content="([^"]+)"')
RE_ID_FOTO = re.compile(r"D_\w*?NP_(?:2X_)?([\w\-]+?)-[A-Z]{1,2}\.(?:webp|jpg)")


def abrir_link_rival(link: str, preco_msg: float = 0.0) -> dict:
    """Resolve o meli.la do rival e lê o anúncio exato pelas meta tags.

    O link dele cai na vitrine de afiliado (/social/...), não no produto —
    mas o `ref` faz o ML montar a página COM as meta tags daquele anúncio:
    og:title traz o título integral do ML e og:image a foto do anúncio.
    O id dessa foto é o que permite achar o anúncio EXATO, e não só um
    perfume de mesmo nome de outro vendedor.
    """
    try:
        html = requisitar(
            link,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept-language": "pt-BR,pt;q=0.9",
                "accept-encoding": "gzip, deflate",
                "user-agent": UA_CHROME,
            },
        )
    except (HttpErro, RuntimeError):
        return {}

    m_t = RE_OG_TITULO.search(html)
    m_i = RE_OG_IMAGEM.search(html)
    id_foto = ""
    if m_i:
        m_p = RE_ID_FOTO.search(m_i.group(1))
        id_foto = m_p.group(1) if m_p else ""
    titulo = m_t.group(1).strip() if m_t else ""
    url_bruta, prova = anuncio_bruto_na_vitrine(html, titulo, id_foto, preco_msg)
    return {
        "titulo": titulo,
        "id_foto": id_foto,
        "imagem": m_i.group(1) if m_i else "",
        "url_bruta": url_bruta,
        "prova": prova,
    }


# O primeiro link COMPLETO de anúncio no HTML da vitrine é o produto que o
# `ref` referenciou — o "link bruto" que aparece no inspecionar. Duas formas:
#   catálogo:  mercadolivre.com.br/<slug>/p/MLB123456
#   avulso:    produto.mercadolivre.com.br/MLB-1234567890-<slug>
RE_BRUTO_CATALOGO = re.compile(
    r"https://www\.mercadolivre\.com\.br/[\w\-]+/p/MLB\d+[^\"\s']*")
RE_BRUTO_AVULSO = re.compile(
    r"https://produto\.mercadolivre\.com\.br/MLB-\d+[^\"\s']*")


def _tokens_uteis(texto: str) -> set:
    return {t for t in normalizar(texto).split() if len(t) > 2 and not t.isdigit()}


# palavras que aparecem em QUALQUER anúncio de perfumaria — não identificam
GENERICAS = {
    "perfume", "desodorante", "colonia", "masculino", "feminino", "unissex",
    "parfum", "edp", "edt", "deo", "eau", "original", "importado", "arabe",
    "spray", "kit", "body", "splash", "para", "com", "the", "pour", "homme",
    "femme", "100ml", "105ml", "90ml", "95ml", "80ml", "50ml", "200ml", "125ml",
}


def _distintivos(texto: str) -> set:
    return _tokens_uteis(texto) - GENERICAS


def anuncio_bruto_na_vitrine(html: str, titulo: str, id_foto: str = "",
                             preco_msg: float = 0.0) -> tuple[str, str]:
    """(URL crua, prova) do anúncio referenciado na vitrine do rival.

    A vitrine é a prateleira inteira dele — posição NÃO identifica o
    produto (já saiu link de Gaby Elysees numa mensagem do Salvo).
    Certificação por provas independentes; na dúvida, ("", motivo) e o
    fluxo cai no plano B (busca por foto exata). Nunca chuta.

    1ª prova (FOTO): o og:image da vitrine carrega o ID único da foto
       do produto referenciado; o card que contém esse ID é o produto.
    2ª prova (SLUG): o ML gera o slug a partir do título do anúncio —
       casamento forte slug×og:title identifica; o preço do card não
       pode gritar contra o preço da mensagem do rival.
    """
    candidatos = []
    for rx in (RE_BRUTO_CATALOGO, RE_BRUTO_AVULSO):
        for m in rx.finditer(html):
            candidatos.append((m.start(), m.group(0).replace("&amp;", "&")))
    if not candidatos:
        return "", "vitrine sem link de anúncio"
    candidatos.sort()
    from mercadolivre.buscador import limpar_url

    # ── 1ª prova: o candidato MAIS PRÓXIMO do ID da foto referenciada
    # (proximidade, não "está na janela": cards vizinhos vazam na janela)
    if id_foto:
        ocorrencias = [m.start() for m in re.finditer(re.escape(id_foto), html)]
        if ocorrencias:
            dist, url_foto = min(
                (min(abs(pos - o) for o in ocorrencias), url)
                for pos, url in candidatos)
            if dist <= 1500:
                return limpar_url(url_foto), "foto"

    # ── 2ª prova: slug × título (+ preço do card não pode gritar)
    esperado = _tokens_uteis(titulo)
    if not esperado:
        return "", "vitrine sem og:title"
    pontuados = []
    for pos, url in candidatos:
        slug = re.sub(r"https://[^/]+/", "", url.split("?")[0])
        casou = len(esperado & _tokens_uteis(slug.replace("-", " ")))
        pontuados.append((casou / len(esperado), -pos, pos, url))
    pontuados.sort(reverse=True)
    escore, _, pos, url = pontuados[0]
    if escore < 0.5:
        return "", f"slug não casa (melhor escore {escore:.0%})"
    # genéricas carregam escore ("desodorante colônia 100ml" casa com tudo):
    # o slug PRECISA conter um token distintivo do título ("clash", "asad"…)
    marcantes = _distintivos(titulo)
    slug_esc = _tokens_uteis(
        re.sub(r"https://[^/]+/", "", url.split("?")[0]).replace("-", " "))
    if marcantes and not (marcantes & slug_esc):
        return "", "slug sem token distintivo do título"
    if preco_msg > 0:
        card = html[max(0, pos - 1500): pos + 1500]
        precos = [preco_br(p) for p in RE_CLONE_PRECO.findall(card)]
        precos = [p for p in precos if p > 0]
        if precos and not any(abs(p - preco_msg) / preco_msg <= 0.40 for p in precos):
            return "", f"preço do card grita ({min(precos):.0f} vs {preco_msg:.0f})"
    return limpar_url(url), "slug+preço" if preco_msg else "slug"


def baixar_midia_rival(mid: str) -> str:
    """A foto EXATA que o rival mandou, hospedada pela uazapi ('' se falhar)."""
    try:
        dados = requisitar_json(
            UAZAPI_URL + "/message/download",
            metodo="POST",
            corpo=json.dumps({"id": mid}).encode("utf-8"),
            headers={"Content-Type": "application/json", "token": UAZAPI_TOKEN},
        )
        return dados.get("fileURL") or ""
    except (HttpErro, RuntimeError):
        return ""


def oferta_do_clone(anuncio: dict, url_bruta: str, titulo: str,
                    imagem: str = "") -> Oferta | None:
    """Oferta montada direto da mensagem + URL exata — sem buscar no ML."""
    m = RE_ID_ANUNCIO.search(url_bruta.replace("/p/MLB", "/p/MLB-"))
    if not m:
        return None
    nome = titulo or anuncio["nome"]
    marca, _, _ = filtrar_marca("", nome)
    de, por = anuncio.get("preco_de") or 0.0, anuncio["preco"]
    return Oferta(
        mlb_id=f"MLB{m.group(1)}",
        nome=nome,
        url=url_bruta,
        imagem=imagem,
        preco_original=de if de > por else 0.0,
        preco_promocional=por,
        desconto_pct=round((1 - por / de) * 100) if de > por else 0,
        marca=marca,
    )


def consultas_do_nome(nome: str) -> list[str]:
    """Consultas em cascata, da mais rica para a mais curta.

    A busca do ML devolve casca vazia em parte das consultas longas, e isso
    é intermitente. Em vez de insistir na mesma frase, encurtamos: 3 palavras,
    depois 2. O volume ("100ml") sai — não ajuda a achar e atrapalha.
    """
    palavras = [
        p for p in re.split(r"[\s\-]+", nome)
        if p
        and normalizar(p) not in ("perfume", "de", "do", "da", "para", "e", "edp", "edt")
        and not RE_SO_VOLUME.match(p.strip())
    ]
    saidas: list[str] = []
    for quantas in (3, 2):
        consulta = " ".join(palavras[:quantas]).strip()
        if consulta and consulta not in saidas:
            saidas.append(consulta)
    return saidas


def achar_no_ml(
    nome: str, preco_alvo: float, id_foto: str = ""
) -> tuple[Oferta | None, str]:
    """Acha no ML o produto que o concorrente anunciou.

    Casa por semelhança de título E proximidade de preço — só o título erra
    entre versões de 50ml e 100ml do mesmo perfume.
    """
    import difflib

    contexto = None
    for i, consulta in enumerate(consultas_do_nome(nome)):
        try:
            contexto = contexto_da_busca(baixar_busca(consulta))
        except (HttpErro, RuntimeError):
            return None, "erro de rede"
        if contexto:
            break
        if i == 0:
            time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS))
    if not contexto:
        return None, "busca sem resultado"

    # 1º: o MESMO anúncio, pelo id da foto. É definitivo — mesma foto,
    # mesmo anúncio, mesmo vendedor que o rival divulgou.
    if id_foto:
        for item in contexto.get("items") or []:
            fotos = ((item.get("card") or {}).get("pictures") or {}).get("pictures") or []
            if fotos and fotos[0].get("id") == id_foto:
                exatas, _ = extrair_ofertas_json(
                    {**contexto, "items": [item]}, set()
                )
                if exatas:
                    return exatas[0], "anúncio exato (mesma foto)"

    ofertas, _ = extrair_ofertas_json(contexto, set())
    alvo = normalizar(nome)
    melhor, melhor_nota = None, 0.0
    for o in ofertas:
        semelhanca = difflib.SequenceMatcher(None, alvo, normalizar(o.nome)).ratio()
        if preco_alvo and o.preco_promocional:
            desvio = abs(o.preco_promocional - preco_alvo) / preco_alvo
            if desvio > CLONE_TOLERANCIA_PRECO:
                continue
            nota = semelhanca * (1 - desvio)
        else:
            nota = semelhanca * 0.5
        if nota > melhor_nota:
            melhor, melhor_nota = o, nota

    if melhor_nota >= 0.45:
        return melhor, f"mesmo perfume, outro anúncio (nota {melhor_nota:.2f})"
    return None, "nenhum candidato convincente"


def bloco4_clonar(con: sqlite3.Connection, seco: bool = False) -> int:
    """Olha os grupos rivais e traz para a sua fila o que eles anunciaram."""
    cfg = clonador_cfg(con)
    if not cfg["ativo"] or not cfg["grupos"]:
        return 0
    if not uazapi_configurado():
        aviso("BLOCO 4 — uazapi não configurado")
        return 0

    # só fala quando tem novidade — a cada 3min isto poluía o log e a
    # página Logs do painel (2 linhas por varredura vazia)
    corte_ms = (agora() - timedelta(minutes=cfg['janela_min'])).timestamp() * 1000
    novas = 0

    for jid in cfg['grupos']:
        chave = f"clone_visto3_{jid}"   # v3: reprocessa a janela no deploy do re-clone
        ja_visto = set(filter(None, ler_estado(con, chave).split(",")))
        try:
            mensagens = mensagens_do_grupo(jid)
        except (HttpErro, RuntimeError) as e:
            aviso(f"  {jid}: {e}")
            continue

        vistos_agora: list[str] = []
        for m in mensagens:
            mid = str(m.get("messageid") or "")
            vistos_agora.append(mid)
            if not mid or mid in ja_visto or m.get("fromMe"):
                continue
            if float(m.get("messageTimestamp") or 0) < corte_ms:
                continue

            texto = m.get("text") or ""
            anuncio = ler_anuncio_rival(texto)
            if not anuncio:
                continue

            # o link dele leva à vitrine, e a vitrine entrega o link BRUTO
            # do anúncio exato — clona direto, sem procurar no ML
            meta = (abrir_link_rival(anuncio["link"], anuncio["preco"])
                    if anuncio.get("link") else {})
            # pré-condição: o og:title tem que bater com o nome que ELE
            # escreveu — senão o próprio ref resolveu outro produto
            nome_msg = _tokens_uteis(anuncio["nome"])
            og_ok = bool(nome_msg) and meta.get("titulo") and (
                len(nome_msg & _tokens_uteis(meta["titulo"])) / len(nome_msg) >= 0.5)
            oferta, como = None, ""
            if meta.get("url_bruta") and og_ok:
                oferta = oferta_do_clone(anuncio, meta["url_bruta"],
                                         meta.get("titulo", ""), meta.get("imagem", ""))
                como = f"anúncio bruto (prova: {meta.get('prova', '?')})"
            if not oferta:
                if meta.get("url_bruta") and not og_ok:
                    info(f"  og:title não bate com a mensagem — plano B: "
                         f"{anuncio['nome'][:36]}")
                elif meta.get("prova"):
                    info(f"  bruto reprovado ({meta['prova']}) — plano B: "
                         f"{anuncio['nome'][:36]}")
                busca_por = (meta.get("titulo") if og_ok else "") or anuncio["nome"]
                oferta, como = achar_no_ml(
                    busca_por, anuncio["preco"], meta.get("id_foto", "")
                )
            if not oferta:
                info(f"  não achei no ML: {anuncio['nome'][:44]} — {como}")
                continue
            info(f"  {como}: {oferta.nome[:48]}")

            # NÃO refiltrar por marca aqui: extrair_ofertas_json já aprovou
            # usando o rótulo de marca do ML. Refiltrar só pelo título
            # derrubava produto bom, porque o rival escreve "Malbec
            # Tradicional 100ml" sem dizer que é O Boticário.

            if seco:
                print(
                    f"  {VERDE}CLONE{FIM} [{oferta.marca}] {oferta.nome[:48]}\n"
                    f"        rival R$ {anuncio['preco']:.2f} · "
                    f"ML R$ {oferta.preco_promocional:.2f} (-{oferta.desconto_pct}%)"
                )
                novas += 1
                continue

            if salvar_oferta(con, oferta):
                clone_texto = RE_CLONE_LINK.sub("{link}", texto)
                clone_imagem = (baixar_midia_rival(mid)
                                if "Image" in str(m.get("messageType", "")) else "")
                con.execute(
                    "UPDATE ofertas SET origem='clone', rival_nome=?, "
                    "rival_preco=?, rival_link=?, clone_texto=?, "
                    "clone_imagem=? WHERE mlb_id=?",
                    (anuncio["nome"], anuncio["preco"], anuncio.get("link", ""),
                     clone_texto, clone_imagem, oferta.mlb_id),
                )
                novas += 1
                ok(
                    f"  clonado: [{oferta.marca}] {oferta.nome[:44]} "
                    f"(-{oferta.desconto_pct}%)"
                )
            else:
                # produto já existia (a busca achou antes do rival postar).
                # Se ainda não saiu no grupo, o clone ASSUME a oferta: vira
                # origem='clone' com a mensagem literal — senão o modo
                # espelho a ignoraria e o espelho ficaria mudo.
                ex = con.execute(
                    "SELECT status_envio, enviado_em FROM ofertas WHERE mlb_id=?",
                    (oferta.mlb_id,)).fetchone()
                recente = False
                if ex and ex["status_envio"] == "ENVIADO" and ex["enviado_em"]:
                    idade_h = (agora() - datetime.fromisoformat(
                        ex["enviado_em"])).total_seconds() / 3600
                    recente = idade_h < cfg.get("reclonar_apos_horas", 20)
                if ex and (ex["status_envio"] == "PENDENTE"
                           or (ex["status_envio"] == "ENVIADO" and not recente)):
                    clone_texto = RE_CLONE_LINK.sub("{link}", texto)
                    clone_imagem = (baixar_midia_rival(mid)
                                    if "Image" in str(m.get("messageType", "")) else "")
                    ts = agora().isoformat(timespec="seconds")
                    con.execute(
                        "UPDATE ofertas SET origem='clone', rival_nome=?, "
                        "rival_preco=?, rival_link=?, clone_texto=?, "
                        "clone_imagem=?, status_envio='PENDENTE', tentativas=0, "
                        "proxima_tentativa=NULL, erro='', atualizado_em=? "
                        "WHERE mlb_id=?",
                        (anuncio["nome"], anuncio["preco"], anuncio.get("link", ""),
                         clone_texto, clone_imagem, ts, oferta.mlb_id))
                    # libera a trava de entrega para a republicação legítima
                    con.execute("DELETE FROM entregas WHERE mlb_id=? AND perfil=?",
                                (oferta.mlb_id, PERFIL_ATIVO))
                    novas += 1
                    ok(f"  clone assumiu: {oferta.nome[:44]}")
                else:
                    info(f"  rival repostou envio recente — pulado: {oferta.nome[:36]}")

        if not seco:
            con.commit()
            gravar_estado(con, chave, ",".join(vistos_agora[:60]))

    if novas:
        ok(f"BLOCO 4 — {novas} oferta(s) do rival na fila")
    return novas
