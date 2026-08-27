"""
Publicação e proteção da conta.

Três coisas que o modelo antigo não conseguia e estes testes protegem:
  · a mesma oferta em dois destinos
  · a mesma oferta de novo, quando o preço cai
  · nenhuma das duas abrindo brecha para mensagem repetida no grupo

E o teto de segurança, que existe porque duas automações no mesmo número
somam um volume que nenhuma delas tem sozinha.
"""

import os
import sys
import tempfile
import unittest
import uuid
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "ML_BANCO", os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "pub.db"))

from nucleo import comum, contexto, protecao, publicacao  # noqa: E402

AGORA_ISO = "2026-08-27T14:00:00-03:00"


class Base(unittest.TestCase):
    def setUp(self):
        comum.BANCO = os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "t.db")
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = comum.abrir_banco()
        self.projeto, self.automacao = str(uuid.uuid4()), str(uuid.uuid4())
        self.conexao = str(uuid.uuid4())
        self.con.execute(
            "INSERT INTO projetos (id, workspace_id, nome, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', 'P', 'ativo', ?, ?)", (self.projeto, AGORA_ISO, AGORA_ISO))
        self.con.execute(
            "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, 'A', 'ativa', ?, ?)",
            (self.automacao, self.projeto, AGORA_ISO, AGORA_ISO))
        self.con.execute(
            "INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, ultimo_estado_em, "
            "criado_em, atualizado_em) VALUES (?, 'ws-afilify', 'whatsapp', 'C', 'conectado', ?, ?, ?)",
            (self.conexao, AGORA_ISO, AGORA_ISO, AGORA_ISO))
        self.oferta = self._oferta()
        self.principal = self._destino("1203@g.us", "Principal", 0)
        self.vip = self._destino("1204@g.us", "VIP", 1)
        self.con.commit()
        self.ctx = contexto.Contexto(
            workspace_id="ws-afilify", projeto_id=self.projeto, automacao_id=self.automacao,
            destinos=[contexto.Destino(id=self.principal, alvo="1203@g.us", nome="Principal", ordem=0),
                      contexto.Destino(id=self.vip, alvo="1204@g.us", nome="VIP", ordem=1)])

    def tearDown(self):
        self.con.close()

    def _oferta(self):
        oid = str(uuid.uuid4())
        self.con.execute(
            "INSERT INTO ofertas_projeto (id, workspace_id, projeto_id, identificador_anuncio, "
            "nome, url, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, ?, 'Perfume X', 'u', 'pronta', ?, ?)",
            (oid, self.projeto, "MLB" + oid[:6], AGORA_ISO, AGORA_ISO))
        return oid

    def _destino(self, alvo, nome, ordem):
        did = str(uuid.uuid4())
        self.con.execute(
            "INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, ordem, "
            "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, ?, ?, ?, ?, ?, ?)",
            (did, self.automacao, self.conexao, alvo, nome, ordem, AGORA_ISO, AGORA_ISO))
        return did


class DoisDestinos(Base):
    def test_uma_oferta_gera_uma_publicacao_por_destino(self):
        criadas = publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, comum.agora(), 250.0)
        self.assertEqual(len(criadas), 2)

    def test_destinos_saem_espacados(self):
        """Três grupos no mesmo segundo é o padrão que derruba número."""
        momento = comum.agora()
        publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, momento, 250.0,
                                    intervalo_seg=protecao.INTERVALO_ENTRE_DESTINOS_SEG)
        horarios = [r["agendada_para"] for r in self.con.execute(
            "SELECT agendada_para FROM publicacoes ORDER BY agendada_para")]
        self.assertEqual(len(set(horarios)), 2)

    def test_agendar_de_novo_nao_duplica(self):
        """Coleta repetida ou processo reiniciado não vira mensagem repetida."""
        publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, comum.agora(), 250.0)
        segunda = publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, comum.agora(), 250.0)
        self.assertEqual(segunda, [])
        n = self.con.execute("SELECT COUNT(*) AS n FROM publicacoes").fetchone()["n"]
        self.assertEqual(n, 2)

    def test_cada_destino_tem_resultado_proprio(self):
        ids = publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, comum.agora(), 250.0)
        publicacao.concluir(self.con, ids[0], "msg-1")
        publicacao.falhar(self.con, ids[1], "O grupo não aceita mensagens de quem não é membro.")
        estados = {r["estado"] for r in self.con.execute("SELECT estado FROM publicacoes")}
        self.assertEqual(estados, {"enviada", "falhou"})


