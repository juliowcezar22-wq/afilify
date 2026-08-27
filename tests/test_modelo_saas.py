"""
Modelo do núcleo SaaS — as regras de integridade que o schema promete.

Cada teste aqui existe porque a estrutura ANTIGA não comportava o caso:
  · a mesma oferta em dois projetos colidia na chave primária global
  · a mesma oferta em dois destinos era impossível (chave mlb_id+canal)
  · republicar após queda de preço era impossível pela mesma razão
"""

import os
import sqlite3
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "ML_BANCO", os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "modelo.db"))

from nucleo import comum  # noqa: E402

AGORA = "2026-08-27T10:00:00-03:00"


def novo_id() -> str:
    return str(uuid.uuid4())


class BaseModelo(unittest.TestCase):
    def setUp(self):
        comum.BANCO = os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "teste.db")
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = comum.abrir_banco()
        self.con.execute("PRAGMA foreign_keys = ON")
        self.projeto_a = self._projeto("Perfumes")
        self.projeto_b = self._projeto("Casa")

    def tearDown(self):
        self.con.close()

    def _projeto(self, nome: str) -> str:
        pid = novo_id()
        self.con.execute(
            "INSERT INTO projetos (id, workspace_id, nome, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, 'ativo', ?, ?)", (pid, nome, AGORA, AGORA))
        return pid

    def _oferta(self, projeto: str, anuncio: str, nome: str = "Perfume X") -> str:
        oid = novo_id()
        self.con.execute(
            "INSERT INTO ofertas_projeto (id, workspace_id, projeto_id, identificador_anuncio, "
            "nome, url, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, ?, ?, 'https://x', 'nova', ?, ?)",
            (oid, projeto, anuncio, nome, AGORA, AGORA))
        return oid

    def _automacao(self, projeto: str) -> str:
        aid = novo_id()
        self.con.execute(
            "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, 'Ofertas', 'ativa', ?, ?)", (aid, projeto, AGORA, AGORA))
        return aid

    def _conexao(self) -> str:
        cid = novo_id()
        self.con.execute(
            "INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, "
            "ultimo_estado_em, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', 'whatsapp', 'Principal', 'conectado', ?, ?, ?)",
            (cid, AGORA, AGORA, AGORA))
        return cid

    def _destino(self, automacao: str, alvo: str) -> str:
        did = novo_id()
        self.con.execute(
            "INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, "
            "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, ?, ?, ?, ?, ?)",
            (did, automacao, self._conexao(), alvo, "Grupo " + alvo[-2:], AGORA, AGORA))
        return did

    def _publicar(self, projeto, automacao, oferta, destino, ciclo=1, tentativa=1):
        pid = novo_id()
        self.con.execute(
            "INSERT INTO publicacoes (id, workspace_id, projeto_id, automacao_id, oferta_id, "
            "destino_id, estado, tentativa, ciclo, chave_idempotencia, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, ?, ?, ?, 'agendada', ?, ?, ?, ?, ?)",
            (pid, projeto, automacao, oferta, destino, tentativa, ciclo,
             f"{oferta}:{destino}:{ciclo}", AGORA, AGORA))
        return pid


