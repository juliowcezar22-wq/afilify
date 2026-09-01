"""
FONTE DE BUSCA — a intenção do usuário virando coleta

O usuário diz o que quer encontrar em quatro campos. Este módulo traduz isso
para o que o buscador precisa, e faz o caminho de volta: o que a coleta
encontrou, filtrado pelos critérios dele.

    criterios = {
      "palavras_chave": ["perfume masculino", "perfume árabe"],
      "onde": {"busca": True, "pagina_ofertas": True},
      "desconto_minimo": 30,
      "preco": {"min": 50, "max": 500},
      "excluir": {"palavras": ["kit"], "marcas": ["Bacarati"]}
    }

O que NÃO está aqui, de propósito: páginas, pausas, tentativas, categoria,
cabeçalhos. Isso é decisão da Afilify — expor no formulário seria transformar
o usuário em operador de scraper.
"""

from __future__ import annotations

# Os únicos campos aceitos. Campo desconhecido é recusado na borda, para que
# a proibição de expor parâmetro técnico valha no contrato, não só na tela.
CAMPOS = {"palavras_chave", "onde", "desconto_minimo", "preco", "excluir"}
ONDE = {"busca", "pagina_ofertas"}

# Teto de palavras-chave: cada uma é uma requisição, e uma lista enorme não
# encontra mais — só demora mais e chama atenção.
MAX_PALAVRAS = 30


class CriteriosInvalidos(ValueError):
    """Mensagem já pronta para a tela."""


def normalizar(bruto) -> dict:
    """Valida e devolve os critérios no formato que o motor usa.

    Levanta CriteriosInvalidos com uma frase de gente — nunca com nome de
    campo interno.
    """
    if not isinstance(bruto, dict):
        raise CriteriosInvalidos("Não entendi a configuração desta fonte.")

    desconhecidos = set(bruto) - CAMPOS
    if desconhecidos:
        raise CriteriosInvalidos(
            "Esta fonte recebeu uma configuração que a Afilify não reconhece.")

    palavras = bruto.get("palavras_chave") or []
    if not isinstance(palavras, list) or not all(isinstance(p, str) for p in palavras):
        raise CriteriosInvalidos("As palavras-chave precisam ser uma lista de textos.")
    palavras = [p.strip() for p in palavras if p and p.strip()]
    if not palavras:
        raise CriteriosInvalidos("Escreva ao menos uma palavra-chave do que você quer encontrar.")
    if len(palavras) > MAX_PALAVRAS:
        raise CriteriosInvalidos(
            f"São muitas palavras-chave (máximo {MAX_PALAVRAS}). "
            "Menos termos, mais específicos, encontram melhor.")

    # Ausente = ainda não escolheu, e o padrão vale. Presente = escolha
    # explícita, e os valores mandam — com padrão True aqui, "não escolhi
    # nada" viraria "escolhi busca", e o aviso nunca apareceria.
    if "onde" not in bruto or bruto.get("onde") is None:
        onde = {"busca": True, "pagina_ofertas": False}
    else:
        onde = bruto["onde"]
        if not isinstance(onde, dict) or set(onde) - ONDE:
            raise CriteriosInvalidos(
                "Escolha onde buscar: nos resultados de busca, na página de ofertas, ou nos dois.")
        onde = {"busca": bool(onde.get("busca", False)),
                "pagina_ofertas": bool(onde.get("pagina_ofertas", False))}
        if not onde["busca"] and not onde["pagina_ofertas"]:
            raise CriteriosInvalidos("Escolha ao menos um lugar para buscar.")

    desconto = bruto.get("desconto_minimo", 0)
    if not isinstance(desconto, (int, float)) or not 0 <= desconto <= 99:
        raise CriteriosInvalidos("O desconto mínimo precisa ser um número entre 0 e 99.")

    preco = bruto.get("preco") or {}
    if not isinstance(preco, dict):
        raise CriteriosInvalidos("A faixa de preço não foi entendida.")
    minimo = preco.get("min")
    maximo = preco.get("max")
    for v in (minimo, maximo):
        if v is not None and (not isinstance(v, (int, float)) or v < 0):
            raise CriteriosInvalidos("A faixa de preço precisa ter valores positivos.")
    if minimo is not None and maximo is not None and minimo > maximo:
        raise CriteriosInvalidos("O preço mínimo ficou maior que o máximo.")

    excluir = bruto.get("excluir") or {}
    if not isinstance(excluir, dict) or set(excluir) - {"palavras", "marcas"}:
        raise CriteriosInvalidos("A lista de exclusões não foi entendida.")
    for chave in ("palavras", "marcas"):
        valor = excluir.get(chave) or []
        if not isinstance(valor, list) or not all(isinstance(x, str) for x in valor):
            raise CriteriosInvalidos("As exclusões precisam ser listas de textos.")

    return {
        "palavras_chave": palavras,
        "onde": onde,
        "desconto_minimo": int(desconto),
        "preco": {"min": minimo, "max": maximo},
        "excluir": {
            "palavras": [p.strip() for p in (excluir.get("palavras") or []) if p.strip()],
            "marcas": [m.strip() for m in (excluir.get("marcas") or []) if m.strip()],
        },
    }


