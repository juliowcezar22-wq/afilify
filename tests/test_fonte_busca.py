"""
Fonte de busca — a intenção do usuário, validada e aplicada.

O que estes testes protegem:
  · o formulário aceita exatamente quatro campos — parâmetro técnico é
    recusado na borda, não só escondido da tela;
  · toda recusa sai como frase de gente;
  · "não achei nada" explica o que provavelmente apertou demais;
  · bloqueio da plataforma NÃO é confundido com critério apertado.
"""

import os
import sys
import tempfile
import unittest
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "ML_BANCO", os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "fonte.db"))

from nucleo import fonte_busca as fb  # noqa: E402


def criterios(**kw):
    base = {
        "palavras_chave": ["perfume importado"],
        "onde": {"busca": True, "pagina_ofertas": False},
        "desconto_minimo": 20,
        "preco": {"min": None, "max": None},
        "excluir": {"palavras": [], "marcas": []},
    }
    base.update(kw)
    return fb.normalizar(base)


@dataclass
class OfertaFalsa:
    nome: str = "Perfume Lattafa Khamrah 100ml"
    marca: str = "Lattafa"
    desconto_pct: int = 35
    preco_promocional: float = 250.0


class SomenteQuatroCampos(unittest.TestCase):
    def test_parametro_tecnico_e_recusado(self):
        """A proibição vale no contrato, não só na interface."""
        for campo in ("concurrency", "timeout", "paginas", "proxy", "retries", "delay"):
            with self.assertRaises(fb.CriteriosInvalidos, msg=campo):
                fb.normalizar({"palavras_chave": ["x"], "onde": {"busca": True}, campo: 1})

    def test_mensagens_nao_citam_nome_de_campo_interno(self):
        try:
            fb.normalizar({"palavras_chave": ["x"], "onde": {"busca": True}, "concurrency": 8})
        except fb.CriteriosInvalidos as e:
            texto = str(e).lower()
            for termo in ("concurrency", "json", "dict", "campo", "none", "null"):
                self.assertNotIn(termo, texto)

    def test_sem_palavras_pede_palavras(self):
        with self.assertRaises(fb.CriteriosInvalidos) as ctx:
            criterios(palavras_chave=[])
        self.assertIn("palavra-chave", str(ctx.exception))

    def test_palavras_demais_explica_o_porque(self):
        with self.assertRaises(fb.CriteriosInvalidos) as ctx:
            criterios(palavras_chave=[f"termo {i}" for i in range(50)])
        self.assertIn("específicos", str(ctx.exception))

    def test_nenhum_lugar_marcado(self):
        with self.assertRaises(fb.CriteriosInvalidos):
            criterios(onde={"busca": False, "pagina_ofertas": False})

    def test_faixa_invertida(self):
        with self.assertRaises(fb.CriteriosInvalidos) as ctx:
            criterios(preco={"min": 500, "max": 100})
        self.assertIn("maior que o máximo", str(ctx.exception))

    def test_desconto_fora_da_escala(self):
        for valor in (-5, 120, "trinta"):
            with self.assertRaises(fb.CriteriosInvalidos):
                criterios(desconto_minimo=valor)

    def test_espacos_em_branco_somem(self):
        c = criterios(palavras_chave=["  perfume  ", "", "   "])
        self.assertEqual(c["palavras_chave"], ["perfume"])


class FiltroDoUsuario(unittest.TestCase):
    def test_desconto_abaixo_do_pedido(self):
        passa, motivo = fb.aceita(OfertaFalsa(desconto_pct=10), criterios(desconto_minimo=30))
        self.assertFalse(passa)
        self.assertIn("desconto", motivo)

    def test_dentro_da_faixa_passa(self):
        passa, _ = fb.aceita(OfertaFalsa(preco_promocional=250.0),
                             criterios(preco={"min": 100, "max": 400}))
        self.assertTrue(passa)

    def test_acima_da_faixa_nao_passa(self):
        passa, motivo = fb.aceita(OfertaFalsa(preco_promocional=900.0),
                                  criterios(preco={"min": None, "max": 400}))
        self.assertFalse(passa)
        self.assertIn("acima", motivo)

    def test_palavra_excluida(self):
        passa, motivo = fb.aceita(OfertaFalsa(nome="Kit Perfume Lattafa"),
                                  criterios(excluir={"palavras": ["kit"], "marcas": []}))
        self.assertFalse(passa)
        self.assertIn("excluída", motivo)

    def test_marca_excluida_e_exata(self):
        """'Lattafa' excluída não pode derrubar 'Lattafa Pride' por acidente
        — a exclusão de marca compara a marca, não o texto."""
        c = criterios(excluir={"palavras": [], "marcas": ["Bacarati"]})
        self.assertTrue(fb.aceita(OfertaFalsa(marca="Lattafa"), c)[0])
        self.assertFalse(fb.aceita(OfertaFalsa(marca="Bacarati"), c)[0])

    def test_sem_criterios_tudo_passa(self):
        passa, _ = fb.aceita(OfertaFalsa(desconto_pct=1), criterios(desconto_minimo=0))
        self.assertTrue(passa)


