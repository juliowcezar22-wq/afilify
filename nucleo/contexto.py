"""
CONTEXTO — quem o motor está operando agora

Até aqui, o motor descobria o projeto no IMPORT: `nucleo/comum.py` lia o
arquivo do perfil e congelava dezenas de constantes de módulo. Foi por isso
que `runner.py` precisou subir um processo por projeto, e é por isso que
criar um projeto exigia escrever um arquivo e reiniciar tudo.

Este módulo troca aquelas constantes por um objeto explícito, que pode vir
de duas fontes:

    Contexto.do_perfil(p)        os arquivos perfis/*.py — o jeito antigo,
                                 preservado para a operação viva não mudar
    Contexto.do_banco(con, id)   uma automação de verdade, criada na tela

O motor não precisa saber de qual das duas veio. É essa indiferença que
permite criar projeto pela interface sem reiniciar nada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Destino:
    """Para onde uma publicação vai."""
    id: str = ""
    alvo: str = ""              # identificador do grupo — área técnica
    nome: str = ""              # nome legível
    conexao_id: str = ""
    ordem: int = 0


@dataclass
class Ritmo:
    """O que o usuário controla sobre o compasso das publicações.

    Dispersão fica aqui porque o motor precisa dela, mas NÃO é configuração
    de usuário: é constante calibrada contra o comportamento real de um grupo
    (lognormal, sigma 0.82). Quem decide é a Afilify.
    """
    envios_por_dia: tuple = (95, 135)
    inicio_janela: tuple = (8.75, 9.5)
    fim_janela: tuple = (22.0, 22.75)
    dispersao: float = 0.82
    proporcao_preferidas: float = 0.70
    busca_horas: list = field(default_factory=lambda: [7, 15])
    validade_horas: int = 48


@dataclass
class Contexto:
    """Tudo que o motor precisa saber para operar UMA automação."""

    workspace_id: str = "ws-afilify"

    projeto_id: str = ""
    projeto_nome: str = ""
    # Identificador usado nas colunas `perfil` e nas chaves de `estado`.
    # No modo antigo é o nome do perfil ("perfumes-ml"); no modo novo é o id
    # do projeto. O motor só precisa que seja estável e único.
    chave: str = ""

    automacao_id: str = ""
    automacao_nome: str = ""

    nicho: str = "perfumes"
    marketplaces: list = field(default_factory=lambda: ["mercadolivre"])
    ritmo: Ritmo = field(default_factory=Ritmo)
    destinos: list = field(default_factory=list)

    clone_ativo: bool = False
    clone_grupos: list = field(default_factory=list)

    # A fonte de busca em vigor: o que procurar, e qual registro de coleta
    # atualizar quando a busca rodar. Vazio no modo antigo — lá os termos
    # vêm do arquivo do nicho.
    fonte_busca_id: str = ""
    criterios_busca: dict = field(default_factory=dict)

    # De onde este contexto veio — o motor não muda de comportamento por
    # causa disso, mas o diagnóstico fica honesto.
    origem: str = "perfil"

    # ── construtores ─────────────────────────────────────────────────

    @classmethod
    def do_perfil(cls, p) -> "Contexto":
        """A partir de perfis/*.py. Preserva o comportamento de sempre."""
        destinos = []
        if p.grupo_whatsapp:
            destinos.append(Destino(alvo=p.grupo_whatsapp, nome="", ordem=0))
        return cls(
            projeto_nome=p.nome,
            chave=p.nome,
            automacao_nome=p.nome,
            nicho=p.nicho,
            marketplaces=list(p.marketplaces),
            ritmo=Ritmo(
                envios_por_dia=tuple(p.envios_por_dia),
                inicio_janela=tuple(p.inicio_janela),
                fim_janela=tuple(p.fim_janela),
                dispersao=p.dispersao,
                proporcao_preferidas=p.proporcao_preferidas,
                busca_horas=list(p.busca_horas),
                validade_horas=p.validade_horas,
            ),
            destinos=destinos,
            clone_ativo=p.clone_ativo,
            clone_grupos=list(p.clone_grupos),
            origem="perfil",
        )

    @classmethod
    def do_banco(cls, con, automacao_id: str) -> "Contexto":
        """A partir de uma automação criada na interface.

        Levanta ValueError quando a automação não existe — o supervisor
        precisa saber disso para não subir um processo sem destino.
        """
        linha = con.execute(
            "SELECT a.id, a.nome, a.ritmo, a.workspace_id, "
            "       p.id AS projeto_id, p.nome AS projeto_nome, p.tipo_nicho_id "
            "  FROM automacoes a JOIN projetos p ON p.id = a.projeto_id "
            " WHERE a.id = ?", (automacao_id,)).fetchone()
        if not linha:
            raise ValueError(f"automação {automacao_id} não existe")

        ritmo = Ritmo()
        try:
            guardado = json.loads(linha["ritmo"] or "{}")
        except (ValueError, TypeError):
            guardado = {}
        for campo in ("envios_por_dia", "inicio_janela", "fim_janela"):
            if isinstance(guardado.get(campo), list) and len(guardado[campo]) == 2:
                setattr(ritmo, campo, tuple(guardado[campo]))
        if isinstance(guardado.get("busca_horas"), list):
            ritmo.busca_horas = list(guardado["busca_horas"])
        for campo in ("validade_horas", "proporcao_preferidas"):
            if isinstance(guardado.get(campo), (int, float)):
                setattr(ritmo, campo, guardado[campo])

        destinos = [
            Destino(id=d["id"], alvo=d["alvo"], nome=d["nome"] or "",
                    conexao_id=d["conexao_id"], ordem=d["ordem"])
            for d in con.execute(
                "SELECT id, alvo, nome, conexao_id, ordem FROM destinos "
                "WHERE automacao_id = ? AND ativo = 1 ORDER BY ordem, criado_em",
                (automacao_id,))
        ]

        # Monitoramento é uma Fonte; o motor lê daqui o que antes vinha do
        # arquivo do perfil.
        clone_grupos, clone_ativo = [], False
        for f in con.execute(
            "SELECT ativa, criterios FROM fontes WHERE automacao_id = ? AND tipo = 'monitoramento'",
            (automacao_id,)):
            try:
                criterios = json.loads(f["criterios"] or "{}")
            except (ValueError, TypeError):
                criterios = {}
            grupos = criterios.get("grupos") or []
            if isinstance(grupos, list):
                clone_grupos.extend(str(g) for g in grupos)
            clone_ativo = clone_ativo or bool(f["ativa"])

        # A fonte de busca traz o que procurar E quando procurar. Sem isto, o
        # usuário configuraria horários na tela da fonte e o motor coletaria
        # em outros — uma configuração que parece funcionar e não funciona.
        fonte_busca_id, criterios_busca = "", {}
        for f in con.execute(
            "SELECT id, ativa, criterios, agenda FROM fontes "
            "WHERE automacao_id = ? AND tipo = 'busca' AND ativa = 1 LIMIT 1",
            (automacao_id,)):
            fonte_busca_id = f["id"]
            try:
                criterios_busca = json.loads(f["criterios"] or "{}")
            except (ValueError, TypeError):
                criterios_busca = {}
            try:
                agenda = json.loads(f["agenda"] or "{}")
            except (ValueError, TypeError):
                agenda = {}
            horarios = agenda.get("horarios")
            if isinstance(horarios, list) and horarios:
                ritmo.busca_horas = [int(h) for h in horarios if isinstance(h, (int, float))]

        return cls(
            workspace_id=linha["workspace_id"],
            projeto_id=linha["projeto_id"],
            projeto_nome=linha["projeto_nome"],
            chave=linha["projeto_id"],
            automacao_id=linha["id"],
            automacao_nome=linha["nome"],
            nicho=linha["tipo_nicho_id"] or "perfumes",
            ritmo=ritmo,
            destinos=destinos,
            clone_ativo=clone_ativo,
            clone_grupos=clone_grupos,
            fonte_busca_id=fonte_busca_id,
            criterios_busca=criterios_busca,
            origem="banco",
        )

    # ── consultas ────────────────────────────────────────────────────

    @property
    def chave_execucao(self) -> str:
        """O que separa DUAS AUTOMAÇÕES do mesmo projeto.

        A oferta pertence ao projeto (duas automações do mesmo nicho veem o
        mesmo catálogo), mas plano do dia, batida de vida e trava de processo
        são de cada automação — senão a segunda automação de um projeto
        roubaria a cota da primeira e as duas disputariam a mesma trava.
        """
        return self.automacao_id or self.chave

    @property
    def destino_principal(self) -> str:
        """O primeiro destino ativo. Mantém funcionando o caminho de quem
        ainda publica em um só — a maioria hoje."""
        return self.destinos[0].alvo if self.destinos else ""

    def pronta_para_publicar(self) -> tuple:
        """(pode, motivo em linguagem comum). O supervisor usa para não subir
        automação que não tem como trabalhar."""
        if not self.destinos:
            return False, "falta escolher para onde publicar"
        return True, ""


def automacoes_ativas(con) -> list:
    """Ids das automações que devem estar rodando agora."""
    return [
        r["id"] for r in con.execute(
            "SELECT a.id FROM automacoes a JOIN projetos p ON p.id = a.projeto_id "
            "WHERE a.estado = 'ativa' AND p.estado = 'ativo' ORDER BY a.criado_em")
    ]
