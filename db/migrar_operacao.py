#!/usr/bin/env python3
"""
MIGRAÇÃO DA OPERAÇÃO — do modelo antigo para o modelo novo

Transforma o que existe hoje (perfis em arquivo, ofertas com coluna `perfil`,
entregas por canal) nas entidades do produto: projeto, automação, fonte,
destino, conexão, ofertas e publicações.

    python3 db/migrar_operacao.py            # mostra o que faria, sem gravar
    python3 db/migrar_operacao.py --aplicar  # grava

Duas propriedades que o desenho garante:

  · IDEMPOTENTE. Rodar de novo não duplica nada — cada entidade é procurada
    antes de ser criada, e as ofertas usam a chave (projeto, anúncio).
  · NÃO DESTRUTIVA. Nada do modelo antigo é apagado ou alterado. As tabelas
    `ofertas`, `entregas`, `config` e `estado` continuam exatamente como
    estão, e o motor antigo continua funcionando com elas. Se algo der
    errado, apagar as tabelas novas devolve tudo ao ponto anterior.

Por isso a migração pode rodar com a operação no ar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from nucleo import comum, tipos_nicho  # noqa: E402

# Nome que o usuário vê, para cada perfil que existe hoje. Perfil novo sem
# entrada aqui ganha o nome humanizado do próprio slug.
NOMES = {
    "perfumes-ml": ("Perfumes", "perfumes", "Ofertas Mercado Livre"),
    "casa-ml-shopee": ("Casa", "casa", "Ofertas Mercado Livre e Shopee"),
}

# Status antigo → estado novo. `ERRO` é ambíguo no modelo antigo: guarda
# tanto falha real quanto "ignorada pelo painel", e a diferença está no texto.
def estado_da_oferta(status: str, erro: str) -> str:
    if status == "ENVIADO":
        return "publicada"
    if status == "ERRO":
        return "ignorada" if "ignorada" in (erro or "").lower() else "retida"
    return "pronta"


def humanizar(slug: str) -> str:
    base = slug.split("-")[0]
    return base.replace("_", " ").capitalize()


class Migracao:
    def __init__(self, con, aplicar: bool):
        self.con = con
        self.aplicar = aplicar
        self.ts = comum.agora().isoformat(timespec="seconds")
        self.ws = comum.WORKSPACE_PADRAO
        self.resumo = {}

    def contar(self, chave, n=1):
        self.resumo[chave] = self.resumo.get(chave, 0) + n

    def executar(self, sql, params=()):
        if self.aplicar:
            self.con.execute(sql, params)

    def um(self, sql, params=()):
        linha = self.con.execute(sql, params).fetchone()
        return linha[0] if linha else None

    # ── passos ───────────────────────────────────────────────────────

    def workspace(self):
        existe = self.um("SELECT id FROM workspaces WHERE id = ?", (self.ws,))
        if not existe:
            self.executar(
                "INSERT INTO workspaces (id, nome, criado_em) VALUES (?, ?, ?)",
                (self.ws, "Operação Afilify", self.ts))
            self.contar("workspace criado")

    def tipos_de_nicho(self):
        n = tipos_nicho.semear(self.con) if self.aplicar else len(tipos_nicho.disponiveis())
        if n:
            self.contar("tipos de nicho", n)

    def limites(self):
        if not self.um("SELECT workspace_id FROM limites_plano WHERE workspace_id = ?", (self.ws,)):
            self.executar(
                "INSERT INTO limites_plano (workspace_id, atualizado_em) VALUES (?, ?)",
                (self.ws, self.ts))
            self.contar("limites do plano")

    def conexao_whatsapp(self) -> str:
        """A conta que já publica hoje vira uma Conexão.

        A credencial vem do ambiente (é onde ela vive hoje) e é gravada
        cifrada. Sem chave mestra configurada, a conexão é criada sem
        credencial: ela aparece na tela e pode ser reconectada por lá.
        """
        existente = self.um(
            "SELECT id FROM conexoes WHERE workspace_id = ? AND plataforma = 'whatsapp' LIMIT 1",
            (self.ws,))
        if existente:
            return existente

        cid = str(uuid.uuid4())
        credencial = ""
        token = os.environ.get("UAZAPI_TOKEN", "").strip()
        if token:
            try:
                from nucleo import cripto
                credencial = cripto.cifrar(token, cid)
            except Exception as e:
                print(f"  ! credencial não pôde ser cifrada ({type(e).__name__}) — "
                      f"a conexão será criada sem ela e você reconecta pela tela")

        self.executar(
            "INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, "
            "identificador_externo, credencial_cifrada, metadados, ultimo_estado_em, "
            "motivo_ultima_queda, criado_em, atualizado_em) "
            "VALUES (?, ?, 'whatsapp', ?, ?, '', ?, ?, ?, '', ?, ?)",
            (cid, self.ws, "WhatsApp da operação",
             "conectado" if token else "desconectado", credencial,
             json.dumps({"provisionadaPelaAfilify": False}, ensure_ascii=False),
             self.ts, self.ts, self.ts))
        self.contar("conexão de WhatsApp")
        return cid

    def projeto(self, slug: str) -> tuple:
        nome, nicho, nome_automacao = NOMES.get(
            slug, (humanizar(slug), "perfumes", "Ofertas"))

        pid = self.um("SELECT id FROM projetos WHERE workspace_id = ? AND nome = ?", (self.ws, nome))
        if not pid:
            pid = str(uuid.uuid4())
            self.executar(
                "INSERT INTO projetos (id, workspace_id, nome, tipo_nicho_id, estado, "
                "criado_em, atualizado_em) VALUES (?, ?, ?, ?, 'ativo', ?, ?)",
                (pid, self.ws, nome, nicho, self.ts, self.ts))
            self.contar("projetos")

        aid = self.um("SELECT id FROM automacoes WHERE projeto_id = ?", (pid,))
        if not aid:
            aid = str(uuid.uuid4())
            ritmo = self.config_do_perfil(slug, "ritmo", {})
            mensagem = {
                **self.config_do_perfil(slug, "mensagem", {}),
                "chamadas": self.config_do_perfil(slug, "headlines", {}),
            }
            # Nasce PAUSADA: quem liga é você, depois de conferir que fonte,
            # destino e conexão estão como espera. Migração não liga automação.
            self.executar(
                "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, "
                "motivo_impedida, ritmo, mensagem, criado_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, 'pausada', '', ?, ?, ?, ?)",
                (aid, self.ws, pid, nome_automacao,
                 json.dumps(ritmo, ensure_ascii=False),
                 json.dumps(mensagem, ensure_ascii=False), self.ts, self.ts))
            self.contar("automações")
        return pid, aid

    def config_do_perfil(self, slug: str, chave: str, padrao):
        bruto = self.um("SELECT valor FROM config WHERE perfil = ? AND chave = ?", (slug, chave))
        if not bruto:
            return padrao
        try:
            return json.loads(bruto)
        except (ValueError, TypeError):
            return padrao

    def fonte(self, slug: str, automacao_id: str):
        """Os termos que a operação usa hoje viram os critérios da Fonte."""
        if self.um("SELECT id FROM fontes WHERE automacao_id = ? AND tipo = 'busca'", (automacao_id,)):
            return
        from nucleo import fonte_busca, nicho as mod_nicho
        _, nicho_id, _ = NOMES.get(slug, (None, "perfumes", None))
        criterios = fonte_busca.padrao_do_nicho(mod_nicho.carregar(nicho_id))
        ritmo = self.config_do_perfil(slug, "ritmo", {})
        agenda = {"horarios": ritmo.get("busca_horas") or [7, 15]}
        self.executar(
            "INSERT INTO fontes (id, workspace_id, automacao_id, tipo, ativa, criterios, "
            "agenda, criado_em, atualizado_em) VALUES (?, ?, ?, 'busca', 0, ?, ?, ?, ?)",
            (str(uuid.uuid4()), self.ws, automacao_id,
             json.dumps(criterios, ensure_ascii=False),
             json.dumps(agenda, ensure_ascii=False), self.ts, self.ts))
        self.contar("fontes de busca")

        # Monitoramento, quando ligado no perfil.
        clonador = self.config_do_perfil(slug, "clonador", {})
        grupos = clonador.get("grupos") or []
        if grupos and not self.um(
                "SELECT id FROM fontes WHERE automacao_id = ? AND tipo = 'monitoramento'",
                (automacao_id,)):
            self.executar(
                "INSERT INTO fontes (id, workspace_id, automacao_id, tipo, ativa, criterios, "
                "agenda, criado_em, atualizado_em) VALUES (?, ?, ?, 'monitoramento', ?, ?, '{}', ?, ?)",
                (str(uuid.uuid4()), self.ws, automacao_id, 1 if clonador.get("ativo") else 0,
                 json.dumps({"grupos": grupos}, ensure_ascii=False), self.ts, self.ts))
            self.contar("fontes de monitoramento")

    def destino(self, slug: str, automacao_id: str, conexao_id: str) -> str:
        """O grupo para onde a operação publica hoje."""
        canal = self.config_do_perfil(slug, "canal", {}).get("grupo") or ""
        if not canal:
            canal = self.um("SELECT canal FROM entregas WHERE perfil = ? LIMIT 1", (slug,)) or ""
        if not canal:
            return ""
        existente = self.um(
            "SELECT id FROM destinos WHERE automacao_id = ? AND alvo = ?", (automacao_id, canal))
        if existente:
            return existente
        did = str(uuid.uuid4())
        self.executar(
            "INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, "
            "ordem, ativo, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
            (did, self.ws, automacao_id, conexao_id, canal, "Grupo principal", self.ts, self.ts))
        self.contar("destinos")
        return did

    def ofertas(self, slug: str, projeto_id: str, fonte_id: str = None) -> dict:
        """Cada linha de `ofertas` vira uma oferta do projeto.

        A coluna `perfil` some: a oferta passa a pertencer ao projeto, e a
        identidade é (projeto, identificador do anúncio).
        """
        mapa = {}
        linhas = self.con.execute(
            "SELECT * FROM ofertas WHERE perfil = ? ORDER BY criado_em", (slug,)).fetchall()
        for l in linhas:
            anuncio = l["mlb_id"]
            ja = self.um(
                "SELECT id FROM ofertas_projeto WHERE projeto_id = ? AND identificador_anuncio = ?",
                (projeto_id, anuncio))
            if ja:
                mapa[anuncio] = ja
                continue
            oid = str(uuid.uuid4())
            mapa[anuncio] = oid
            colunas = l.keys()
            def v(nome, padrao=None):
                return l[nome] if nome in colunas else padrao
            self.executar(
                "INSERT INTO ofertas_projeto (id, workspace_id, projeto_id, fonte_id, "
                "identificador_anuncio, nome, url, imagem, titulo_norm, preco_original, "
                "preco_promocional, desconto_pct, marca, familia, condicao, badge, loja, "
                "loja_oficial, vendedor, avaliacao, vendidos, link_afiliado, codigo, origem, "
                "estado, motivo_retencao, validade_ate, criado_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', NULL, ?, ?)",
                (oid, self.ws, projeto_id, None, anuncio, v("nome", ""), v("url", ""),
                 v("imagem", ""), v("titulo_norm", ""), v("preco_original"),
                 v("preco_promocional"), v("desconto_pct"), v("marca", ""), v("familia", ""),
                 v("condicao", ""), v("badge", ""), v("loja", ""), int(v("loja_oficial", 0) or 0),
                 v("vendedor", ""), v("avaliacao", 0) or 0, v("vendidos", ""),
                 v("link_afiliado", ""), v("codigo", ""),
                 "monitoramento" if v("origem") == "clone" else "busca",
                 estado_da_oferta(v("status_envio", ""), v("erro", "")),
                 v("criado_em", self.ts), v("atualizado_em", self.ts)))
            self.contar("ofertas")
        return mapa

    def publicacoes(self, slug: str, projeto_id: str, automacao_id: str,
                    destino_id: str, mapa_ofertas: dict):
        """Cada entrega vira uma publicação, com o histórico preservado."""
        if not destino_id:
            return
        for l in self.con.execute(
                "SELECT * FROM entregas WHERE perfil = ?", (slug,)).fetchall():
            oferta_id = mapa_ofertas.get(l["mlb_id"])
            if not oferta_id:
                continue                      # entrega órfã: a oferta sumiu
            chave = f"{oferta_id}:{destino_id}:1"
            if self.um("SELECT id FROM publicacoes WHERE chave_idempotencia = ?", (chave,)):
                continue
            colunas = l.keys()
            def v(nome, padrao=None):
                return l[nome] if nome in colunas else padrao
            estado = {"enviada": "enviada", "falhou": "falhou"}.get(v("status", ""), "agendada")
            preco = self.um(
                "SELECT preco_enviado FROM ofertas WHERE mlb_id = ?", (l["mlb_id"],))
            self.executar(
                "INSERT INTO publicacoes (id, workspace_id, projeto_id, automacao_id, oferta_id, "
                "destino_id, estado, tentativa, ciclo, chave_idempotencia, preco_publicado, "
                "mensagem_enviada, id_externo, motivo_falha, agendada_para, enviada_em, "
                "criado_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, '', ?, ?, NULL, ?, ?, ?)",
                (str(uuid.uuid4()), self.ws, projeto_id, automacao_id, oferta_id, destino_id,
                 estado, int(v("tentativa", 1) or 1), chave, preco, v("id_externo", ""),
                 v("erro", ""), v("atualizado_em") if estado == "enviada" else None,
                 v("criado_em", self.ts), v("atualizado_em", self.ts)))
            self.contar("publicações")

    # ── orquestração ─────────────────────────────────────────────────

    def rodar(self):
        self.workspace()
        self.tipos_de_nicho()
        self.limites()
        conexao_id = self.conexao_whatsapp()

        perfis = [r[0] for r in self.con.execute(
            "SELECT DISTINCT perfil FROM ofertas WHERE perfil <> '' ORDER BY perfil")]
        if not perfis:
            perfis = [r[0] for r in self.con.execute(
                "SELECT DISTINCT perfil FROM config WHERE perfil <> ''")]

        for slug in perfis:
            print(f"\n  projeto de «{slug}»")
            projeto_id, automacao_id = self.projeto(slug)
            self.fonte(slug, automacao_id)
            destino_id = self.destino(slug, automacao_id, conexao_id)
            mapa = self.ofertas(slug, projeto_id)
            self.publicacoes(slug, projeto_id, automacao_id, destino_id, mapa)

        if self.aplicar:
            self.con.commit()
        return self.resumo


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aplicar", action="store_true",
                   help="grava de verdade (sem isto, só mostra o que faria)")
    args = p.parse_args()

    con = comum.abrir_banco()
    print("═" * 62)
    print("  MIGRAÇÃO DA OPERAÇÃO" + ("" if args.aplicar else "  ·  SIMULAÇÃO (nada é gravado)"))
    print("═" * 62)

    resumo = Migracao(con, args.aplicar).rodar()

    print("\n" + "─" * 62)
    if not resumo:
        print("  nada a migrar — o modelo novo já está em dia")
    for chave, n in resumo.items():
        print(f"  {n:>6}  {chave}")
    print("─" * 62)
    if args.aplicar:
        print("\n  Pronto. As automações nasceram PAUSADAS: confira fonte,")
        print("  destino e conexão no painel antes de ligar.")
    else:
        print("\n  Para gravar:  python3 db/migrar_operacao.py --aplicar")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
