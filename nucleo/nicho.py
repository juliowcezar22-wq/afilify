"""
CARREGADOR DE NICHO

O motor não conhece perfume nem casa. Ele pede um nicho a este módulo e
trabalha com o que vier. Trocar de nicho é trocar uma string.

    from nucleo.nicho import ativo
    n = ativo()
    n.keywords, n.blacklist, n.marcas, n.headlines, ...

Campos opcionais no arquivo do nicho ganham padrão aqui — assim um nicho
novo pode ser um arquivo curto, declarando só o que importa.
"""

from __future__ import annotations

import importlib
import os
import re
import unicodedata
from dataclasses import dataclass, field


def normalizar(texto: str) -> str:
    """'Dolce & Gabbana' → 'dolce gabbana'. Sem acento, sem pontuação."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()


@dataclass
class Nicho:
    nome: str
    descricao: str = ""
    keywords: list = field(default_factory=list)
    regex_qualifica: str = ""
    blacklist: list = field(default_factory=list)
    unidade_regex: str = ""
    unidade_nome: str = ""
    unidade_minima: int = 0
    desconto_minimo: int = 10
    exige_marca: bool = True
    marcas: dict = field(default_factory=dict)
    familias_preferidas: tuple = ()
    familias_contratipo: tuple = ()
    apelidos: dict = field(default_factory=dict)
    termos_contratipo: list = field(default_factory=list)
    titulo_prefixos: list = field(default_factory=list)
    titulo_ruido: list = field(default_factory=list)
    headlines: dict = field(default_factory=dict)
    por_marketplace: dict = field(default_factory=dict)

    # ── índices derivados, montados uma vez ──
    marcas_norm: dict = field(default_factory=dict, repr=False)
    familia_por_marca: dict = field(default_factory=dict, repr=False)
    contratipo_norm: list = field(default_factory=list, repr=False)
    re_unidade: object = field(default=None, repr=False)
    re_qualifica: object = field(default=None, repr=False)

    def indexar(self) -> "Nicho":
        for familia, lista in self.marcas.items():
            for m in lista:
                chave = normalizar(m)
                self.marcas_norm.setdefault(chave, m)
                self.familia_por_marca.setdefault(chave, familia)
        self.contratipo_norm = [normalizar(t) for t in self.termos_contratipo]
        self.re_unidade = re.compile(self.unidade_regex, re.I) if self.unidade_regex else None
        self.re_qualifica = re.compile(self.regex_qualifica, re.I) if self.regex_qualifica else None
        return self

    def config(self, marketplace: str) -> dict:
        return self.por_marketplace.get(marketplace.lower(), {})


def carregar(nome: str) -> Nicho:
    mod = importlib.import_module(f"nichos.{nome}")
    g = lambda k, p=None: getattr(mod, k, p)
    return Nicho(
        nome=g("NOME", nome),
        descricao=g("DESCRICAO", ""),
        keywords=g("KEYWORDS_OBRIGATORIAS", []),
        regex_qualifica=g("REGEX_QUALIFICA", ""),
        blacklist=g("BLACKLIST", []),
        unidade_regex=g("UNIDADE_REGEX", ""),
        unidade_nome=g("UNIDADE_NOME", ""),
        unidade_minima=g("UNIDADE_MINIMA", 0),
        desconto_minimo=g("DESCONTO_MINIMO", 10),
        exige_marca=g("EXIGE_MARCA", True),
        marcas=g("MARCAS", {}),
        familias_preferidas=tuple(g("FAMILIAS_PREFERIDAS", ())),
        familias_contratipo=tuple(g("FAMILIAS_CONTRATIPO", ())),
        apelidos=g("MARCAS_APELIDOS", {}),
        termos_contratipo=g("TERMOS_CONTRATIPO", []),
        titulo_prefixos=g("TITULO_PREFIXOS", []),
        titulo_ruido=g("TITULO_RUIDO", []),
        headlines=g("HEADLINES", {}),
        por_marketplace={
            "mercadolivre": g("MERCADOLIVRE", {}),
            "shopee": g("SHOPEE", {}),
        },
    ).indexar()


_ativo: Nicho | None = None


def ativo() -> Nicho:
    """O nicho em uso. Vem de NICHO no .env, ou do perfil, ou 'perfumes'."""
    global _ativo
    if _ativo is None:
        _ativo = carregar(os.environ.get("NICHO", "perfumes"))
    return _ativo


def usar(nome: str) -> Nicho:
    """Troca o nicho em tempo de execução (o painel vai usar isto)."""
    global _ativo
    _ativo = carregar(nome)
    return _ativo
