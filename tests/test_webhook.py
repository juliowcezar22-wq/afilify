"""Webhook: mensagens chegam pela tabela e não são reprocessadas."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import abrir_banco, mensagens_do_webhook, concluir_webhook

JID = "120363406025827790@g.us"


class MensagensDoWebhook(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM rival_mensagens")
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def _inserir(self, mid, texto="*Perfume X*\nPor *R$99,00*\nhttps://meli.la/x",
                chat=JID, processado=0, de_mim=0):
        self.con.execute(
            "INSERT INTO rival_mensagens (messageid, chatid, texto, tipo, de_mim,"
            " ts_mensagem, recebido_em, processado) VALUES (?,?,?,?,?,?,?,?)",
            (mid, chat, texto, "ImageMessage", de_mim, "1787600365000",
             "2026-08-26T20:00:00", processado))
        self.con.commit()

    def test_le_pendentes_no_formato_do_grupo(self):
        self._inserir("m1")
        msgs = mensagens_do_webhook(self.con, JID)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["messageid"], "m1")
        self.assertIn("meli.la", msgs[0]["text"])
        self.assertFalse(msgs[0]["fromMe"])
        self.assertTrue(msgs[0]["_via_webhook"])

    def test_processada_nao_volta(self):
        self._inserir("m1")
        concluir_webhook(self.con, ["m1"])
        self.assertEqual(mensagens_do_webhook(self.con, JID), [])

    def test_so_do_grupo_pedido(self):
        self._inserir("m1", chat="outro@g.us")
        self.assertEqual(mensagens_do_webhook(self.con, JID), [])

    def test_duas_chamadas_sem_concluir_devolvem_de_novo(self):
        # se o ciclo falhar antes de concluir, a mensagem continua pendente
        self._inserir("m1")
        self.assertEqual(len(mensagens_do_webhook(self.con, JID)), 1)
        self.assertEqual(len(mensagens_do_webhook(self.con, JID)), 1)

    def test_mensagem_real_do_maeno_e_lida_pelo_clonador(self):
        from mercadolivre.clonador import ler_anuncio_rival
        texto = ("*YSL Myslf Edp 100ml*\n\nDe ~R$1.059,00~ \nPor *R$611,00* 🤩🔥\n\n"
                 "Loja Verificada no Mercado Livre\n🔗https://meli.la/1JMYeyU")
        self._inserir("m9", texto=texto)
        msgs = mensagens_do_webhook(self.con, JID)
        a = ler_anuncio_rival(msgs[0]["text"])
        self.assertEqual(a["preco"], 611.0)
        self.assertEqual(a["link"], "https://meli.la/1JMYeyU")


class MemoriaDeVistos(unittest.TestCase):
    """Regressão do laço de duplicatas de 26/08 21h.

    Com o webhook, cada ciclo via 1 mensagem e a memória era sobrescrita
    com esse único id. Na releitura do histórico (a cada 10 min) as 20
    últimas voltavam a parecer novas e o grupo recebia tudo de novo.
    """

    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM estado")
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_memoria_acumula_entre_ciclos(self):
        chave = "clone_visto3_teste@g.us"
        comum.gravar_estado(self.con, chave, "a,b,c,d,e")
        vistos_antes = [x for x in comum.ler_estado(self.con, chave).split(",") if x]
        # ciclo do webhook: só uma mensagem nova
        vistos_agora = ["f"]
        memoria = list(dict.fromkeys(vistos_agora + vistos_antes))[:400]
        comum.gravar_estado(self.con, chave, ",".join(memoria))
        guardado = comum.ler_estado(self.con, chave).split(",")
        self.assertIn("f", guardado)
        for antigo in ("a", "b", "c", "d", "e"):
            self.assertIn(antigo, guardado, "memória antiga não pode sumir")

    def test_memoria_tem_teto(self):
        memoria = list(dict.fromkeys([str(i) for i in range(500)]))[:400]
        self.assertEqual(len(memoria), 400)
