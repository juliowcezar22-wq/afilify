"""
BUSCADOR DA SHOPEE

API oficial de afiliados (GraphQL, assinatura SHA256). Bem mais simples que
o Mercado Livre: sem scraping, sem cookie de sessão, sem gerar link — o
`offerLink` já volta com o seu código de afiliado.

A dificuldade aqui é outra: o catálogo é cheio de falsificação. Por isso o
filtro de loja oficial (shopee/config.py) é o coração deste módulo.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import time

from nucleo.comum import (
    DESCONTO_MINIMO, VOLUME_MINIMO_ML,
    HttpErro, Oferta, agora, aviso, erro, familia_da_marca, filtrar_marca,
    filtrar_preco, filtrar_titulo, filtrar_volume, info, normalizar, ok,
    requisitar, salvar_oferta,
)
from nucleo import nicho
from shopee.config import (
    ITENS_POR_PAGINA, NOTA_MINIMA, ORDENACAO, PAGINAS_POR_TERMO,
    PAUSA_ENTRE_BUSCAS, SHOPEE_APP_ID, SHOPEE_ENDPOINT, SHOPEE_SECRET,
    SHOP_TYPE_OFICIAL, SOMENTE_LOJA_OFICIAL, TERMOS_BUSCA, VENDAS_MINIMAS,
)

BUSCA = """
query($palavra: String, $limite: Int, $pagina: Int, $ordem: Int) {
  productOfferV2(keyword: $palavra, limit: $limite, page: $pagina, sortType: $ordem) {
    nodes {
      itemId shopId productName productLink offerLink imageUrl
      price priceMin priceMax priceDiscountRate
      sales ratingStar commissionRate shopName shopType
    }
    pageInfo { hasNextPage }
  }
}
"""

DICAS_ERRO = {
    10020: "assinatura inválida — confira SHOPEE_APP_ID e SHOPEE_SECRET no .env",
    10030: "rate limit — espere um pouco",
    10035: "sua conta ainda não tem acesso à Open API",
    11001: "parâmetros inválidos",
}


def chamar(query: str, variaveis: dict | None = None) -> dict:
    """GraphQL com a assinatura SHA256 que a Shopee exige."""
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        raise RuntimeError(
            "SHOPEE_APP_ID / SHOPEE_SECRET ausentes no .env.\n"
            "  Pegue em affiliate.shopee.com.br → Open API"
        )

    corpo = json.dumps(
        {"query": query, "variables": variaveis or {}}, separators=(",", ":")
    )
    ts = int(time.time())
    assinatura = hashlib.sha256(
        f"{SHOPEE_APP_ID}{ts}{corpo}{SHOPEE_SECRET}".encode()
    ).hexdigest()

    texto = requisitar(
        SHOPEE_ENDPOINT,
        metodo="POST",
        corpo=corpo.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": (
                f"SHA256 Credential={SHOPEE_APP_ID}, "
                f"Timestamp={ts}, Signature={assinatura}"
            ),
        },
    )
    resposta = json.loads(texto)

    if resposta.get("errors"):
        e = resposta["errors"][0]
        ext = e.get("extensions") or {}
        codigo = ext.get("code")
        msg = ext.get("message") or e.get("message") or "erro desconhecido"
        raise RuntimeError(f"Shopee [{codigo}] {msg}. {DICAS_ERRO.get(codigo, '')}")

    return resposta.get("data") or {}


def loja_confiavel(no: dict) -> tuple[bool, str]:
    """A defesa contra réplica. Devolve (aceita, motivo_da_recusa)."""
    tipos = no.get("shopType") or []
    oficial = SHOP_TYPE_OFICIAL in tipos
    if SOMENTE_LOJA_OFICIAL:
        return (True, "") if oficial else (False, "loja não oficial")

    nota = float(no.get("ratingStar") or 0)
    vendas = int(no.get("sales") or 0)
    if not oficial and nota and nota < NOTA_MINIMA:
        return False, f"nota < {NOTA_MINIMA}"
    if not oficial and vendas < VENDAS_MINIMAS:
        return False, f"menos de {VENDAS_MINIMAS} vendas"
    return True, ""


def para_oferta(no: dict) -> Oferta:
    """Nó da API → a mesma Oferta que o agente do ML usa."""
    promocional = float(no.get("price") or no.get("priceMin") or 0)
    taxa = float(no.get("priceDiscountRate") or 0)
    # a Shopee dá a taxa, não o preço cheio: reconstrói o "de"
    original = round(promocional / (1 - taxa / 100), 2) if 0 < taxa < 100 else 0.0

    oficial = SHOP_TYPE_OFICIAL in (no.get("shopType") or [])
    nome = no.get("productName") or ""
    marca, _, _ = filtrar_marca("", nome)

    return Oferta(
        mlb_id=f"SHP{no.get('itemId')}",       # prefixo evita colidir com MLB
        nome=nome,
        url=no.get("productLink") or "",
        imagem=no.get("imageUrl") or "",
        preco_original=original,
        preco_promocional=promocional,
        desconto_pct=round(taxa),
        badge="PROMOÇÃO GERAL",
        marca=marca,
        loja=(no.get("shopName") or "").strip(),
        loja_oficial=oficial,
        vendedor=(no.get("shopName") or "").strip(),
        avaliacao=float(no.get("ratingStar") or 0),
        vendidos=str(no.get("sales") or ""),
        link_afiliado=no.get("offerLink") or "",   # já vem com a sua tag
    )


def extrair_ofertas(nos: list[dict], vistos: set[str]) -> tuple[list[Oferta], dict]:
    recusas: dict[str, int] = {}

    def recusar(motivo: str) -> None:
        recusas[motivo] = recusas.get(motivo, 0) + 1

    ofertas: list[Oferta] = []
    for no in nos:
        nome = no.get("productName") or ""
        if not nome:
            continue

        motivo = filtrar_titulo(nome)
        if motivo:
            recusar(motivo)
            continue

        marca, motivo, de_onde = filtrar_marca("", nome)   # a Shopee não rotula marca
        if motivo:
            recusar(motivo)
            continue

        motivo = filtrar_volume(nome)
        if motivo:
            recusar(motivo)
            continue

        aceita, motivo = loja_confiavel(no)
        if not aceita:
            recusar(motivo)
            continue

        o = para_oferta(no)
        if not o.link_afiliado:
            recusar("sem link de afiliado")
            continue

        motivo = filtrar_preco(o.preco_original, o.preco_promocional, o.desconto_pct)
        if motivo:
            recusar(motivo)
            continue

        chave_titulo = "t:" + normalizar(o.nome)
        if o.mlb_id in vistos or chave_titulo in vistos:
            continue
        vistos.update((o.mlb_id, chave_titulo))
        ofertas.append(o)

    return ofertas, recusas


def buscar(con: sqlite3.Connection, seco: bool = False) -> int:
    """Varre os termos configurados e põe na mesma fila do agente do ML."""
    termos = nicho.ativo().config("shopee").get("termos", []) or []
    info(f"SHOPEE — nicho {nicho.ativo().nome} · {len(termos)} termo(s)")
    vistos: set[str] = set()
    recusas_total: dict[str, int] = {}
    novas = conhecidas = 0

    for termo in termos:
        for pagina in range(1, PAGINAS_POR_TERMO + 1):
            try:
                dados = chamar(BUSCA, {
                    "palavra": termo, "limite": ITENS_POR_PAGINA,
                    "pagina": pagina, "ordem": ORDENACAO,
                })
            except (HttpErro, RuntimeError) as e:
                aviso(f"  {termo!r} p{pagina}: {e}")
                break

            bloco = dados.get("productOfferV2") or {}
            nos = bloco.get("nodes") or []
            if not nos:
                break

            ofertas, recusas = extrair_ofertas(nos, vistos)
            for k, v in recusas.items():
                recusas_total[k] = recusas_total.get(k, 0) + v

            for o in ofertas:
                if seco:
                    print(f"  {o.desconto_pct:>3}%  [{o.marca:<16}] {o.nome[:52]}")
                    print(f"        R$ {o.preco_original:.2f} → R$ {o.preco_promocional:.2f}"
                          f"  {o.loja[:22]}{' ✓oficial' if o.loja_oficial else ''}")
                    novas += 1
                elif salvar_oferta(con, o):
                    con.execute(
                        "UPDATE ofertas SET origem='shopee', familia=? WHERE mlb_id=?",
                        (familia_da_marca(o.marca), o.mlb_id),
                    )
                    novas += 1
                else:
                    conhecidas += 1

            if not seco:
                con.commit()
            info(f"  {termo!r} p{pagina}: {len(nos)} nó(s) → {len(ofertas)} aprovada(s)")

            if not (bloco.get("pageInfo") or {}).get("hasNextPage"):
                break
            time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS))
        time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS))

    if recusas_total:
        resumo = " · ".join(
            f"{n} {m}" for m, n in sorted(recusas_total.items(), key=lambda x: -x[1])
        )
        info(f"recusados: {resumo}")
    ok(f"SHOPEE — {novas} nova(s), {conhecidas} já conhecida(s)")
    return novas