class IdentidadeDaOferta(BaseModelo):
    def test_mesma_oferta_existe_em_dois_projetos(self):
        """No modelo antigo os dois projetos brigavam pela mesma linha."""
        a = self._oferta(self.projeto_a, "MLB123")
        b = self._oferta(self.projeto_b, "MLB123")
        self.con.commit()
        self.assertNotEqual(a, b)
        n = self.con.execute(
            "SELECT COUNT(*) AS n FROM ofertas_projeto WHERE identificador_anuncio = 'MLB123'"
        ).fetchone()["n"]
        self.assertEqual(n, 2)

    def test_mesma_oferta_duas_vezes_no_mesmo_projeto_e_recusada(self):
        self._oferta(self.projeto_a, "MLB123")
        self.con.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self._oferta(self.projeto_a, "MLB123")
            self.con.commit()

    def test_estado_invalido_e_recusado(self):
        """Estado fora do conjunto não entra — nada de 'PENDENTE' antigo."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO ofertas_projeto (id, workspace_id, projeto_id, "
                "identificador_anuncio, nome, url, estado, criado_em, atualizado_em) "
                "VALUES (?, 'ws-afilify', ?, 'X', 'n', 'u', 'PENDENTE', ?, ?)",
                (novo_id(), self.projeto_a, AGORA, AGORA))
            self.con.commit()

    def test_isolamento_entre_projetos_na_consulta(self):
        self._oferta(self.projeto_a, "MLB1", "Só de perfumes")
        self._oferta(self.projeto_b, "MLB2", "Só de casa")
        self.con.commit()
        nomes = [r["nome"] for r in self.con.execute(
            "SELECT nome FROM ofertas_projeto WHERE projeto_id = ?", (self.projeto_a,))]
        self.assertEqual(nomes, ["Só de perfumes"])


class PublicacaoEmVariosDestinos(BaseModelo):
    def setUp(self):
        super().setUp()
        self.automacao = self._automacao(self.projeto_a)
        self.oferta = self._oferta(self.projeto_a, "MLB999")
        self.principal = self._destino(self.automacao, "1203634@g.us")
        self.vip = self._destino(self.automacao, "1203635@g.us")
        self.con.commit()

    def test_mesma_oferta_em_dois_destinos(self):
        """Impossível no modelo antigo: a chave era (oferta, canal)."""
        self._publicar(self.projeto_a, self.automacao, self.oferta, self.principal)
        self._publicar(self.projeto_a, self.automacao, self.oferta, self.vip)
        self.con.commit()
        n = self.con.execute(
            "SELECT COUNT(*) AS n FROM publicacoes WHERE oferta_id = ?", (self.oferta,)
        ).fetchone()["n"]
        self.assertEqual(n, 2)

    def test_publicacao_duplicada_no_mesmo_ciclo_e_recusada(self):
        """A proteção contra envio duplo que a chave antiga dava de graça."""
        self._publicar(self.projeto_a, self.automacao, self.oferta, self.principal)
        self.con.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self._publicar(self.projeto_a, self.automacao, self.oferta, self.principal)
            self.con.commit()

    def test_queda_de_preco_abre_ciclo_novo(self):
        """Republicar após queda de preço (D31), sem abrir brecha para duplicata."""
        self._publicar(self.projeto_a, self.automacao, self.oferta, self.principal, ciclo=1)
        self.con.commit()
        self._publicar(self.projeto_a, self.automacao, self.oferta, self.principal, ciclo=2)
        self.con.commit()
        n = self.con.execute(
            "SELECT COUNT(*) AS n FROM publicacoes WHERE oferta_id = ? AND destino_id = ?",
            (self.oferta, self.principal)).fetchone()["n"]
        self.assertEqual(n, 2)

    def test_destino_repetido_na_mesma_automacao_e_recusado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self._destino(self.automacao, "1203634@g.us")
            self.con.commit()

    def test_historico_sobrevive_a_troca_de_destino(self):
        """Trocar o destino da automação não apaga o que já foi publicado (FR-007)."""
        self._publicar(self.projeto_a, self.automacao, self.oferta, self.principal)
        self.con.commit()
        self.con.execute("UPDATE destinos SET ativo = 0 WHERE id = ?", (self.principal,))
        self.con.commit()
        n = self.con.execute(
            "SELECT COUNT(*) AS n FROM publicacoes WHERE destino_id = ?", (self.principal,)
        ).fetchone()["n"]
        self.assertEqual(n, 1)


class Integridade(BaseModelo):
    def test_projeto_precisa_existir(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self._oferta("projeto-que-nao-existe", "MLB1")
            self.con.commit()

    def test_nome_de_projeto_e_unico_no_workspace(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self._projeto("Perfumes")
            self.con.commit()

    def test_automacao_com_estado_invalido_e_recusada(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, "
                "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, 'X', 'ligada', ?, ?)",
                (novo_id(), self.projeto_a, AGORA, AGORA))
            self.con.commit()

    def test_conexao_com_plataforma_invalida_e_recusada(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, "
                "ultimo_estado_em, criado_em, atualizado_em) "
                "VALUES (?, 'ws-afilify', 'telegram', 'X', 'conectado', ?, ?, ?)",
                (novo_id(), AGORA, AGORA, AGORA))
            self.con.commit()

    def test_comando_com_tipo_invalido_e_recusado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO comandos (id, workspace_id, tipo, expira_em, criado_em, atualizado_em) "
                "VALUES (?, 'ws-afilify', 'formatar_disco', ?, ?, ?)",
                (novo_id(), AGORA, AGORA, AGORA))
            self.con.commit()


if __name__ == "__main__":
    unittest.main()
