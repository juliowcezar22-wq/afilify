"""Cadência de envio — o ativo mais valioso do projeto, congelado em teste."""
import sys, os, random, statistics, unittest
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.comum import TZ
from mercadolivre.agente import (
    sortear_intervalo, ritmo, fim_do_ciclo, hora_do_dia, dentro_da_janela,
)

PLANO = {"data": "2026-08-20", "cota": 100, "inicio": 9.0, "fim": 22.0}


def em(h, m=0):
    return datetime(2026, 8, 20, h, m, tzinfo=TZ)


class Cadencia(unittest.TestCase):
    def test_media_do_sorteio_converge_para_base(self):
        random.seed(42)
        for base in (5.0, 7.0, 21.0):
            amostra = [sortear_intervalo(base) for _ in range(20000)]
            self.assertAlmostEqual(statistics.mean(amostra), base, delta=base * 0.06)

    def test_forma_lognormal_tem_rajadas_e_cauda(self):
        random.seed(7)
        amostra = [sortear_intervalo(7.0) for _ in range(20000)]
        rajadas = sum(1 for x in amostra if x < 2) / len(amostra)
        cauda = sum(1 for x in amostra if x > 20) / len(amostra)
        self.assertGreater(rajadas, 0.08)   # MAENO real: 13%
        self.assertLess(rajadas, 0.20)
        self.assertGreater(cauda, 0.02)     # MAENO real: 5%

    def test_ritmo_espalha_cota_pelo_dia(self):
        # fila gigante de manhã NÃO pode acelerar além da cota do dia
        base = ritmo(None, em(9), fila=500, resta_dia=780, resta_ciclo=180,
                     cota_total=100, ja_enviadas=0)
        self.assertGreaterEqual(base, 780 / 100 * 0.99)

    def test_ritmo_espalha_fila_pelo_ciclo(self):
        # fila curta desacelera para o grupo não ficar mudo até a próxima coleta
        base = ritmo(None, em(9), fila=3, resta_dia=780, resta_ciclo=240,
                     cota_total=100, ja_enviadas=0)
        self.assertGreaterEqual(base, 240 / 3 * 0.99)

    def test_cota_esgotada_para(self):
        self.assertIsNone(ritmo(None, em(20), fila=50, resta_dia=120,
                                resta_ciclo=120, cota_total=100, ja_enviadas=100))

    def test_janela(self):
        self.assertFalse(dentro_da_janela(em(8, 59), PLANO))
        self.assertTrue(dentro_da_janela(em(12), PLANO))
        self.assertFalse(dentro_da_janela(em(22, 1), PLANO))

    def test_fim_do_ciclo_respeita_coletas_e_janela(self):
        # BUSCA_HORAS do perfil ativo é [7, 15]
        self.assertEqual(fim_do_ciclo(em(9), PLANO).hour, 15)
        self.assertEqual(fim_do_ciclo(em(16), PLANO).hour, 22)

    def test_hora_do_dia_fracionaria(self):
        t = hora_do_dia(em(9), 8.75)
        self.assertEqual((t.hour, t.minute), (8, 45))


if __name__ == "__main__":
    unittest.main()
