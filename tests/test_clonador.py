"""Parser das mensagens do concorrente — formato real do grupo monitorado."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
# `discover -s tests` importa este módulo SEM rodar tests/__init__.py, então
# o redirecionamento do banco precisa acontecer AQUI, antes de importar o
# núcleo. Aprendido do jeito difícil em 20/08/2026.
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mercadolivre.clonador import ler_anuncio_rival, consultas_do_nome, preco_br

MSG_REAL = """NOTURNO NO PRECINHO

*Asad Elixir Lattafa 100ml*

De ~R$369,00~ ❌
Por *R$239,00* ✅

 Loja verificada no ML
🔗 https://meli.la/1GeFaey"""


class Parser(unittest.TestCase):
    def test_mensagem_real_do_rival(self):
        r = ler_anuncio_rival(MSG_REAL)
        self.assertEqual(r["nome"], "Asad Elixir Lattafa 100ml")
        self.assertEqual(r["preco"], 239.0)
        self.assertEqual(r["preco_de"], 369.0)
        self.assertEqual(r["link"], "https://meli.la/1GeFaey")

    def test_conversa_nao_vira_anuncio(self):
        self.assertIsNone(ler_anuncio_rival("bom dia pessoal, tudo bem?"))
        self.assertIsNone(ler_anuncio_rival("*promoção chegando* fiquem ligados"))

    def test_negrito_de_preco_nao_e_nome(self):
        r = ler_anuncio_rival("*Por R$99,00* corre\n*Malbec Black Boticário 100ml*\n"
                              "https://meli.la/abc R$ 99,00")
        self.assertEqual(r["nome"], "Malbec Black Boticário 100ml")

    def test_precos_brasileiros(self):
        self.assertEqual(preco_br("1.234,56"), 1234.56)
        self.assertEqual(preco_br("369,00"), 369.0)
        self.assertEqual(preco_br("99"), 99.0)

    def test_consultas_em_cascata_sem_volume(self):
        c = consultas_do_nome("Club De Nuit Intense Men 105ml")
        self.assertEqual(c, ["Club Nuit Intense", "Club Nuit"])
        self.assertNotIn("105ml", " ".join(c))


if __name__ == "__main__":
    unittest.main()
