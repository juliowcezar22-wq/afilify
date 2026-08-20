"""Idempotência de publicação — reserva, retry e reconciliação pós-crash."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import (
    Oferta, abrir_banco, agora, salvar_oferta,
    reservar_entrega, concluir_entrega, falhar_entrega, reconciliar_entregas,
)

CANAL = "grupo-teste@g.us"


class Entregas(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM ofertas")
        self.con.execute("DELETE FROM entregas")
        self.con.commit()
        salvar_oferta(self.con, Oferta(
            mlb_id="MLBX1", nome="Perfume Lattafa Teste 100ml",
            url="https://ml.com/x", preco_original=200.0,
            preco_promocional=150.0, desconto_pct=25,
            link_afiliado="https://meli.la/UNICO123"))
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_reserva_e_exclusiva(self):
        self.assertTrue(reservar_entrega(self.con, "MLBX1", CANAL))
        self.assertFalse(reservar_entrega(self.con, "MLBX1", CANAL))  # 2ª execução: barrada

    def test_enviada_nunca_reenvia(self):
        reservar_entrega(self.con, "MLBX1", CANAL)
        concluir_entrega(self.con, "MLBX1", "id-wpp-123", CANAL)
        self.assertFalse(reservar_entrega(self.con, "MLBX1", CANAL))

    def test_falha_permite_retry(self):
        reservar_entrega(self.con, "MLBX1", CANAL)
        falhar_entrega(self.con, "MLBX1", "uazapi 500", CANAL)
        self.assertTrue(reservar_entrega(self.con, "MLBX1", CANAL))   # retry reutiliza
        t = self.con.execute("SELECT tentativa FROM entregas WHERE mlb_id='MLBX1'"
                             ).fetchone()["tentativa"]
        self.assertEqual(t, 2)

    def _prender_entrega(self):
        """Simula o crash: reserva feita há 20min, sem conclusão."""
        reservar_entrega(self.con, "MLBX1", CANAL)
        velho = (agora() - timedelta(minutes=20)).isoformat(timespec="seconds")
        self.con.execute("UPDATE entregas SET atualizado_em=?", (velho,))
        self.con.commit()

    def test_crash_com_mensagem_no_grupo_sela(self):
        self._prender_entrega()
        # o grupo TEM a mensagem (link único presente) → não reenviar nunca
        fake = lambda canal, n=50: [{"text": "oferta boa https://meli.la/UNICO123 corre"}]
        self.assertEqual(reconciliar_entregas(self.con, buscar=fake), 1)
        e = self.con.execute("SELECT status FROM entregas WHERE mlb_id='MLBX1'").fetchone()
        o = self.con.execute("SELECT status_envio FROM ofertas WHERE mlb_id='MLBX1'").fetchone()
        self.assertEqual((e["status"], o["status_envio"]), ("enviada", "ENVIADO"))

    def test_crash_sem_mensagem_reenfileira(self):
        self._prender_entrega()
        fake = lambda canal, n=50: [{"text": "nada a ver"}]
        self.assertEqual(reconciliar_entregas(self.con, buscar=fake), 1)
        e = self.con.execute("SELECT COUNT(*) n FROM entregas").fetchone()["n"]
        o = self.con.execute("SELECT status_envio FROM ofertas WHERE mlb_id='MLBX1'").fetchone()
        self.assertEqual(e, 0)                              # reserva liberada
        self.assertEqual(o["status_envio"], "PENDENTE")     # volta à fila

    def test_recente_nao_e_tocada(self):
        reservar_entrega(self.con, "MLBX1", CANAL)          # acabou de reservar
        self.assertEqual(reconciliar_entregas(self.con, buscar=lambda c, n=50: []), 0)


if __name__ == "__main__":
    unittest.main()
