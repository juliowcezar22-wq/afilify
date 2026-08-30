"""Clone literal: link bruto da vitrine, mensagem verbatim, foto exata."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import gzip, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import abrir_banco, montar_mensagem, Oferta, salvar_oferta
from mercadolivre.clonador import (anuncio_bruto_na_vitrine,
                                   anuncio_marcado_na_vitrine, oferta_do_clone)
from mercadolivre.buscador import foto_para_envio

AQUI = os.path.dirname(os.path.abspath(__file__))


def vitrine_real() -> str:
    with gzip.open(os.path.join(AQUI, "fixtures", "vitrine-maeno-spectre.html.gz"),
                   "rt", encoding="utf-8") as f:
        return f.read()


class AnuncioBruto(unittest.TestCase):
    TITULO = "Perfume Spectre Ghost Fragrance World Eau De Parfum 80ml Masculino"

    def test_vitrine_real_do_rival(self):
        url, prova = anuncio_bruto_na_vitrine(vitrine_real(), self.TITULO)
        self.assertIn("/p/MLB27861230", url)
        self.assertIn("spectre-ghost", url)
        self.assertNotIn("matt_", url)          # limpa tracking do ML

    def test_titulo_decide_nao_a_posicao(self):
        # regressão do caso Salvo→Gaby: o 1º link do HTML é OUTRO produto
        html = ('<a href="https://www.mercadolivre.com.br/perfume-gaby-paris-elysees-feminino/p/MLB111">'
                '<a href="https://www.mercadolivre.com.br/perfume-maison-alhambra-salvo-edp-100ml/p/MLB222">')
        url, prova = anuncio_bruto_na_vitrine(html, "Perfume Maison Alhambra Salvo Edp 100ml")
        self.assertIn("MLB222", url)
        self.assertIn("salvo", url)
        self.assertEqual(prova, "slug")

    def test_prova_fotografica_vence_o_slug(self):
        # foto do produto referenciado está no card do 2º link — ele vence
        # mesmo com slug ilegível
        html = ('<img src="D_NQ_NP_2X_777777-AAA-F.webp">'
                '<a href="https://www.mercadolivre.com.br/x-y-z/p/MLB111">'
                '<div><img src="D_NQ_NP_2X_ABC123-MLA-F.webp">'
                '<a href="https://www.mercadolivre.com.br/a-b-c/p/MLB222"></div>')
        url, prova = anuncio_bruto_na_vitrine(html, "Nada A Ver", id_foto="ABC123-MLA")
        self.assertIn("MLB222", url)
        self.assertEqual(prova, "foto")

    def test_preco_nao_reprova_mais(self):
        # medido no laboratório: o preço da vitrine muda em minutos, nos dois
        # sentidos. Usá-lo como prova reprovava anúncio certo.
        html = ('<a href="https://www.mercadolivre.com.br/perfume-salvo-edp-100ml/p/MLB222">'
                ' R$ 899,00 ')
        url, prova = anuncio_bruto_na_vitrine(html, "Perfume Salvo Edp 100ml")
        self.assertIn("MLB222", url)
        self.assertEqual(prova, "slug")

    def test_sem_casamento_decente_devolve_vazio(self):
        html = '<a href="https://www.mercadolivre.com.br/perfume-gaby-paris-elysees/p/MLB111">'
        url, prova = anuncio_bruto_na_vitrine(html, "Lattafa Asad Bourbon 100ml")
        self.assertEqual(url, "")
        self.assertIn("slug não casa", prova)

    def test_sem_titulo_devolve_vazio(self):
        url, prova = anuncio_bruto_na_vitrine(vitrine_real(), "")
        self.assertEqual(url, "")

    def test_sem_anuncio_devolve_vazio(self):
        url, _ = anuncio_bruto_na_vitrine("<html>nada</html>", self.TITULO)
        self.assertEqual(url, "")


class MarcadorDoML(unittest.TestCase):
    """O card cuja origem é ÚNICA na página é o item compartilhado."""

    def _card(self, uid, item, produto, backend, slug):
        return ('{"unique_id":"' + uid + '","metadata":{"id":"' + item + '",'
                '"product_id":"' + produto + '","url":"www.mercadolivre.com.br/' + slug + '",'
                '"url_fragments":"#reco_backend=' + backend + '"},"components":[]}')

    def test_acha_o_unico_diferente(self):
        html = "".join([
            self._card("a", "MLB1", "MLB11", "ranker_retrieval_system_vpp_v2p", "x/p/MLB11"),
            self._card("b", "MLB2", "MLB22", "item_decorator", "salvo/p/MLB22"),
            self._card("c", "MLB3", "MLB33", "ranker_retrieval_system_vpp_v2p", "y/p/MLB33"),
        ])
        achado = anuncio_marcado_na_vitrine(html)
        self.assertEqual(achado["item_id"], "MLB2")
        self.assertIn("MLB22", achado["url"])

    def test_todos_iguais_devolve_vazio(self):
        html = "".join([
            self._card(u, "MLB" + u, "MLB1" + u, "ranker_retrieval_system_vpp_v2p", "x/p/MLB1")
            for u in ("a", "b", "c", "d")])
        self.assertEqual(anuncio_marcado_na_vitrine(html), {})

    def test_dois_unicos_devolve_vazio(self):
        # ambiguidade não vira chute
        html = "".join([
            self._card("a", "MLB1", "MLB11", "backend_a", "x/p/MLB11"),
            self._card("b", "MLB2", "MLB22", "backend_b", "y/p/MLB22"),
            self._card("c", "MLB3", "MLB33", "comum", "z/p/MLB33"),
            self._card("d", "MLB4", "MLB44", "comum", "w/p/MLB44"),
        ])
        self.assertEqual(anuncio_marcado_na_vitrine(html), {})

    def test_html_sem_polycard(self):
        self.assertEqual(anuncio_marcado_na_vitrine("<html>nada</html>"), {})


class OfertaDoClone(unittest.TestCase):
    ANUNCIO = {"nome": "Spectre Ghost 80ml", "preco": 272.0, "preco_de": 499.0,
               "link": "https://meli.la/x"}

    def test_catalogo(self):
        o = oferta_do_clone(self.ANUNCIO,
            "https://www.mercadolivre.com.br/perfume-x/p/MLB27861230",
            "Perfume Spectre Ghost Fragrance World Edp 80ml", "https://http2.mlstatic.com/f.jpg")
        self.assertEqual(o.mlb_id, "MLB27861230")
        self.assertEqual(o.preco_promocional, 272.0)
        self.assertEqual(o.preco_original, 499.0)
        self.assertEqual(o.desconto_pct, 45)
        self.assertEqual(o.imagem, "https://http2.mlstatic.com/f.jpg")

    def test_avulso(self):
        o = oferta_do_clone(self.ANUNCIO,
            "https://produto.mercadolivre.com.br/MLB-4993818683-perfume-y", "")
        self.assertEqual(o.mlb_id, "MLB4993818683")

    def test_catalogo_com_id_curto(self):
        # regressão do Homme Joop!: /p/MLB6093091 tem 7 dígitos e era
        # descartado, deixando a oferta fora do grupo 3 dias seguidos
        o = oferta_do_clone(self.ANUNCIO,
            "https://www.mercadolivre.com.br/perfume-homme-joop-125ml/p/MLB6093091",
            "Perfume Masculino Homme Joop! Eau de Toilette 125ml")
        self.assertIsNotNone(o)
        self.assertEqual(o.mlb_id, "MLB6093091")

    def test_url_de_anuncio_de_vendedor(self):
        o = oferta_do_clone(self.ANUNCIO,
            "https://www.mercadolivre.com.br/perfume-x/up/MLBU3880520594", "Perfume X")
        self.assertEqual(o.mlb_id, "MLBU3880520594")

    def test_url_sem_id(self):
        self.assertIsNone(oferta_do_clone(self.ANUNCIO, "https://ml.com/nada", ""))


class MensagemEFotoLiterais(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM ofertas"); self.con.execute("DELETE FROM config")
        self.con.commit()
        salvar_oferta(self.con, Oferta(mlb_id="MLB1", nome="Spectre",
            url="https://ml.com/x", preco_original=499, preco_promocional=272,
            link_afiliado="https://meli.la/MEU"))
        self.con.execute(
            "UPDATE ofertas SET clone_texto=?, clone_imagem=? WHERE mlb_id='MLB1'",
            ("BAUNILHA ABSURDA\n\n*Spectre 80ml*\n\nDe ~R$499~ ❌\nPor *R$272* ✅\n\n{link}",
             "https://pessoal.uazapi.com/files/abc.jpg"))
        self.con.commit()
        self.linha = self.con.execute("SELECT * FROM ofertas WHERE mlb_id='MLB1'").fetchone()

    def tearDown(self):
        self.con.close()

    def test_mensagem_e_a_do_rival_com_o_meu_link(self):
        texto = montar_mensagem(self.linha, self.con)
        self.assertTrue(texto.startswith("BAUNILHA ABSURDA"))
        self.assertIn("De ~R$499~ ❌", texto)
        self.assertIn("https://meli.la/MEU", texto)
        self.assertNotIn("{link}", texto)
        self.assertNotIn("Loja Oficial", texto)   # sem remodelar nada

    def test_foto_e_a_do_rival(self):
        self.assertEqual(foto_para_envio(self.linha),
                         "https://pessoal.uazapi.com/files/abc.jpg")

    def test_clone_assume_pendente_existente(self):
        # simula o galho do bloco4: produto da busca ainda não enviado
        from mercadolivre.clonador import RE_CLONE_LINK
        texto_rival = "TOP\n*Spectre 80ml*\nPor *R$272* 🔥\nhttps://meli.la/xyz"
        clone_texto = RE_CLONE_LINK.sub("{link}", texto_rival)
        self.con.execute(
            "UPDATE ofertas SET origem='busca', clone_texto='', clone_imagem='' "
            "WHERE mlb_id='MLB1'")
        status = self.con.execute(
            "SELECT status_envio FROM ofertas WHERE mlb_id='MLB1'").fetchone()
        self.assertEqual(status["status_envio"], "PENDENTE")   # pré-condição
        self.con.execute(
            "UPDATE ofertas SET origem='clone', clone_texto=? WHERE mlb_id='MLB1' "
            "AND status_envio='PENDENTE'", (clone_texto,))
        self.con.commit()
        linha = self.con.execute("SELECT * FROM ofertas WHERE mlb_id='MLB1'").fetchone()
        self.assertEqual(linha["origem"], "clone")
        self.assertIn("{link}", linha["clone_texto"])

    def test_oferta_normal_segue_no_template(self):
        salvar_oferta(self.con, Oferta(mlb_id="MLB2", nome="Perfume Asad Lattafa 100ml",
            url="https://ml.com/y", preco_original=300, preco_promocional=200,
            link_afiliado="https://meli.la/N"))
        self.con.commit()
        linha = self.con.execute("SELECT * FROM ofertas WHERE mlb_id='MLB2'").fetchone()
        self.assertIn("https://meli.la/N", montar_mensagem(linha, self.con))
