"""
TESTAR BUSCA — a amostra que o usuário vê antes de ligar a fonte

Regra que sustenta esta funcionalidade: o teste roda **o mesmo caminho** da
coleta real, só que menor. Um teste que consultasse outra coisa viraria
demonstração — e na primeira vez que a fonte real divergisse da amostra, o
usuário perderia a confiança na ferramenta inteira.

Devolve o que a tela precisa e nada além: quantos compatíveis, e alguns
exemplos com nome, preço e desconto.
"""

from __future__ import annotations

# Quantos exemplos mostrar. Poucos de propósito: a tela quer dar confiança,
# não listar catálogo.
AMOSTRA = 6
# Quantas palavras-chave o teste realmente consulta. O teste precisa ser
# rápido (a pessoa está olhando), e as primeiras já dizem se a configuração
# faz sentido.
PALAVRAS_NO_TESTE = 3


def _exemplo(oferta) -> dict:
    """Só o que a tela mostra — nada de identificador nem link interno."""
    return {
        "nome": oferta.nome,
        "preco": oferta.preco_promocional,
        "preco_original": oferta.preco_original,
        "desconto": oferta.desconto_pct,
        "marca": oferta.marca,
        "imagem": oferta.imagem,
    }


def executar(con, parametros: dict) -> dict:
    """Executor do comando `testar_busca`.

    Recebe os critérios já normalizados e devolve a amostra. Erros viram
    frase — quem lê é alguém esperando na tela.
    """
    from nucleo import fonte_busca
    from mercadolivre import buscador

    criterios = fonte_busca.normalizar(parametros.get("criterios") or {})
    palavras = criterios["palavras_chave"][:PALAVRAS_NO_TESTE]
    onde = criterios["onde"]

    if onde["busca"] and not buscador.cookie_ml():
        if not onde["pagina_ofertas"]:
            return {
                "compativeis": 0,
                "amostra": [],
                "aviso": "Conecte sua conta do Mercado Livre para buscar nos resultados de busca.",
            }

    anterior = buscador.CRITERIOS_DA_FONTE
    buscador.usar_criterios(criterios)
    try:
        compativeis, exemplos = [], []
        bloqueios = 0

        vistos: set = set()

        # Página de ofertas do dia: não exige sessão, e é a fonte que
        # continua de pé quando a busca é bloqueada.
        if onde["pagina_ofertas"]:
            html = buscador.baixar_pagina(1)
            if buscador.foi_bloqueada(html):
                bloqueios += 1
            else:
                ctx = buscador.extrair_contexto(html)
                ofertas, _recusas = buscador.extrair_ofertas_json(ctx, vistos) if ctx else ([], {})
                for oferta in ofertas:
                    passa, _ = fonte_busca.aceita(oferta, criterios)
                    if not passa or oferta.mlb_id in compativeis:
                        continue
                    compativeis.append(oferta.mlb_id)
                    if len(exemplos) < AMOSTRA:
                        exemplos.append(_exemplo(oferta))

        for termo in (palavras if onde["busca"] else []):
            try:
                html = buscador.baixar_busca(termo)
            except Exception:
                continue
            try:
                ctx = buscador.contexto_da_busca(html)
            except buscador.BuscaBloqueada:
                # Bloqueio não é "não encontrei nada": dizer ao usuário que
                # os critérios estão apertados demais, quando o problema é
                # do outro lado, o faria caçar um defeito que não existe.
                bloqueios += 1
                continue
            if not ctx:
                continue
            ofertas, _recusas = buscador.extrair_ofertas_json(ctx, vistos)
            for oferta in ofertas:
                passa, _ = fonte_busca.aceita(oferta, criterios)
                if not passa:
                    continue
                if oferta.mlb_id in compativeis:
                    continue
                compativeis.append(oferta.mlb_id)
                if len(exemplos) < AMOSTRA:
                    exemplos.append(_exemplo(oferta))
    finally:
        buscador.usar_criterios(anterior)

    resposta = {"compativeis": len(compativeis), "amostra": exemplos,
                "palavras_testadas": palavras}
    if bloqueios and not compativeis:
        resposta["aviso"] = buscador.BuscaBloqueada.mensagem_usuario
        resposta["bloqueada"] = True
    elif not compativeis:
        resposta["aviso"] = fonte_busca.por_que_vazio(criterios)
    return resposta
