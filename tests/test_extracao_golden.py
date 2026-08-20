"""Extração do ML contra HTML real congelado — o canário do scraping.

Se o ML mudar o layout, estes testes quebram ANTES da produção quebrar
em silêncio. Fixtures re-capturáveis com tests/fixtures/capturar.py.
"""
import sys, os, gzip, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import nicho
from mercadolivre.buscador import (
    extrair_contexto, extrair_ofertas_json, contexto_da_busca,
)

AQUI = os.path.dirname(os.path.abspath(__file__))


def fixture(nome):
    return gzip.open(os.path.join(AQUI, "fixtures", nome), "rt", encoding="utf-8").read()


class Vitrine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nicho.usar("perfumes")
        cls.ctx = extrair_contexto(fixture("vitrine.html.gz"))

    def test_estado_embutido_presente(self):
        self.assertIsNotNone(self.ctx)
        self.assertGreaterEqual(len(self.ctx["items"]), 40)
        self.assertIn("total", self.ctx["paging"])

    def test_extracao_completa(self):
        ofertas, _ = extrair_ofertas_json(self.ctx, set())
        self.assertGreaterEqual(len(ofertas), 10)
        for o in ofertas:
            self.assertRegex(o.mlb_id, r"^MLBU?\d+$")
            self.assertTrue(o.url.startswith("https://"))
            self.assertGreater(o.preco_original, o.preco_promocional)
            self.assertGreaterEqual(o.desconto_pct, 10)
            self.assertTrue(o.imagem.startswith("https://http2.mlstatic.com/"))
            self.assertNotIn("mclics", o.url)      # pixel de anúncio nunca passa

    def test_dedup_intra_execucao(self):
        vistos = set()
        a, _ = extrair_ofertas_json(self.ctx, vistos)
        b, _ = extrair_ofertas_json(self.ctx, vistos)
        self.assertEqual(len(b), 0)


class Busca(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nicho.usar("perfumes")
        cls.ctx = contexto_da_busca(fixture("busca.html.gz"))

    def test_payload_escapado_decodifica(self):
        self.assertIsNotNone(self.ctx)
        self.assertGreaterEqual(len(self.ctx["items"]), 50)

    def test_ids_unicos_e_validos(self):
        ofertas, _ = extrair_ofertas_json(self.ctx, set())
        self.assertGreaterEqual(len(ofertas), 8)
        ids = [o.mlb_id for o in ofertas]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
