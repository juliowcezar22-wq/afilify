#!/usr/bin/env python3
"""
AGENTE DA SHOPEE

    python3 agente.py shopee buscar        varre e põe na fila
    python3 agente.py shopee buscar --seco só mostra
    python3 agente.py shopee testar        confere credenciais
    python3 agente.py shopee termos "x"    testa um termo

A fila, o ritmo de envio e o WhatsApp são os MESMOS do Mercado Livre — as
ofertas caem no mesmo banco e saem pelo mesmo daemon, com a mesma cadência
e a mesma cota diária. Isto aqui é só a origem das ofertas.
"""

from __future__ import annotations

import argparse
import sys

from nucleo.comum import (
    AZUL, CINZA, FIM, VERDE, VERMELHO, abrir_banco, agora, erro, info, ok,
    aviso, reais,
)
from shopee import config
from shopee.buscador import BUSCA, buscar, chamar, extrair_ofertas


def cmd_buscar(args) -> int:
    con = abrir_banco()
    try:
        buscar(con, seco=args.seco)
    except RuntimeError as e:
        erro(str(e))
        return 1
    finally:
        con.close()
    return 0


def cmd_testar(args) -> int:
    print()
    if not config.SHOPEE_APP_ID or not config.SHOPEE_SECRET:
        erro("SHOPEE_APP_ID / SHOPEE_SECRET vazios no .env")
        return 1
    try:
        dados = chamar(BUSCA, {"palavra": "perfume", "limite": 3,
                               "pagina": 1, "ordem": config.ORDENACAO})
        nos = (dados.get("productOfferV2") or {}).get("nodes") or []
        ok(f"API da Shopee respondendo — {len(nos)} produto(s) na sonda")
    except RuntimeError as e:
        erro(str(e))
        return 1

    print(f"\n{CINZA}loja oficial obrigatória: "
          f"{'SIM' if config.SOMENTE_LOJA_OFICIAL else 'não'} · "
          f"{len(config.TERMOS_BUSCA)} termo(s) · "
          f"{config.PAGINAS_POR_TERMO} página(s) por termo{FIM}")
    if not config.SOMENTE_LOJA_OFICIAL:
        aviso("sem exigir loja oficial, a Shopee entrega muita réplica")
    print()
    return 0


def cmd_termos(args) -> int:
    """Mostra o que cada termo renderia, e por que o resto caiu."""
    alvos = args.termo or config.TERMOS_BUSCA
    for termo in alvos:
        try:
            dados = chamar(BUSCA, {"palavra": termo, "limite": config.ITENS_POR_PAGINA,
                                   "pagina": 1, "ordem": config.ORDENACAO})
        except RuntimeError as e:
            erro(f"{termo!r}: {e}")
            continue
        nos = (dados.get("productOfferV2") or {}).get("nodes") or []
        ofertas, recusas = extrair_ofertas(nos, set())
        print(f"\n  {VERDE}{termo!r}{FIM}: {len(nos)} nó(s) → "
              f"{VERDE}{len(ofertas)} aprovada(s){FIM}")
        for o in ofertas[:6]:
            print(f"     -{o.desconto_pct:>2}% R$ {o.preco_promocional:>8.2f} "
                  f"[{o.marca:<16}] {o.nome[:44]}")
        if recusas:
            print(f"     {CINZA}recusas: "
                  f"{dict(sorted(recusas.items(), key=lambda x: -x[1]))}{FIM}")
    print()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Agente da Shopee")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("buscar", help="varre os termos e põe na fila")
    b.add_argument("--seco", action="store_true", help="só mostra, não grava")

    sub.add_parser("testar", help="confere credenciais e configuração")

    t = sub.add_parser("termos", help="testa termos de busca")
    t.add_argument("termo", nargs="*", help="padrão: os de TERMOS_BUSCA")

    args = p.parse_args()
    return {"buscar": cmd_buscar, "testar": cmd_testar, "termos": cmd_termos}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
