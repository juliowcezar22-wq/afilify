"""
TIPOS DE NICHO — a curadoria que protege o grupo, como dado

Hoje o que impede publicar falsificação e paralela mora em `nichos/*.py`:
marcas aceitas, palavras proibidas, volume mínimo, termos de contratipo. É o
ativo de qualidade da operação, e é por isso que o usuário NÃO o configura
(decisão D29) — ele escolhe um tipo de nicho ao criar o projeto e pronto.

Este módulo faz a ponte: lê os arquivos de nicho (que continuam sendo a
fonte de versão, revisada por gente) e semeia a tabela `tipos_nicho`, de onde
o produto passa a ler.

    from nucleo import tipos_nicho
    tipos_nicho.semear(con)             # idempotente; não sobrescreve edição
    tipos_nicho.curadoria(con, "perfumes")

A `versao` existe para a curadoria evoluir sem quebrar projeto existente:
subir a versão do arquivo re-semeia; projetos guardam o id, não a cópia.
"""

from __future__ import annotations

import json
import os

from nucleo.comum import agora
from nucleo import nicho as mod_nicho

# Rótulo humano de cada nicho conhecido. Nicho novo sem rótulo aqui ganha o
# nome capitalizado — arquivo novo nunca quebra a listagem.
ROTULOS = {
    "perfumes": "Perfumes",
    "casa": "Casa e decoração",
}


def disponiveis() -> list:
    """Ids dos nichos declarados em nichos/*.py, em ordem alfabética."""
    pasta = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nichos")
    if not os.path.isdir(pasta):
        return []
    return sorted(
        f[:-3] for f in os.listdir(pasta)
        if f.endswith(".py") and f != "__init__.py"
    )


def rotulo(nicho_id: str) -> str:
    return ROTULOS.get(nicho_id) or nicho_id.replace("_", " ").replace("-", " ").capitalize()


def extrair_curadoria(nicho_id: str) -> dict:
    """O que de fato decide se um anúncio vira oferta.

    Só o que é curadoria de QUALIDADE entra aqui. Termos de busca não entram:
    eles viraram configuração da Fonte, escolhida pelo usuário (D28).
    """
    n = mod_nicho.carregar(nicho_id)
    return {
        "marcas_aceitas": {familia: list(marcas) for familia, marcas in n.marcas.items()},
        "palavras_proibidas": list(n.blacklist),
        "exige_marca": bool(n.exige_marca),
        "unidade": {
            "nome": n.unidade_nome,
            "minima": n.unidade_minima,
            "regex": n.unidade_regex,
        },
        "desconto_minimo_padrao": n.desconto_minimo,
        "contratipo": {
            "termos": list(n.termos_contratipo),
            "familias_permitidas": list(n.familias_contratipo),
        },
        "familias_preferidas": list(n.familias_preferidas),
        "titulo": {
            "prefixos": list(n.titulo_prefixos),
            "ruido": list(n.titulo_ruido),
        },
        "qualifica_regex": n.regex_qualifica,
        "categoria_por_marketplace": {
            plataforma: cfg.get("categoria", "")
            for plataforma, cfg in n.por_marketplace.items() if cfg
        },
        "termos_semente": {
            plataforma: list(cfg.get("termos", []))
            for plataforma, cfg in n.por_marketplace.items() if cfg
        },
    }


def semear(con, forcar: bool = False) -> int:
    """Grava os tipos de nicho ausentes. Devolve quantos foram semeados.

    Idempotente: um tipo que já existe na mesma versão não é tocado. Com
    `forcar`, reescreve — usado quando a curadoria de um arquivo muda.
    """
    ts = agora().isoformat(timespec="seconds")
    semeados = 0
    for nicho_id in disponiveis():
        try:
            curadoria = extrair_curadoria(nicho_id)
        except Exception:
            continue          # nicho quebrado não impede os outros de existirem
        existente = con.execute(
            "SELECT versao FROM tipos_nicho WHERE id = ?", (nicho_id,)).fetchone()
        if existente and not forcar:
            continue
        versao = (existente["versao"] + 1) if existente else 1
        con.execute(
            "INSERT INTO tipos_nicho (id, nome, versao, curadoria, criado_em) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET "
            "nome = excluded.nome, versao = excluded.versao, curadoria = excluded.curadoria",
            (nicho_id, rotulo(nicho_id), versao,
             json.dumps(curadoria, ensure_ascii=False), ts))
        semeados += 1
    con.commit()
    return semeados


def curadoria(con, nicho_id: str) -> dict:
    """A curadoria vigente de um tipo de nicho ({} se não existir)."""
    linha = con.execute(
        "SELECT curadoria FROM tipos_nicho WHERE id = ?", (nicho_id,)).fetchone()
    if not linha:
        return {}
    try:
        return json.loads(linha["curadoria"])
    except (ValueError, TypeError):
        return {}


def listar(con) -> list:
    """[(id, nome, versao)] para a tela de criação de projeto."""
    return [
        {"id": r["id"], "nome": r["nome"], "versao": r["versao"]}
        for r in con.execute("SELECT id, nome, versao FROM tipos_nicho ORDER BY nome")
    ]
