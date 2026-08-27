"""
MERCADO LIVRE — a conta de afiliado do usuário

O Mercado Livre não publica API de afiliados (verificado em 26/08/2026): a
geração de link acontece pelo mesmo caminho que o painel de afiliados usa,
com a sessão da conta. Enquanto a extensão de navegador não existe (D26), a
renovação da sessão vive fora da Afilify.

O que a plataforma faz por aqui, então:
  · provar que a conexão funciona, gerando um link de verdade
  · dizer qual tag está sendo usada — a atribuição é o que separa trabalhar
    e receber de trabalhar e outro receber
  · avisar antes de a sessão morrer, em vez de depois
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

# Sessão do Mercado Livre dura cerca de 30 dias. O aviso começa antes para
# a renovação não virar emergência.
VALIDADE_DIAS = 30
AVISAR_A_PARTIR_DE = 21

CONECTADA = "conectado"
PRECISA_RECONECTAR = "precisa_reconectar"
EXPIRADA = "sessao_perdida"
AUSENTE = "desconectado"

FRASES = {
    CONECTADA: "Sua conta está conectada e gerando links normalmente.",
    PRECISA_RECONECTAR: "Sua conexão com o Mercado Livre vence em breve. "
                        "Renove para não interromper as publicações.",
    EXPIRADA: "Sua conexão com o Mercado Livre expirou. "
              "Reconecte sua conta para continuar gerando ofertas.",
    AUSENTE: "Conecte sua conta de afiliado do Mercado Livre para gerar links.",
}


def estado_da_sessao(idade_dias: float) -> str:
    if idade_dias < 0:
        return AUSENTE
    if idade_dias >= VALIDADE_DIAS:
        return EXPIRADA
    if idade_dias >= AVISAR_A_PARTIR_DE:
        return PRECISA_RECONECTAR
    return CONECTADA


def idade_da_sessao() -> float:
    """Dias desde a última renovação. -1 quando não há sessão."""
    from mercadolivre.config import ARQUIVO_COOKIE
    if os.environ.get("ML_COOKIE", "").strip():
        return 0.0
    if not os.path.exists(ARQUIVO_COOKIE):
        return -1.0
    idade = datetime.now() - datetime.fromtimestamp(os.path.getmtime(ARQUIVO_COOKIE))
    return idade / timedelta(days=1)


def frase(estado: str) -> str:
    return FRASES.get(estado, FRASES[AUSENTE])


def _produto_real() -> str:
    """Um anúncio que existe agora, colhido da vitrine pública.

    A vitrine não exige sessão — então serve mesmo quando a busca logada
    está bloqueada.
    """
    try:
        from mercadolivre import buscador
        html = buscador.baixar_pagina(1)
        if buscador.foi_bloqueada(html):
            return ""
        contexto = buscador.extrair_contexto(html)
        if not contexto:
            return ""
        ofertas, _ = buscador.extrair_ofertas_json(contexto, set())
        return ofertas[0].url if ofertas else ""
    except Exception:
        return ""


def validar(con=None, parametros: dict = None) -> dict:
    """Prova que a conexão funciona — gerando um link de verdade.

    Executor do comando `validar_conexao_ml`. Um teste que só olhasse a data
    do arquivo diria "conectado" para uma sessão que o Mercado Livre já
    recusa; só gerar link responde a pergunta que importa.
    """
    from mercadolivre import buscador
    from mercadolivre.config import ML_AFFILIATE_TAG

    idade = idade_da_sessao()
    estado = estado_da_sessao(idade)

    if estado == AUSENTE:
        return {"estado": estado, "mensagem": frase(estado), "tag": "", "gerou_link": False}

    if not ML_AFFILIATE_TAG:
        return {
            "estado": AUSENTE,
            "mensagem": "Falta informar a sua tag de afiliado do Mercado Livre.",
            "tag": "",
            "gerou_link": False,
        }

    # O produto precisa EXISTIR: um endereço inventado é recusado pelo
    # Mercado Livre, e a validação diria "não gerou link" para uma sessão
    # perfeitamente boa — o falso negativo que faria o usuário reconectar
    # uma conta que não tem problema nenhum.
    alvo = (parametros or {}).get("url") or _produto_real()
    if not alvo:
        return {
            "estado": estado,
            "mensagem": "Não conseguimos verificar a conexão agora. Tente de novo em instantes.",
            "tag": ML_AFFILIATE_TAG,
            "gerou_link": False,
        }
    try:
        links = buscador.gerar_links([alvo])
    except RuntimeError as e:
        texto = str(e).lower()
        expirou = "expirada" in texto or "401" in texto or "403" in texto
        return {
            "estado": EXPIRADA if expirou else estado,
            "mensagem": frase(EXPIRADA) if expirou else
                        "Não conseguimos falar com o Mercado Livre agora. Tente de novo em instantes.",
            "tag": ML_AFFILIATE_TAG,
            "gerou_link": False,
        }

    curto = next(iter(links.values()), "")
    return {
        "estado": estado,
        "mensagem": frase(estado),
        "tag": ML_AFFILIATE_TAG,
        "gerou_link": bool(curto),
        "dias_restantes": max(0, round(VALIDADE_DIAS - idade)),
    }