class PadraoDoNicho(unittest.TestCase):
    def test_nicho_traz_configuracao_que_ja_funciona(self):
        from nucleo import nicho
        p = fb.padrao_do_nicho(nicho.carregar("perfumes"))
        self.assertTrue(p["palavras_chave"])
        self.assertLessEqual(len(p["palavras_chave"]), 8)
        self.assertTrue(fb.normalizar(p))            # o padrão é sempre válido

    def test_padrao_de_outro_nicho_tambem_vale(self):
        from nucleo import nicho
        self.assertTrue(fb.normalizar(fb.padrao_do_nicho(nicho.carregar("casa"))))


class QuandoNaoVemNada(unittest.TestCase):
    def test_aponta_o_desconto_alto(self):
        texto = fb.por_que_vazio(criterios(desconto_minimo=60))
        self.assertIn("60%", texto)

    def test_aponta_a_faixa_de_preco(self):
        texto = fb.por_que_vazio(criterios(preco={"min": 500, "max": 800}))
        self.assertIn("500", texto)

    def test_sem_aperto_evidente_sugere_palavras(self):
        texto = fb.por_que_vazio(criterios(desconto_minimo=0))
        self.assertIn("palavras-chave", texto)

    def test_varios_apertos_sao_listados(self):
        texto = fb.por_que_vazio(criterios(
            desconto_minimo=50, preco={"min": 500, "max": 800},
            excluir={"palavras": ["kit"], "marcas": []}))
        self.assertIn(" e ", texto)


class Bloqueio(unittest.TestCase):
    def test_pagina_de_verificacao_e_reconhecida(self):
        from mercadolivre import buscador
        for sinal in ("abuse-captcha-mobile-frontend", "captcha/wall/logged",
                      "gz-account-verification-index"):
            self.assertTrue(buscador.foi_bloqueada(f"<html>{sinal}</html>"), sinal)

    def test_pagina_normal_nao_e_bloqueio(self):
        from mercadolivre import buscador
        self.assertFalse(buscador.foi_bloqueada('<html><div class="polycard">…</div></html>'))

    def test_bloqueio_levanta_erro_proprio(self):
        """Confundir bloqueio com 'nada encontrado' faria o usuário caçar um
        defeito nos próprios critérios."""
        from mercadolivre import buscador
        with self.assertRaises(buscador.BuscaBloqueada):
            buscador.contexto_da_busca("<html>captcha/wall/logged</html>")

    def test_mensagem_do_bloqueio_diz_o_que_esperar(self):
        from mercadolivre import buscador
        self.assertIn("minutos", buscador.BuscaBloqueada.mensagem_usuario)


class HistoricoDeColetas(unittest.TestCase):
    def test_resumo_distingue_os_tres_desfechos(self):
        self.assertIn("12", fb.resumo_legivel("ok", 40, 12, ""))
        self.assertIn("não encontrou novidades", fb.resumo_legivel("sem_novidades", 35, 0, ""))
        self.assertIn("bloqueou", fb.resumo_legivel("falhou", 0, 0, "O Mercado Livre bloqueou a busca."))

    def test_singular_e_plural(self):
        self.assertIn("1 oferta nova", fb.resumo_legivel("ok", 5, 1, ""))
        self.assertIn("2 ofertas novas", fb.resumo_legivel("ok", 5, 2, ""))


if __name__ == "__main__":
    unittest.main()
