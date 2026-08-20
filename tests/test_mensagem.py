"""Montagem da mensagem — formato, loja oficial, headlines por contexto."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
# `discover -s tests` importa este módulo SEM rodar tests/__init__.py, então
# o redirecionamento do banco precisa acontecer AQUI, antes de importar o
# núcleo. Aprendido do jeito difícil em 20/08/2026.
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import sys, os, sqlite3, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import nicho
from nucleo.comum import montar_mensagem, grupo_de_headline, linha_da_loja


def linha(**kw):
    """Constrói um sqlite3.Row de verdade, como o publisher recebe."""
    base = dict(nome="Perfume Lattafa Asad 100ml", condicao="", preco_original=369.0,
                preco_promocional=239.0, desconto_pct=35, badge="PROMOÇÃO GERAL",
                link_afiliado="https://meli.la/abc", url="https://ml.com/x",
                loja="", loja_oficial=0)
    base.update(kw)
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    cols = ", ".join(base)
    con.execute(f"CREATE TABLE t ({cols})")
    con.execute(f"INSERT INTO t VALUES ({', '.join('?'*len(base))})", list(base.values()))
    return con.execute("SELECT * FROM t").fetchone()


class Mensagem(unittest.TestCase):
    def setUp(self):
        nicho.usar("perfumes")

    def test_formato_completo(self):
        m = montar_mensagem(linha(loja="Lipx", loja_oficial=1))
        self.assertIn("~R$ 369,00~", m)          # UM til: tachado do WhatsApp
        self.assertIn("*R$ 239,00*", m)
        self.assertIn("Loja Oficial Lipx no ML", m)
        self.assertIn("https://meli.la/abc", m)
        self.assertNotIn("~~", m)                 # dois tis era o bug do n8n

    def test_no_pix_aparece(self):
        m = montar_mensagem(linha(condicao="no Pix"))
        self.assertIn("R$ 239,00 no Pix", m)

    def test_loja_comum_nao_ganha_selo(self):
        self.assertNotIn("Loja Oficial", montar_mensagem(linha(loja="Vendedor X")))
        self.assertEqual(linha_da_loja(linha(loja="")), "\n")

    def test_headline_por_contexto(self):
        self.assertEqual(grupo_de_headline(linha(desconto_pct=50)), "desconto_alto")
        self.assertEqual(grupo_de_headline(linha(desconto_pct=30)), "desconto_medio")
        self.assertEqual(grupo_de_headline(linha(desconto_pct=12)), "geral")
        self.assertEqual(grupo_de_headline(linha(badge="OFERTA RELÂMPAGO")), "relampago")
        self.assertEqual(grupo_de_headline(linha(badge="MAIS VENDIDO")), "mais_vendido")

    def test_titulo_seo_limpo_na_mensagem(self):
        m = montar_mensagem(linha(nome="Perfume Masculino Malbec Black 100ml Novo Lacrado"))
        self.assertIn("*Malbec Black 100ml*", m)
        self.assertNotIn("Lacrado", m)

    def test_titulo_nunca_encolhe_demais(self):
        # regra: a limpeza para antes de deixar menos de 3 palavras
        m = montar_mensagem(linha(nome="Perfume Masculino Malbec 100ml Novo"))
        self.assertIn("Malbec 100ml Novo", m)


if __name__ == "__main__":
    unittest.main()
