"""
Migração da operação — db/migrar_operacao.py

Esta migração roda uma vez, no banco de produção, com a operação no ar. O
que estes testes protegem:

  · o modelo antigo sai INTOCADO — se algo der errado, apagar as tabelas
    novas devolve tudo ao ponto anterior;
  · rodar de novo não duplica nada;
  · o histórico chega inteiro: cada oferta e cada entrega viram registro no
    modelo novo, com o estado traduzido corretamente;
  · a automação nasce PAUSADA — migração não liga operação sozinha.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault(
    "ML_BANCO", os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "mig.db"))

from nucleo import comum  # noqa: E402
from db.migrar_operacao import Migracao, estado_da_oferta, humanizar  # noqa: E402

# Relativo ao relógio: data cravada envelhece e o teste passa a falhar
# sozinho dias depois, sem nada ter mudado no código.
AGORA = comum.agora().isoformat(timespec="seconds")
GRUPO = "120363408117538302@g.us"


class Base(unittest.TestCase):
    def setUp(self):
        comum.BANCO = os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "t.db")
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = comum.abrir_banco()
        self._semear_modelo_antigo()

    def tearDown(self):
        self.con.close()

    def _semear_modelo_antigo(self):
        """Reproduz a forma do banco de produção antes da migração."""
        # Os quatro desfechos que existem no banco de produção, incluindo os
        # DOIS tipos de ERRO — falha real e "ignorada pelo painel" — que o
        # modelo antigo guardava misturados.
        casos = [
            ("ENVIADO", "", "busca"),
            ("PENDENTE", "", "busca"),
            ("ERRO", "ignorada pelo painel", "busca"),
            ("ERRO", "afiliado: anúncio recusado pelo createLink", "clone"),
            ("ENVIADO", "", "clone"),
        ]
        for i, (status, erro, origem) in enumerate(casos):
            self.con.execute(
                "INSERT INTO ofertas (mlb_id, nome, url, preco_original, preco_promocional, "
                "desconto_pct, marca, origem, perfil, status_envio, erro, criado_em, atualizado_em) "
                "VALUES (?, ?, 'https://x', 300.0, 200.0, 33, 'Lattafa', ?, 'perfumes-ml', ?, ?, ?, ?)",
                (f"MLB{i}", f"Perfume {i}", origem, status, erro, AGORA, AGORA))
        for i in range(3):
            self.con.execute(
                "INSERT INTO entregas (mlb_id, canal, perfil, status, tentativa, id_externo, "
                "erro, criado_em, atualizado_em) VALUES (?, ?, 'perfumes-ml', ?, 1, ?, '', ?, ?)",
                (f"MLB{i}", GRUPO, "enviada" if i < 2 else "falhou", f"msg{i}", AGORA, AGORA))
        for chave, valor in [
            ("canal", {"grupo": GRUPO}),
            ("ritmo", {"envios_por_dia": [95, 135], "busca_horas": [7, 15], "validade_horas": 48}),
            ("clonador", {"ativo": True, "grupos": ["120363406025827790@g.us"]}),
            ("mensagem", {"base": "{nome} {link} {preco_promocional}"}),
            ("headlines", {"geral": ["OLHA O PREÇO"]}),
        ]:
            self.con.execute(
                "INSERT INTO config (perfil, chave, valor, atualizado_em) VALUES (?, ?, ?, ?)",
                ("perfumes-ml", chave, json.dumps(valor), AGORA))
        self.con.commit()

    def migrar(self, aplicar=True):
        return Migracao(self.con, aplicar).rodar()


class ModeloAntigoIntocado(Base):
    def test_nada_do_antigo_e_alterado(self):
        antes = {
            t: self.con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            for t in ("ofertas", "entregas", "config")
        }
        self.migrar()
        depois = {
            t: self.con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            for t in ("ofertas", "entregas", "config")
        }
        self.assertEqual(antes, depois)

    def test_status_das_ofertas_antigas_nao_muda(self):
        """O motor antigo continua rodando com elas durante a transição."""
        antes = sorted(r["status_envio"] for r in self.con.execute("SELECT status_envio FROM ofertas"))
        self.migrar()
        depois = sorted(r["status_envio"] for r in self.con.execute("SELECT status_envio FROM ofertas"))
        self.assertEqual(antes, depois)


class HistoricoCompleto(Base):
    def test_toda_oferta_vira_registro_no_modelo_novo(self):
        self.migrar()
        antigas = self.con.execute("SELECT COUNT(*) AS n FROM ofertas").fetchone()["n"]
        novas = self.con.execute("SELECT COUNT(*) AS n FROM ofertas_projeto").fetchone()["n"]
        self.assertEqual(antigas, novas)

    def test_toda_entrega_vira_publicacao(self):
        self.migrar()
        entregas = self.con.execute("SELECT COUNT(*) AS n FROM entregas").fetchone()["n"]
        publicacoes = self.con.execute("SELECT COUNT(*) AS n FROM publicacoes").fetchone()["n"]
        self.assertEqual(entregas, publicacoes)

    def test_clone_vira_monitoramento(self):
        """'clone' era vocabulário interno; no produto é monitoramento."""
        self.migrar()
        origens = {r["origem"] for r in self.con.execute("SELECT origem FROM ofertas_projeto")}
        self.assertEqual(origens, {"busca", "monitoramento"})

    def test_ritmo_da_operacao_e_preservado(self):
        self.migrar()
        ritmo = json.loads(self.con.execute("SELECT ritmo FROM automacoes").fetchone()["ritmo"])
        self.assertEqual(ritmo["envios_por_dia"], [95, 135])
        self.assertEqual(ritmo["busca_horas"], [7, 15])

    def test_grupo_de_destino_e_preservado(self):
        self.migrar()
        alvo = self.con.execute("SELECT alvo FROM destinos").fetchone()["alvo"]
        self.assertEqual(alvo, GRUPO)

    def test_monitoramento_vira_fonte(self):
        self.migrar()
        f = self.con.execute(
            "SELECT criterios FROM fontes WHERE tipo = 'monitoramento'").fetchone()
        self.assertIn("120363406025827790@g.us", f["criterios"])


class TraducaoDeEstados(Base):
    def test_enviado_vira_publicada(self):
        self.assertEqual(estado_da_oferta("ENVIADO", ""), "publicada")

    def test_pendente_vira_pronta(self):
        self.assertEqual(estado_da_oferta("PENDENTE", ""), "pronta")

    def test_erro_de_verdade_vira_retida(self):
        """Retida, não perdida: a oferta continua na fila esperando a causa."""
        self.assertEqual(estado_da_oferta("ERRO", "uazapi 500"), "retida")

    def test_ignorada_pelo_painel_vira_ignorada(self):
        """O modelo antigo guardava as duas coisas em ERRO; aqui elas se separam."""
        self.assertEqual(estado_da_oferta("ERRO", "ignorada pelo painel"), "ignorada")

    def test_separacao_acontece_de_fato_na_migracao(self):
        self.migrar()
        estados = dict(self.con.execute(
            "SELECT estado, COUNT(*) FROM ofertas_projeto GROUP BY estado").fetchall())
        self.assertIn("ignorada", estados)
        self.assertIn("retida", estados)


class NaoLigaSozinha(Base):
    def test_automacao_nasce_pausada(self):
        self.migrar()
        estado = self.con.execute("SELECT estado FROM automacoes").fetchone()["estado"]
        self.assertEqual(estado, "pausada")

    def test_fonte_de_busca_nasce_desligada(self):
        self.migrar()
        ativa = self.con.execute(
            "SELECT ativa FROM fontes WHERE tipo = 'busca'").fetchone()["ativa"]
        self.assertEqual(ativa, 0)


class Idempotencia(Base):
    def test_rodar_duas_vezes_nao_duplica(self):
        self.migrar()
        contagem = lambda: {
            t: self.con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            for t in ("projetos", "automacoes", "fontes", "destinos",
                      "conexoes", "ofertas_projeto", "publicacoes")
        }
        antes = contagem()
        self.migrar()
        self.assertEqual(antes, contagem())

    def test_segunda_execucao_nao_reporta_trabalho(self):
        self.migrar()
        self.assertEqual(self.migrar(), {})

    def test_simulacao_nao_grava(self):
        self.migrar(aplicar=False)
        n = self.con.execute("SELECT COUNT(*) AS n FROM projetos").fetchone()["n"]
        self.assertEqual(n, 0)


class NomesDeProduto(Base):
    def test_slug_vira_nome_de_gente(self):
        self.migrar()
        nome = self.con.execute("SELECT nome FROM projetos").fetchone()["nome"]
        self.assertEqual(nome, "Perfumes")
        self.assertNotIn("-ml", nome)

    def test_slug_desconhecido_ganha_nome_legivel(self):
        self.assertEqual(humanizar("eletronicos-ml"), "Eletronicos")


class CompatibilidadePostgres(unittest.TestCase):
    """O DDL roda igual nos dois bancos — mas só o SQLite foi exercitado aqui.

    Estes testes cobrem o que é possível cobrir sem um servidor: a divisão
    por `;` que o adaptador de Postgres faz, e a ausência de sintaxe que só
    o SQLite aceita.
    """

    ARQUIVOS = ["db/0009_entidades.sql", "db/0010_ofertas_publicacoes.sql"]

    def _sql(self, arquivo):
        with open(os.path.join(RAIZ, arquivo), encoding="utf-8") as f:
            return f.read()

    def test_divisao_por_ponto_e_virgula_nao_gera_fragmento_vazio(self):
        """O adaptador divide o arquivo por `;` — um fragmento que sobra só
        com comentário viraria um statement vazio no Postgres."""
        import re
        for arquivo in self.ARQUIVOS:
            for i, parte in enumerate(self._sql(arquivo).split(";")):
                if not parte.strip():
                    continue
                limpo = re.sub(r"--[^\n]*", "", parte).strip()
                self.assertTrue(limpo, f"{arquivo}: fragmento {i} é só comentário")

    def test_nenhum_comentario_contem_ponto_e_virgula(self):
        for arquivo in self.ARQUIVOS:
            for n, linha in enumerate(self._sql(arquivo).splitlines(), 1):
                c = linha.find("--")
                if c >= 0:
                    self.assertNotIn(";", linha[c:], f"{arquivo}:{n}")

    def test_sem_sintaxe_exclusiva_do_sqlite(self):
        proibidos = ["AUTOINCREMENT", "PRAGMA", "WITHOUT ROWID", "INTEGER PRIMARY KEY AUTOINCREMENT"]
        for arquivo in self.ARQUIVOS:
            sql = self._sql(arquivo).upper()
            for termo in proibidos:
                self.assertNotIn(termo, sql, f"{arquivo} usa {termo}, que o Postgres não aceita")

    def test_sem_tipos_que_o_postgres_recusa(self):
        """SQLite aceita qualquer nome de tipo; o Postgres não."""
        import re
        validos = {"TEXT", "INTEGER", "BIGINT", "DOUBLE PRECISION", "REAL", "BOOLEAN",
                   "TIMESTAMP", "NUMERIC", "BIGSERIAL", "SERIAL", "JSONB"}
        for arquivo in self.ARQUIVOS:
            for linha in self._sql(arquivo).splitlines():
                m = re.match(r"\s+(\w+)\s+([A-Z][A-Z ]*?)(\s+(NOT|PRIMARY|REFERENCES|DEFAULT|CHECK|UNIQUE)|,|$)", linha)
                if m and m.group(2).strip():
                    tipo = m.group(2).strip()
                    self.assertIn(tipo, validos, f"{arquivo}: tipo {tipo!r} em {linha.strip()[:50]!r}")


if __name__ == "__main__":
    unittest.main()
