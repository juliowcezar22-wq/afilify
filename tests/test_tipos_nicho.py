"""
Tipos de nicho — nucleo/tipos_nicho.py

O que protegem: a curadoria que impede publicar falsificação continua íntegra
ao virar dado, a semeadura não sobrescreve o que já existe, e termos de busca
NÃO vazam para a curadoria (eles pertencem à Fonte, escolhida pelo usuário).
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ML_BANCO", os.path.join(tempfile.mkdtemp(), "tipos.db"))

from nucleo import comum, tipos_nicho  # noqa: E402


class Semeadura(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        comum.BANCO = os.path.join(self.pasta, "teste.db")
        self.con = comum.abrir_banco()

    def tearDown(self):
        self.con.close()

    def test_semeia_os_nichos_do_repositorio(self):
        n = tipos_nicho.semear(self.con)
        self.assertGreaterEqual(n, 2)              # perfumes e casa, no mínimo
        ids = {t["id"] for t in tipos_nicho.listar(self.con)}
        self.assertIn("perfumes", ids)
        self.assertIn("casa", ids)

    def test_idempotente(self):
        tipos_nicho.semear(self.con)
        self.assertEqual(tipos_nicho.semear(self.con), 0)

    def test_forcar_sobe_a_versao(self):
        tipos_nicho.semear(self.con)
        antes = tipos_nicho.listar(self.con)[0]["versao"]
        tipos_nicho.semear(self.con, forcar=True)
        depois = tipos_nicho.listar(self.con)[0]["versao"]
        self.assertEqual(depois, antes + 1)

    def test_rotulo_humano_nunca_e_slug(self):
        tipos_nicho.semear(self.con)
        for t in tipos_nicho.listar(self.con):
            self.assertNotIn("_", t["nome"])
            self.assertNotIn("-ml", t["nome"])
            self.assertEqual(t["nome"][0], t["nome"][0].upper())

    def test_nicho_desconhecido_ganha_rotulo_legivel(self):
        self.assertEqual(tipos_nicho.rotulo("eletronicos_leves"), "Eletronicos leves")


class Curadoria(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        comum.BANCO = os.path.join(self.pasta, "teste.db")
        self.con = comum.abrir_banco()
        tipos_nicho.semear(self.con)

    def tearDown(self):
        self.con.close()

    def test_marcas_aceitas_sobrevivem_a_travessia(self):
        """A lista de marcas é o que separa oferta legítima de paralela —
        perdê-la na migração seria publicar falsificação com o link do usuário."""
        c = tipos_nicho.curadoria(self.con, "perfumes")
        marcas = c["marcas_aceitas"]
        todas = {m.lower() for lista in marcas.values() for m in lista}
        self.assertGreater(len(todas), 100)
        self.assertIn("lattafa", todas)
        self.assertIn("natura", todas)

    def test_palavras_proibidas_preservadas(self):
        c = tipos_nicho.curadoria(self.con, "perfumes")
        self.assertGreater(len(c["palavras_proibidas"]), 10)

    def test_contratipo_so_para_familias_permitidas(self):
        """Contratipo é aceito em casa nacional e recusado em grife — a regra
        que evita publicar 'inspirado em' de marca importada."""
        c = tipos_nicho.curadoria(self.con, "perfumes")
        self.assertTrue(c["contratipo"]["termos"])
        self.assertTrue(c["contratipo"]["familias_permitidas"])

    def test_termos_de_busca_nao_sao_curadoria_de_qualidade(self):
        """Os termos viraram configuração da Fonte (D28). Ficam guardados como
        semente, mas nunca como critério de qualidade."""
        c = tipos_nicho.curadoria(self.con, "perfumes")
        self.assertIn("termos_semente", c)
        self.assertNotIn("termos", c)
        self.assertNotIn("palavras_chave", c)

    def test_nicho_inexistente_devolve_vazio(self):
        self.assertEqual(tipos_nicho.curadoria(self.con, "inexistente"), {})

    def test_curadoria_e_json_valido(self):
        linha = self.con.execute(
            "SELECT curadoria FROM tipos_nicho WHERE id = 'perfumes'").fetchone()
        json.loads(linha["curadoria"])


if __name__ == "__main__":
    unittest.main()
