"""Clone sai na hora; busca própria continua no ritmo."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import Oferta, abrir_banco, gravar_config, salvar_oferta
from mercadolivre import agente


class FilaSoClones(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM ofertas"); self.con.execute("DELETE FROM config")
        self.con.execute("DELETE FROM entregas"); self.con.commit()
        for mlb, origem in (("MLB1", "busca"), ("MLB2", "clone")):
            salvar_oferta(self.con, Oferta(
                mlb_id=mlb, nome=f"Perfume {mlb}", url=f"https://ml.com/{mlb}",
                preco_original=200, preco_promocional=100,
                link_afiliado=f"https://meli.la/{mlb}"))
            self.con.execute("UPDATE ofertas SET origem=? WHERE mlb_id=?", (origem, mlb))
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_so_clones_filtra(self):
        self.assertEqual([f["mlb_id"] for f in agente.fila_de_envio(self.con, 10, so_clones=True)],
                         ["MLB2"])

    def test_sem_filtro_pega_tudo(self):
        self.assertEqual(len(agente.fila_de_envio(self.con, 10)), 2)


class EnvioImediato(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        for t in ("ofertas", "config", "entregas", "estado"):
            self.con.execute(f"DELETE FROM {t}")
        self.con.commit()
        salvar_oferta(self.con, Oferta(
            mlb_id="MLB9", nome="Perfume Clonado", url="https://ml.com/9",
            preco_original=200, preco_promocional=100, link_afiliado="https://meli.la/9"))
        self.con.execute("UPDATE ofertas SET origem='clone' WHERE mlb_id='MLB9'")
        self.con.commit()
        # plano com janela FECHADA agora (00:00–00:01)
        gravar_config(self.con, "ritmo", {"envios_por_dia": [10, 10],
                                          "inicio_janela": [0.0, 0.01],
                                          "fim_janela": [0.02, 0.03],
                                          "busca_horas": [7], "validade_horas": 720,
                                          "proporcao_preferidas": 0.0})

    def tearDown(self):
        self.con.close()

    def test_imediato_ignora_janela_fechada(self):
        with mock.patch.object(agente, "uazapi_enviar", return_value="id1") as env, \
             mock.patch.object(agente, "uazapi_configurado", return_value=True), \
             mock.patch.object(agente, "dormir", return_value=True):
            n = agente.bloco3_enviar(self.con, imediato=True)
        self.assertEqual(n, 1)
        env.assert_called_once()

    def test_ritmo_normal_respeita_janela_fechada(self):
        with mock.patch.object(agente, "uazapi_enviar") as env, \
             mock.patch.object(agente, "uazapi_configurado", return_value=True), \
             mock.patch.object(agente, "dormir", return_value=True):
            n = agente.bloco3_enviar(self.con)
        self.assertEqual(n, 0)
        env.assert_not_called()

    def test_imediato_usa_pausa_curta(self):
        gravar_config(self.con, "clonador", {
            "ativo": True, "grupos": ["1@g.us"], "intervalo_seg": 60,
            "janela_min": 60, "reclonar_apos_horas": 8, "poll_seg": 600,
            "envio_imediato": True, "pausa_clone_seg": [2, 2]})
        with mock.patch.object(agente, "uazapi_enviar", return_value="id1"), \
             mock.patch.object(agente, "uazapi_configurado", return_value=True), \
             mock.patch.object(agente, "dormir", return_value=True) as d:
            agente.bloco3_enviar(self.con, imediato=True)
        self.assertEqual(d.call_args[0][0], 2)   # pausa curta, não 5-15s

    def test_imediato_respeita_cota_do_dia(self):
        # cota é a última defesa contra laço de repetição
        gravar_config(self.con, "ritmo", {"envios_por_dia": [0, 0],
                                          "inicio_janela": [0.0, 0.01],
                                          "fim_janela": [23.9, 23.99],
                                          "busca_horas": [7], "validade_horas": 720,
                                          "proporcao_preferidas": 0.0})
        self.con.execute("DELETE FROM estado")   # força replanejar com cota 0
        self.con.commit()
        with mock.patch.object(agente, "uazapi_enviar") as env, \
             mock.patch.object(agente, "uazapi_configurado", return_value=True), \
             mock.patch.object(agente, "dormir", return_value=True):
            n = agente.bloco3_enviar(self.con, imediato=True)
        self.assertEqual(n, 0)
        env.assert_not_called()
