"""Filtros por nicho — os casos que já nos morderam em produção."""
import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import nicho
from nucleo.comum import (
    filtrar_titulo, filtrar_marca, filtrar_volume, filtrar_preco,
    familia_da_marca, limpar_titulo, normalizar,
)


class Perfumes(unittest.TestCase):
    def setUp(self):
        nicho.usar("perfumes")

    def test_titulo_qualifica(self):
        self.assertEqual(filtrar_titulo("Perfume Lattafa Asad 100ml"), "")
        self.assertEqual(filtrar_titulo("Lattafa Asad EDP 100ml"), "")   # via regex EDP

    def test_titulo_fora_do_nicho(self):
        self.assertNotEqual(filtrar_titulo("Jogo de Panelas Tramontina 5 peças"), "")

    def test_blacklist(self):
        self.assertEqual(filtrar_titulo("Perfume Difusor de Ambiente 250ml"), "blacklist")

    def test_marca_de_perfume_nao_e_marca(self):
        # Elliur é perfume da Bidaya; Turathi é da Afnan — bug real corrigido
        marca, _, _ = filtrar_marca("", "Perfume Bidaya Elliur 100ml")
        self.assertEqual(marca, "Bidaya")
        marca, _, _ = filtrar_marca("", "Afnan Turathi Blue 90ml")
        self.assertEqual(marca, "Afnan")

    def test_marca_desconhecida_barra(self):
        _, motivo, _ = filtrar_marca("", "Perfume Voker Vonter 100ml")
        self.assertEqual(motivo, "marca não conhecida")

    def test_rotulo_do_ml_vence_titulo(self):
        marca, _, de_onde = filtrar_marca("AL WATANIAH", "Perfume Sedutor Árabe Sabah 100ml")
        self.assertEqual((marca, de_onde), ("Al Wataniah", "rotulo"))

    def test_contratipo_so_nas_casas(self):
        _, motivo, _ = filtrar_marca("", "Perfume Contratipo Inspirado Dior Sauvage 100ml")
        self.assertIn("contratipo", motivo)
        _, motivo, _ = filtrar_marca("", "Lab 8 Contratipo Sauvage 100ml")
        self.assertEqual(motivo, "")

    def test_apelidos_normalizam(self):
        marca, _, _ = filtrar_marca("", "Perfume Dolce & Gabbana Light Blue 100ml")
        self.assertEqual(marca, "Dolce & Gabbana")
        self.assertEqual(familia_da_marca("Paco Rabanne"), "importada")
        self.assertEqual(familia_da_marca("Lattafa"), "arabe")

    def test_volume_exigido_sem_rotulo(self):
        self.assertNotEqual(filtrar_volume("Perfume Lattafa Asad Original"), "")
        self.assertEqual(filtrar_volume("Perfume Lattafa Asad 100ml"), "")

    def test_desconto_minimo_do_nicho(self):
        self.assertEqual(filtrar_preco(100.0, 85.0, 15), "")
        self.assertNotEqual(filtrar_preco(100.0, 95.0, 5), "")

    def test_limpar_titulo_tira_seo_preserva_miolo(self):
        self.assertEqual(
            limpar_titulo("Perfume Ted Lapidus Pour Homme Edt M 100ml Novo Lacrado Original Homem"),
            "Ted Lapidus Pour Homme Edt M 100ml")
        self.assertEqual(limpar_titulo("Natura Hoje Deo-colônia 100 ml Para Mulher"),
                         "Natura Hoje Deo-colônia 100 ml")
        # nunca deixa menos de 3 palavras
        self.assertEqual(limpar_titulo("Perfume 100ml"), "Perfume 100ml")


class Casa(unittest.TestCase):
    def setUp(self):
        nicho.usar("casa")

    def tearDown(self):
        nicho.usar("perfumes")

    def test_panela_passa_perfume_nao(self):
        self.assertEqual(filtrar_titulo("Jogo de Panelas Tramontina 5 peças"), "")
        self.assertNotEqual(filtrar_titulo("Perfume Lattafa Asad 100ml"), "")

    def test_sem_unidade_obrigatoria(self):
        self.assertEqual(filtrar_volume("Cadeira Escritório Ergonômica"), "")

    def test_sem_exigir_marca(self):
        marca, motivo, _ = filtrar_marca("", "Kit 10 Potes Herméticos Vidro 640ml")
        self.assertEqual((marca, motivo), ("", ""))

    def test_desconto_minimo_maior(self):
        self.assertNotEqual(filtrar_preco(100.0, 85.0, 15), "")   # 15% < 25% do nicho
        self.assertEqual(filtrar_preco(100.0, 70.0, 30), "")


class Normalizar(unittest.TestCase):
    def test_acentos_e_pontuacao(self):
        self.assertEqual(normalizar("Dolce & Gabbana"), "dolce gabbana")
        self.assertEqual(normalizar("Réplica  Árabe!"), "replica arabe")


if __name__ == "__main__":
    unittest.main()