class SemEnvioDuplo(Base):
    def test_dois_processos_nao_enviam_a_mesma(self):
        pid = publicacao.agendar(self.con, self.ctx, self.oferta, self.principal, comum.agora(), 250.0)
        self.assertTrue(publicacao.marcar_enviando(self.con, pid))
        self.assertFalse(publicacao.marcar_enviando(self.con, pid))

    def test_publicacao_falha_volta_para_a_fila(self):
        pid = publicacao.agendar(self.con, self.ctx, self.oferta, self.principal, comum.agora(), 250.0)
        publicacao.marcar_enviando(self.con, pid)
        publicacao.falhar(self.con, pid, "A conexão caiu no meio do envio.")
        self.assertTrue(publicacao.repetir(self.con, pid))
        self.assertFalse(publicacao.repetir(self.con, pid))   # já está na fila

    def test_tentativa_e_contada(self):
        pid = publicacao.agendar(self.con, self.ctx, self.oferta, self.principal, comum.agora(), 250.0)
        publicacao.falhar(self.con, pid, "erro")
        n = self.con.execute("SELECT tentativa FROM publicacoes WHERE id = ?", (pid,)).fetchone()["tentativa"]
        self.assertEqual(n, 2)


class RepeticaoPorQuedaDePreco(Base):
    def _publicar(self, preco, ciclo=1):
        pid = publicacao.agendar(self.con, self.ctx, self.oferta, self.principal,
                                 comum.agora(), preco, ciclo=ciclo)
        publicacao.concluir(self.con, pid, f"msg-{ciclo}")
        return pid

    def test_queda_relevante_permite_republicar(self):
        self._publicar(300.0)
        self.assertTrue(publicacao.deve_republicar(self.con, self.oferta, self.principal, 240.0))

    def test_oscilacao_pequena_nao_republica(self):
        """Sem isso, o grupo viraria repetição a cada centavo de variação."""
        self._publicar(300.0)
        self.assertFalse(publicacao.deve_republicar(self.con, self.oferta, self.principal, 295.0))

    def test_preco_subindo_nao_republica(self):
        self._publicar(300.0)
        self.assertFalse(publicacao.deve_republicar(self.con, self.oferta, self.principal, 350.0))

    def test_nunca_publicada_nao_e_republicacao(self):
        self.assertFalse(publicacao.deve_republicar(self.con, self.oferta, self.principal, 100.0))

    def test_ciclo_novo_permite_a_segunda_saida(self):
        self._publicar(300.0)
        novo = publicacao.abrir_ciclo(self.con, self.oferta, self.principal)
        self.assertEqual(novo, 2)
        pid = publicacao.agendar(self.con, self.ctx, self.oferta, self.principal,
                                 comum.agora(), 240.0, ciclo=novo)
        self.assertIsNotNone(pid)

    def test_mesmo_ciclo_continua_bloqueado(self):
        self._publicar(300.0)
        repetida = publicacao.agendar(self.con, self.ctx, self.oferta, self.principal,
                                      comum.agora(), 240.0, ciclo=1)
        self.assertIsNone(repetida)


class TetoDeSeguranca(Base):
    def _enviar(self, quantas, destino=None):
        for i in range(quantas):
            o = self._oferta()
            self.con.commit()
            pid = publicacao.agendar(self.con, self.ctx, o, destino or self.principal,
                                     comum.agora(), 100.0)
            publicacao.concluir(self.con, pid, f"m{i}")

    def test_abaixo_do_teto_pode_enviar(self):
        self._enviar(3)
        pode, motivo = protecao.pode_enviar(self.con, self.conexao, "ws-afilify")
        self.assertTrue(pode)
        self.assertEqual(motivo, "")

    def test_no_teto_segura_e_explica(self):
        self.con.execute(
            "INSERT INTO limites_plano (workspace_id, teto_envios_conexao_hora, atualizado_em) "
            "VALUES ('ws-afilify', 5, ?) ON CONFLICT (workspace_id) DO UPDATE SET "
            "teto_envios_conexao_hora = 5", (AGORA_ISO,))
        self.con.commit()
        self._enviar(5)
        pode, motivo = protecao.pode_enviar(self.con, self.conexao, "ws-afilify")
        self.assertFalse(pode)
        self.assertIn("proteger", motivo)
        self.assertNotIn("teto", motivo.lower())      # linguagem de produto

    def test_teto_conta_a_conexao_inteira_nao_a_automacao(self):
        """Duas automações no mesmo número somam — é o número que paga."""
        self.con.execute(
            "INSERT INTO limites_plano (workspace_id, teto_envios_conexao_hora, atualizado_em) "
            "VALUES ('ws-afilify', 4, ?) ON CONFLICT (workspace_id) DO UPDATE SET "
            "teto_envios_conexao_hora = 4", (AGORA_ISO,))
        self.con.commit()
        self._enviar(2, self.principal)
        self._enviar(2, self.vip)
        pode, _ = protecao.pode_enviar(self.con, self.conexao, "ws-afilify")
        self.assertFalse(pode)

    def test_envio_antigo_nao_conta(self):
        self._enviar(3)
        self.con.execute(
            "UPDATE publicacoes SET enviada_em = ?",
            ((comum.agora() - timedelta(hours=3)).isoformat(timespec="seconds"),))
        self.con.commit()
        self.assertEqual(protecao.enviadas_na_ultima_hora(self.con, self.conexao), 0)


