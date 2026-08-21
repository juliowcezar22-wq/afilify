"""coletar(): o daemon varre TODOS os marketplaces do perfil ativo."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo import perfil
from nucleo.comum import abrir_banco
from mercadolivre import agente


class Coleta(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self._antes = perfil._ativo

    def tearDown(self):
        perfil._ativo = self._antes
        self.con.close()

    def test_perfumes_nao_chama_shopee(self):
        perfil.usar("perfumes_ml")
        with mock.patch.object(agente, "bloco1_buscar") as ml, \
             mock.patch("shopee.buscador.buscar") as shp:
            agente.coletar(self.con, paginas=1)
        ml.assert_called_once()
        shp.assert_not_called()

    def test_casa_chama_ml_e_shopee(self):
        perfil.usar("casa_ml_shopee")
        with mock.patch.object(agente, "bloco1_buscar") as ml, \
             mock.patch("shopee.buscador.buscar") as shp:
            agente.coletar(self.con, paginas=1)
        ml.assert_called_once()
        shp.assert_called_once_with(self.con)

    def test_shopee_quebrada_nao_derruba_a_coleta(self):
        perfil.usar("casa_ml_shopee")
        with mock.patch.object(agente, "bloco1_buscar"), \
             mock.patch("shopee.buscador.buscar", side_effect=RuntimeError("api fora")):
            agente.coletar(self.con, paginas=1)   # não pode levantar
