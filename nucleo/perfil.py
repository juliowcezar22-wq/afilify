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
    ativo: bool = True
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
        ativo=g("ATIVO", True),
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


def listar() -> list[Perfil]:
    """Todos os perfis declarados em perfis/*.py (ordem alfabética)."""
    pasta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "perfis")
    nomes = sorted(
        f[:-3] for f in os.listdir(pasta)
        if f.endswith(".py") and f != "__init__.py"
    )
    return [carregar(n) for n in nomes]


def _canal_no_banco(nome: str) -> str:
    """Destino salvo pelo painel (config "canal") — permite ligar um perfil
    sem GRUPO_WHATSAPP no arquivo: basta escolher o grupo em /canais."""
    import json, sqlite3
    caminho = os.environ.get("ML_BANCO", "dados/ofertas.db")
    if not os.path.exists(caminho):
        return ""
    try:
        con = sqlite3.connect(caminho, timeout=5)
        linha = con.execute(
            "SELECT valor FROM config WHERE perfil=? AND chave='canal'", (nome,)
        ).fetchone()
        con.close()
        return (json.loads(linha[0]).get("grupo") or "") if linha else ""
    except Exception:
        return ""


def escolher_para_rodar(perfis: list[Perfil]) -> tuple[list[Perfil], list[tuple[str, str]]]:
    """(rodáveis, pulados_com_motivo). O runner decide o resto (locks)."""
    rodar, pulados = [], []
    for p in perfis:
        if not p.ativo:
            pulados.append((p.nome, "ATIVO=False"))
        elif not p.grupo_whatsapp and not _canal_no_banco(p.nome):
            pulados.append((p.nome, "sem grupo: defina GRUPO_WHATSAPP ou escolha em /canais"))
        else:
            rodar.append(p)
    return rodar, pulados
