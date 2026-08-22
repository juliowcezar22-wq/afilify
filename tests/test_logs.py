"""Logs no banco: espelhamento best-effort de info/ok/aviso/erro."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import abrir_banco


class LogsNoBanco(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM logs"); self.con.commit()

    def tearDown(self):
        comum._LOG_CON = None
        self.con.close()

    def test_sem_registro_nao_grava(self):
        comum.info("linha solta")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 0)

    def test_registrado_espelha_com_nivel_e_perfil(self):
        comum.registrar_logs_no_banco()
        comum.ok("enviada com sucesso")
        comum.erro("algo falhou")
        linhas = self.con.execute("SELECT nivel, texto, perfil FROM logs ORDER BY id").fetchall()
        self.assertEqual([(l["nivel"], l["texto"]) for l in linhas],
                         [("✓", "enviada com sucesso"), ("✗", "algo falhou")])
        self.assertEqual(linhas[0]["perfil"], comum.PERFIL_ATIVO)

    def test_log_quebrado_nao_derruba(self):
        comum.registrar_logs_no_banco()
        comum._LOG_CON.close()          # simula conexão morta
        comum.aviso("ainda vivo")       # não pode levantar exceção
