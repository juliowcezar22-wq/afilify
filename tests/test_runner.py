"""Runner multi-perfil — seleção de perfis e regras de supervisão."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.perfil import Perfil, listar, escolher_para_rodar


class Selecao(unittest.TestCase):
    def test_listar_encontra_os_perfis_do_projeto(self):
        nomes = [p.nome for p in listar()]
        self.assertIn("perfumes-ml", nomes)
        self.assertIn("casa-ml-shopee", nomes)

    def test_perfumes_roda_casa_ainda_nao(self):
        rodar, pulados = escolher_para_rodar(listar())
        self.assertIn("perfumes-ml", [p.nome for p in rodar])
        motivo = dict(pulados).get("casa-ml-shopee", "")
        self.assertIn("GRUPO_WHATSAPP", motivo)   # sem grupo definido ainda

    def test_inativo_e_pulado_com_motivo(self):
        perfis = [Perfil(nome="x", ativo=False, grupo_whatsapp="123@g.us"),
                  Perfil(nome="y", ativo=True, grupo_whatsapp="456@g.us")]
        rodar, pulados = escolher_para_rodar(perfis)
        self.assertEqual([p.nome for p in rodar], ["y"])
        self.assertEqual(pulados, [("x", "ATIVO=False")])


if __name__ == "__main__":
    unittest.main()