class Fila(Base):
    def test_fila_respeita_o_horario_agendado(self):
        momento = comum.agora()
        publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, momento, 250.0,
                                    intervalo_seg=600)
        prontas = publicacao.fila(self.con, self.automacao, momento)
        self.assertEqual(len(prontas), 1)          # o segundo destino ainda espera

    def test_fila_traz_o_nome_do_destino(self):
        publicacao.agendar_em_todos(self.con, self.ctx, self.oferta, comum.agora(), 250.0)
        prontas = publicacao.fila(self.con, self.automacao, comum.agora())
        self.assertIn(prontas[0]["destino_nome"], {"Principal", "VIP"})


if __name__ == "__main__":
    unittest.main()


class OfertaRetida(Base):
    """Nada se perde por falha de infraestrutura (FR-042, SC-006)."""

    def setUp(self):
        super().setUp()
        from nucleo import oferta
        self.oferta_mod = oferta

    def test_retida_guarda_o_motivo(self):
        self.oferta_mod.reter(self.con, self.oferta, self.oferta_mod.CONEXAO_ML)
        r = self.con.execute(
            "SELECT estado, motivo_retencao FROM ofertas_projeto WHERE id = ?",
            (self.oferta,)).fetchone()
        self.assertEqual(r["estado"], "retida")
        self.assertEqual(r["motivo_retencao"], self.oferta_mod.CONEXAO_ML)

    def test_retida_nao_e_erro_e_volta_sozinha(self):
        self.oferta_mod.reter_todas(self.con, self.projeto, self.oferta_mod.CONEXAO_ML)
        liberadas = self.oferta_mod.liberar(self.con, self.projeto, self.oferta_mod.CONEXAO_ML)
        self.assertEqual(liberadas, 1)
        estado = self.con.execute(
            "SELECT estado FROM ofertas_projeto WHERE id = ?", (self.oferta,)).fetchone()["estado"]
        self.assertEqual(estado, "pronta")

    def test_liberar_um_motivo_nao_solta_o_outro(self):
        """Reconectar o WhatsApp não pode soltar ofertas que esperam link."""
        outra = self._oferta()
        self.con.commit()
        self.oferta_mod.reter(self.con, self.oferta, self.oferta_mod.CONEXAO_ML)
        self.oferta_mod.reter(self.con, outra, self.oferta_mod.CONEXAO_DESTINO)
        self.oferta_mod.liberar(self.con, self.projeto, self.oferta_mod.CONEXAO_DESTINO)
        estados = {r["id"]: r["estado"] for r in self.con.execute(
            "SELECT id, estado FROM ofertas_projeto")}
        self.assertEqual(estados[self.oferta], "retida")
        self.assertEqual(estados[outra], "pronta")

    def test_frase_da_retencao_e_acionavel(self):
        frase = self.oferta_mod.frase_da_retencao(self.oferta_mod.CONEXAO_ML)
        self.assertIn("Reconecte", frase)
        self.assertNotIn("_", frase)

    def test_motivo_desconhecido_nao_vira_codigo_na_tela(self):
        frase = self.oferta_mod.frase_da_retencao("erro_xyz_42")
        self.assertNotIn("xyz", frase)

    def test_vencida_sai_como_expirada_nao_como_erro(self):
        self.con.execute(
            "UPDATE ofertas_projeto SET criado_em = ? WHERE id = ?",
            ((comum.agora() - timedelta(hours=100)).isoformat(timespec="seconds"), self.oferta))
        self.con.commit()
        n = self.oferta_mod.expirar_vencidas(self.con, self.projeto, 48)
        self.assertEqual(n, 1)
        estado = self.con.execute(
            "SELECT estado FROM ofertas_projeto WHERE id = ?", (self.oferta,)).fetchone()["estado"]
        self.assertEqual(estado, "expirada")

    def test_oferta_nova_nao_expira(self):
        self.assertEqual(self.oferta_mod.expirar_vencidas(self.con, self.projeto, 48), 0)
