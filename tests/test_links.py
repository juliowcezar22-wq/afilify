"""BLOCO 2: quem já desistiu (ERRO) fica desistido."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import abrir_banco, Oferta, salvar_oferta
from mercadolivre import buscador


class Bloco2NaoRessuscitaErro(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM ofertas"); self.con.commit()
        salvar_oferta(self.con, Oferta(mlb_id="MLB1", nome="Pendente OK",
            url="https://ml.com/a", preco_original=100, preco_promocional=80))
        salvar_oferta(self.con, Oferta(mlb_id="MLB2", nome="Ja desistido",
            url="https://ml.com/b", preco_original=100, preco_promocional=80))
        self.con.execute(
            "UPDATE ofertas SET status_envio='ERRO', tentativas=5 WHERE mlb_id='MLB2'")
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_erro_fora_do_lote(self):
        with mock.patch.object(buscador, "gerar_links", return_value={}) as g:
            buscador.bloco2_links(self.con)
        urls = g.call_args[0][0]
        self.assertEqual(len(urls), 1)
        self.assertIn("ml.com/a", urls[0])

    def test_quinta_recusa_desiste_de_verdade(self):
        self.con.execute("UPDATE ofertas SET tentativas=4 WHERE mlb_id='MLB1'")
        self.con.commit()
        with mock.patch.object(buscador, "gerar_links", return_value={}):
            buscador.bloco2_links(self.con)     # 5ª recusa → ERRO
            buscador.bloco2_links(self.con)     # e o ERRO não volta ao lote
        linha = self.con.execute(
            "SELECT status_envio, tentativas FROM ofertas WHERE mlb_id='MLB1'").fetchone()
        self.assertEqual(linha["status_envio"], "ERRO")
        self.assertEqual(linha["tentativas"], 5)
