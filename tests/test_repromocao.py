"""Re-promoção por queda de preço (§10) + regressão da ligação perfil→config."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, subprocess, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import (
    Oferta, abrir_banco, agora, salvar_oferta, reservar_entrega,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def oferta(preco: float, **kw):
    base = dict(mlb_id="MLBR1", nome="Perfume Lattafa Repromo 100ml",
                url="https://ml.com/r", preco_original=400.0,
                preco_promocional=preco, desconto_pct=30, marca="Lattafa")
    base.update(kw)
    return Oferta(**base)


class Repromocao(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM ofertas")
        self.con.execute("DELETE FROM entregas")
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def _enviada_a(self, preco: float):
        """Oferta no estado pós-envio: ENVIADO + preco_enviado + entrega selada."""
        salvar_oferta(self.con, oferta(preco))
        ts = agora().isoformat(timespec="seconds")
        self.con.execute(
            "UPDATE ofertas SET status_envio='ENVIADO', enviado_em=?, "
            "preco_enviado=? WHERE mlb_id='MLBR1'", (ts, preco))
        self.con.commit()
        reservar_entrega(self.con, "MLBR1", "g@g.us")
        self.con.execute("UPDATE entregas SET status='enviada'")
        self.con.commit()

    def _status(self):
        return self.con.execute(
            "SELECT status_envio FROM ofertas WHERE mlb_id='MLBR1'").fetchone()["status_envio"]

    def test_queda_relevante_reabre_e_libera_entrega(self):
        self._enviada_a(200.0)
        salvar_oferta(self.con, oferta(160.0))          # −20% vs preço enviado
        self.assertEqual(self._status(), "PENDENTE")
        n = self.con.execute("SELECT COUNT(*) n FROM entregas").fetchone()["n"]
        self.assertEqual(n, 0)                           # trava de duplicata liberada
        self.assertTrue(reservar_entrega(self.con, "MLBR1", "g@g.us"))

    def test_queda_pequena_nao_reabre(self):
        self._enviada_a(200.0)
        salvar_oferta(self.con, oferta(185.0))          # −7,5% < 15%
        self.assertEqual(self._status(), "ENVIADO")

    def test_linha_antiga_sem_preco_enviado_nao_reabre(self):
        # as 156 enviadas de antes desta feature têm preco_enviado NULL:
        # só entram no jogo depois do PRÓXIMO envio selar o preço da época
        self._enviada_a(200.0)
        self.con.execute("UPDATE ofertas SET preco_enviado=NULL")
        self.con.commit()
        salvar_oferta(self.con, oferta(100.0))          # −50%, mas sem base
        self.assertEqual(self._status(), "ENVIADO")

    def test_pendente_so_atualiza_preco(self):
        salvar_oferta(self.con, oferta(200.0))
        salvar_oferta(self.con, oferta(120.0))
        self.assertEqual(self._status(), "PENDENTE")
        n = self.con.execute("SELECT COUNT(*) n FROM entregas").fetchone()["n"]
        self.assertEqual(n, 0)


class LigacaoPerfilConfig(unittest.TestCase):
    """Regressão do fio morto de 20/08: valores derivados do perfil eram
    sombreados pelas constantes. O teste usa o perfil de CASA porque os
    valores dele DIFEREM das constantes — coincidência não passa."""

    def test_config_vem_do_perfil(self):
        saida = subprocess.run(
            [sys.executable, "-c",
             "import sys;sys.path.insert(0,'.');import nucleo.comum as m;"
             "print(m.ENVIOS_POR_DIA, m.BUSCA_HORAS, m.VALIDADE_HORAS, m.PROPORCAO_IMPORTADOS)"],
            capture_output=True, text=True, cwd=RAIZ,
            env={**os.environ, "PERFIL": "casa_ml_shopee",
                 "ML_BANCO": os.environ["ML_BANCO"]},
        ).stdout.strip()
        self.assertEqual(saida, "(40, 60) [8, 14, 20] 72 0.0")


if __name__ == "__main__":
    unittest.main()