def padrao_do_nicho(nicho_ativo) -> dict:
    """Critérios iniciais de um nicho — o usuário abre a tela já com algo que
    funciona, em vez de uma página em branco."""
    cfg = nicho_ativo.config("mercadolivre")
    return {
        "palavras_chave": list(cfg.get("termos", []))[:8],
        "onde": {"busca": True, "pagina_ofertas": True},
        "desconto_minimo": nicho_ativo.desconto_minimo,
        "preco": {"min": None, "max": None},
        "excluir": {"palavras": [], "marcas": []},
    }


def aceita(oferta, criterios: dict) -> tuple:
    """(passa, motivo). O motivo alimenta o resumo de recusas da coleta.

    Aplica SÓ o que o usuário pediu. A curadoria do nicho (marcas aceitas,
    palavras proibidas, tamanho mínimo) roda antes, no filtro do próprio
    buscador — são duas barreiras independentes, de propósito.
    """
    desconto = getattr(oferta, "desconto_pct", None) or 0
    if criterios["desconto_minimo"] and desconto < criterios["desconto_minimo"]:
        return False, "desconto abaixo do pedido"

    preco = getattr(oferta, "preco_promocional", None)
    faixa = criterios.get("preco") or {}
    if preco is not None:
        if faixa.get("min") is not None and preco < faixa["min"]:
            return False, "abaixo da faixa de preço"
        if faixa.get("max") is not None and preco > faixa["max"]:
            return False, "acima da faixa de preço"

    texto = (getattr(oferta, "nome", "") or "").lower()
    for palavra in criterios["excluir"]["palavras"]:
        if palavra.lower() in texto:
            return False, "contém palavra excluída"

    marca = (getattr(oferta, "marca", "") or "").lower()
    for excluida in criterios["excluir"]["marcas"]:
        if excluida.lower() == marca:
            return False, "marca excluída"

    return True, ""


# ══════════════════════════════════════════════════════════════════════
# HISTÓRICO DE COLETAS
# ══════════════════════════════════════════════════════════════════════
# Sem isto, uma coleta que rodou e não achou nada é indistinguível de uma
# coleta que nunca aconteceu — e o usuário fica olhando para uma tela
# parada sem saber se o problema é dele ou nosso.

import uuid as _uuid


def iniciar_execucao(con, fonte_id: str, workspace_id: str = "") -> str:
    from nucleo.comum import agora, WORKSPACE_PADRAO
    eid = str(_uuid.uuid4())
    con.execute(
        "INSERT INTO execucoes_fonte (id, workspace_id, fonte_id, iniciada_em, resultado, "
        "encontradas, novas, motivo) VALUES (?, ?, ?, ?, 'ok', 0, 0, '')",
        (eid, workspace_id or WORKSPACE_PADRAO, fonte_id,
         agora().isoformat(timespec="seconds")))
    con.commit()
    return eid


def concluir_execucao(con, execucao_id: str, encontradas: int, novas: int,
                      motivo: str = "") -> None:
    """`sem_novidades` é resultado legítimo, não falha: a fonte trabalhou,
    o catálogo é que não mudou."""
    from nucleo.comum import agora
    if motivo:
        resultado = "falhou"
    elif novas == 0:
        resultado = "sem_novidades"
    else:
        resultado = "ok"
    con.execute(
        "UPDATE execucoes_fonte SET terminada_em = ?, resultado = ?, encontradas = ?, "
        "novas = ?, motivo = ? WHERE id = ?",
        (agora().isoformat(timespec="seconds"), resultado, encontradas, novas, motivo, execucao_id))
    con.execute(
        "UPDATE fontes SET ultima_execucao_em = ? WHERE id = "
        "(SELECT fonte_id FROM execucoes_fonte WHERE id = ?)",
        (agora().isoformat(timespec="seconds"), execucao_id))
    con.commit()


def resumo_legivel(resultado: str, encontradas: int, novas: int, motivo: str) -> str:
    """Uma linha que o usuário entende, para a lista de coletas."""
    if resultado == "falhou":
        return motivo or "A coleta não pôde ser concluída."
    if resultado == "sem_novidades":
        return (f"Procurou e não encontrou novidades ({encontradas} já conhecidas)."
                if encontradas else "Procurou e não encontrou nada novo.")
    return f"Encontrou {novas} oferta{'s' if novas != 1 else ''} nova{'s' if novas != 1 else ''}."


def por_que_vazio(criterios: dict) -> str:
    """Quando não vem nada, dizer o que provavelmente apertou demais.

    Um "nenhum resultado" seco deixa o usuário adivinhando qual dos quatro
    campos mexer.
    """
    apertos = []
    if criterios["desconto_minimo"] >= 40:
        apertos.append(f"o desconto mínimo de {criterios['desconto_minimo']}%")
    faixa = criterios.get("preco") or {}
    if faixa.get("min") and faixa.get("max"):
        apertos.append(f"a faixa de R$ {faixa['min']:.0f} a R$ {faixa['max']:.0f}")
    elif faixa.get("min"):
        apertos.append(f"o preço mínimo de R$ {faixa['min']:.0f}")
    if criterios["excluir"]["palavras"] or criterios["excluir"]["marcas"]:
        apertos.append("as exclusões")

    if not apertos:
        return ("Não encontramos nada com essas palavras-chave. "
                "Tente termos mais comuns, como os que você usaria na busca do site.")
    if len(apertos) == 1:
        return f"Não encontramos nada. Provavelmente {apertos[0]} está restringindo demais."
    return ("Não encontramos nada. Provavelmente "
            + ", ".join(apertos[:-1]) + f" e {apertos[-1]} estão restringindo demais.")
