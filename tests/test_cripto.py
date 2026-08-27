"""
Cifra de credenciais — nucleo/cripto.py

O que estes testes protegem: credencial nunca fica em claro, adulteração é
DETECTADA (não devolve lixo), e credencial de uma conexão não abre no lugar
de outra.

Pulam inteiros quando `cryptography` não está no ambiente — o módulo degrada
com mensagem clara, e é isso que o teste do ambiente sem a lib verifica.
"""

import base64
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import cripto  # noqa: E402

TEM_LIB = True
try:
    import cryptography  # noqa: F401
except ImportError:
    TEM_LIB = False

CHAVE = base64.urlsafe_b64encode(b"0" * 32).decode()


class ChaveMestra(unittest.TestCase):
    def setUp(self):
        self._antes = os.environ.get("AFILIFY_CHAVE_MESTRA")

    def tearDown(self):
        if self._antes is None:
            os.environ.pop("AFILIFY_CHAVE_MESTRA", None)
        else:
            os.environ["AFILIFY_CHAVE_MESTRA"] = self._antes

    def test_ausente_explica_como_gerar(self):
        os.environ.pop("AFILIFY_CHAVE_MESTRA", None)
        with self.assertRaises(cripto.ErroCripto) as ctx:
            cripto.chave_mestra()
        self.assertIn("AFILIFY_CHAVE_MESTRA", str(ctx.exception))
        self.assertIn("urandom", str(ctx.exception))   # a mensagem ensina a gerar

    def test_tamanho_errado_recusado(self):
        os.environ["AFILIFY_CHAVE_MESTRA"] = base64.urlsafe_b64encode(b"curta").decode()
        with self.assertRaises(cripto.ErroCripto):
            cripto.chave_mestra()

    def test_nao_base64_recusado(self):
        os.environ["AFILIFY_CHAVE_MESTRA"] = "isto não é base64!!"
        with self.assertRaises(cripto.ErroCripto):
            cripto.chave_mestra()


@unittest.skipUnless(TEM_LIB, "cryptography não instalado neste ambiente")
class CifraEDecifra(unittest.TestCase):
    def setUp(self):
        self._antes = os.environ.get("AFILIFY_CHAVE_MESTRA")
        os.environ["AFILIFY_CHAVE_MESTRA"] = CHAVE

    def tearDown(self):
        if self._antes is None:
            os.environ.pop("AFILIFY_CHAVE_MESTRA", None)
        else:
            os.environ["AFILIFY_CHAVE_MESTRA"] = self._antes

    def test_ida_e_volta(self):
        segredo = "43c5f1e2-token-da-instancia"
        guardado = cripto.cifrar(segredo)
        self.assertNotIn(segredo, guardado)          # nunca em claro
        self.assertTrue(guardado.startswith("v1."))
        self.assertEqual(cripto.decifrar(guardado), segredo)

    def test_mesma_entrada_gera_saidas_diferentes(self):
        """Nonce aleatório: dois workspaces com o mesmo token não são
        identificáveis por comparação de coluna."""
        a, b = cripto.cifrar("igual"), cripto.cifrar("igual")
        self.assertNotEqual(a, b)
        self.assertEqual(cripto.decifrar(a), cripto.decifrar(b))

    def test_adulteracao_e_detectada(self):
        guardado = cripto.cifrar("token")
        versao, nonce, selado = guardado.split(".")
        mexido = f"{versao}.{nonce}.{selado[:-4]}AAAA"
        with self.assertRaises(cripto.ErroCripto):
            cripto.decifrar(mexido)

    def test_contexto_amarra_a_credencial_ao_dono(self):
        guardado = cripto.cifrar("token", contexto="conexao-1")
        self.assertEqual(cripto.decifrar(guardado, contexto="conexao-1"), "token")
        with self.assertRaises(cripto.ErroCripto):
            cripto.decifrar(guardado, contexto="conexao-2")

    def test_chave_trocada_nao_abre(self):
        guardado = cripto.cifrar("token")
        os.environ["AFILIFY_CHAVE_MESTRA"] = base64.urlsafe_b64encode(b"1" * 32).decode()
        with self.assertRaises(cripto.ErroCripto):
            cripto.decifrar(guardado)

    def test_vazio_volta_vazio(self):
        self.assertEqual(cripto.decifrar(""), "")

    def test_formato_desconhecido_recusado(self):
        with self.assertRaises(cripto.ErroCripto):
            cripto.decifrar("v9.abc.def")


class Mascara(unittest.TestCase):
    def test_mostra_so_o_fim(self):
        self.assertEqual(cripto.mascarar("5575999991234"), "••••1234")

    def test_valor_curto_nao_vaza(self):
        self.assertEqual(cripto.mascarar("abc"), "••••")

    def test_vazio(self):
        self.assertEqual(cripto.mascarar(""), "")


if __name__ == "__main__":
    unittest.main()
