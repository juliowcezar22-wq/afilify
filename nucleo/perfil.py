"""
CARREGADOR DE PERFIL

Um perfil amarra nicho + marketplaces + grupo + ritmo. É a unidade que vira
LINHA NO BANCO quando o painel existir — cada cliente do SaaS é um perfil, e
o motor é o mesmo para todos.

    python3 agente.py --perfil casa_ml_shopee ml rodar
    PERFIL=casa_ml_shopee python3 agente.py shopee buscar
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field


@dataclass
class Perfil:
    nome: str
    nicho: str = "perfumes"
    marketplaces: list = field(default_factory=lambda: ["mercadolivre"])
    grupo_whatsapp: str = ""
    envios_por_dia: tuple = (95, 135)
    inicio_janela: tuple = (8.75, 9.5)
    fim_janela: tuple = (22.0, 22.75)
    dispersao: float = 0.82
    proporcao_preferidas: float = 0.70
    busca_horas: list = field(default_factory=lambda: [7, 15])
    validade_horas: int = 48
    clone_ativo: bool = False
    clone_grupos: list = field(default_factory=list)


def carregar(nome: str) -> Perfil:
    mod = importlib.import_module(f"perfis.{nome}")
    g = lambda k, p=None: getattr(mod, k, p)
    return Perfil(
        nome=g("NOME", nome),
        nicho=g("NICHO", "perfumes"),
        marketplaces=g("MARKETPLACES", ["mercadolivre"]),
        grupo_whatsapp=g("GRUPO_WHATSAPP", ""),
        envios_por_dia=tuple(g("ENVIOS_POR_DIA", (95, 135))),
        inicio_janela=tuple(g("ENVIO_INICIO_JANELA", (8.75, 9.5))),
        fim_janela=tuple(g("ENVIO_FIM_JANELA", (22.0, 22.75))),
        dispersao=g("ENVIO_DISPERSAO", 0.82),
        proporcao_preferidas=g("PROPORCAO_PREFERIDAS", 0.70),
        busca_horas=g("BUSCA_HORAS", [7, 15]),
        validade_horas=g("VALIDADE_HORAS", 48),
        clone_ativo=g("CLONE_ATIVO", False),
        clone_grupos=g("CLONE_GRUPOS", []),
    )


_ativo: Perfil | None = None


def ativo() -> Perfil:
    global _ativo
    if _ativo is None:
        _ativo = carregar(os.environ.get("PERFIL", "perfumes_ml"))
    return _ativo


def usar(nome: str) -> Perfil:
    global _ativo
    _ativo = carregar(nome)
    return _ativo
