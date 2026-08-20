"""Dedup e isolamento por perfil — a fila não pode misturar nem duplicar."""
import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import Oferta, abrir_banco, salvar_oferta


def oferta(mlb_id="MLB1", nome="Perfume Lattafa Asad 100ml", **kw):
    base = dict(mlb_id=mlb_id, nome=nome, url=f"https://ml.com/{mlb_id}",
                preco_original=200.0, preco_promocional=150.0, desconto_pct=25,
                marca="Lattafa", link_afiliado="https://meli.la/x")
    base.update(kw)
    return Oferta(**base)


class Dedup(unittest.TestCase):
    def setUp(self):
        self.con = abrir_banco()
        self.con.execute("DELETE FROM ofertas")
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_upsert_por_id_nao_duplica(self):
        self.assertTrue(salvar_oferta(self.con, oferta()))
        self.assertFalse(salvar_oferta(self.con, oferta(preco_promocional=140.0)))
        linhas = self.con.execute("SELECT COUNT(*) n FROM ofertas").fetchone()["n"]
        self.assertEqual(linhas, 1)
        preco = self.con.execute("SELECT preco_promocional p FROM ofertas").fetchone()["p"]
        self.assertEqual(preco, 140.0)   # atualiza o preço…

    def test_upsert_preserva_status_de_envio(self):
        salvar_oferta(self.con, oferta())
        self.con.execute("UPDATE ofertas SET status_envio='ENVIADO'")
        self.con.commit()
        salvar_oferta(self.con, oferta(preco_promocional=99.0))
        status = self.con.execute("SELECT status_envio s FROM ofertas").fetchone()["s"]
        self.assertEqual(status, "ENVIADO")  # …mas nunca reabre sozinho

    def test_mesmo_titulo_outro_id_nao_entra(self):
        # anúncio avulso vs catálogo: ids diferentes, mesmo perfume
        self.assertTrue(salvar_oferta(self.con, oferta("MLB111")))
        self.assertFalse(salvar_oferta(self.con, oferta("MLBU999")))

    def test_perfil_gravado_em_toda_oferta(self):
        salvar_oferta(self.con, oferta())
        p = self.con.execute("SELECT perfil FROM ofertas").fetchone()["perfil"]
        self.assertEqual(p, comum.PERFIL_ATIVO)

    def test_estado_prefixado_por_perfil(self):
        comum.gravar_estado(self.con, "chave_teste", "valor")
        bruto = self.con.execute(
            "SELECT chave FROM estado WHERE chave LIKE '%chave_teste'").fetchone()["chave"]
        self.assertEqual(bruto, f"{comum.PERFIL_ATIVO}:chave_teste")
        self.assertEqual(comum.ler_estado(self.con, "chave_teste"), "valor")


if __name__ == "__main__":
    unittest.main()
