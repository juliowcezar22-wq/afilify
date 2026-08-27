"""
Conexão de WhatsApp — nucleo/conexoes/whatsapp.py

O que estes testes protegem:
  · o vocabulário do provedor nunca vaza para o produto
  · o usuário nunca lê erro técnico (HTTP, token, nome de fornecedor)
  · credencial não aparece em texto exibível
  · casos que derrubam o fluxo na vida real: já conectado antes de a tela
    pedir, resposta sem código, grupo sem nome, queda de rede

Sem rede: o transporte é substituído por uma resposta gravada da API real
(capturada em 27/08/2026).
"""

import os
import sys
import unittest
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.conexoes import whatsapp as w  # noqa: E402

CFG = w.Config(url="https://exemplo.invalido", admin="admin-de-teste")


class RespostaGravada:
    """Substitui o transporte. Guarda o que foi pedido, devolve o que mandarem."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def __call__(self, caminho, metodo="GET", corpo=None, headers=None, cfg=None):
        self.chamadas.append({"caminho": caminho, "metodo": metodo,
                              "corpo": corpo, "headers": headers or {}})
        r = self.respostas.pop(0) if self.respostas else {}
        if isinstance(r, Exception):
            raise r
        return r


class Tradutor(unittest.TestCase):
    """Quatro estados do provedor → onze do produto."""

    def test_todos_os_estados_do_provedor_tem_traducao(self):
        for bruto in ("connected", "connecting", "disconnected", "hibernated"):
            self.assertIn(bruto, w.DO_PROVEDOR)
            self.assertNotEqual(w.DO_PROVEDOR[bruto], w.ERRO)

    def test_estado_desconhecido_vira_erro_e_nao_conectado(self):
        """Estado novo do provedor não pode ser lido como 'está tudo bem'."""
        conta = w._conta_do_payload({"instance": {"status": "quantum"}})
        self.assertEqual(conta.estado, w.ERRO)

    def test_hibernado_vira_precisa_reconectar(self):
        conta = w._conta_do_payload({"instance": {"status": "hibernated"}})
        self.assertEqual(conta.estado, w.PRECISA_RECONECTAR)

    def test_payload_da_api_real_e_traduzido(self):
        """Forma capturada de /instance/all em 27/08/2026."""
        conta = w._conta_do_payload({
            "id": "abc-123", "name": "bot de promoções", "status": "connected",
            "profileName": "Achei Barato", "owner": "557591234567",
            "isBusiness": False, "lastDisconnectReason": "401: logged out from another device",
        })
        self.assertEqual(conta.estado, w.CONECTADO)
        self.assertEqual(conta.perfil, "Achei Barato")
        self.assertEqual(conta.nome, "bot de promoções")


class Pareamento(unittest.TestCase):
    def setUp(self):
        self._original = w._requisitar

    def tearDown(self):
        w._requisitar = self._original

    def test_sem_telefone_devolve_qr(self):
        w._requisitar = RespostaGravada(
            {"instance": {"status": "connecting", "qrcode": "data:image/png;base64,AAA"}})
        c = w.iniciar_pareamento("token", cfg=CFG)
        self.assertEqual(c.tipo, "qr")
        self.assertEqual(c.validade_seg, w.VALIDADE_QR_SEG)
        self.assertEqual(c.estado, w.CODIGO_DISPONIVEL)

    def test_com_telefone_devolve_codigo_digitavel(self):
        transporte = RespostaGravada(
            {"instance": {"status": "connecting", "paircode": "ABCD-1234"}})
        w._requisitar = transporte
        c = w.iniciar_pareamento("token", telefone="5575999991234", cfg=CFG)
        self.assertEqual(c.tipo, "pareamento")
        self.assertEqual(c.valor, "ABCD-1234")
        self.assertEqual(c.validade_seg, w.VALIDADE_PARCODE_SEG)
        self.assertEqual(transporte.chamadas[0]["corpo"], {"phone": "5575999991234"})

    def test_ja_conectado_nao_e_erro(self):
        """O usuário pode ter pareado antes de a tela pedir o código."""
        w._requisitar = RespostaGravada({"instance": {"status": "connected"}})
        c = w.iniciar_pareamento("token", cfg=CFG)
        self.assertEqual(c.estado, w.CONECTADO)
        self.assertEqual(c.valor, "")

    def test_resposta_sem_codigo_explica_o_que_fazer(self):
        w._requisitar = RespostaGravada({"instance": {"status": "disconnected"}})
        with self.assertRaises(w.ErroWhatsApp) as ctx:
            w.iniciar_pareamento("token", cfg=CFG)
        self.assertIn("novo", ctx.exception.mensagem_usuario.lower())


class MensagensParaOUsuario(unittest.TestCase):
    """Princípio I da constitution, no ponto onde erro técnico costuma vazar."""

    def setUp(self):
        self._abrir = w.urllib.request.urlopen

    def tearDown(self):
        w.urllib.request.urlopen = self._abrir

    def _falhar_com(self, erro):
        def abrir(*a, **k):
            raise erro
        w.urllib.request.urlopen = abrir

    def test_sessao_expirada_fala_de_reconectar(self):
        self._falhar_com(urllib.error.HTTPError(
            "http://x", 401, "Unauthorized", {}, None))
        with self.assertRaises(w.ErroWhatsApp) as ctx:
            w.consultar("token", cfg=CFG)
        msg = ctx.exception.mensagem_usuario
        self.assertIn("Reconecte", msg)
        self.assertNotIn("401", msg)

    def test_erro_de_rede_nao_vaza_detalhe(self):
        self._falhar_com(urllib.error.URLError("conexão recusada"))
        with self.assertRaises(w.ErroWhatsApp) as ctx:
            w.consultar("token", cfg=CFG)
        self.assertNotIn("URLError", ctx.exception.mensagem_usuario)

    def test_nenhuma_mensagem_de_usuario_cita_o_fornecedor(self):
        proibidos = ("uazapi", "instance", "token", "http", "admintoken", "jid")
        casos = [
            w.ErroWhatsApp("x").mensagem_usuario,
            w.ErroWhatsApp("x", "Esta conexão de WhatsApp perdeu o acesso. Reconecte a conta.").mensagem_usuario,
        ]
        for msg in casos:
            for termo in proibidos:
                self.assertNotIn(termo, msg.lower(), f"{termo!r} vazou em {msg!r}")

    def test_credencial_nunca_aparece_em_mensagem(self):
        e = w.ErroWhatsApp("falha com token 43c5-secreto")
        self.assertNotIn("43c5", e.mensagem_usuario)


class Grupos(unittest.TestCase):
    def setUp(self):
        self._original = w._requisitar

    def tearDown(self):
        w._requisitar = self._original

    def test_le_o_formato_real_da_api(self):
        w._requisitar = RespostaGravada({"groups": [
            {"JID": "120363408117538302@g.us", "Name": "#17 ACHEI BARATO | PERFUMES",
             "Participants": [{}, {}, {}]},
            {"JID": "120363406025827790@g.us", "Name": "Teste", "Participants": [{}, {}]},
        ]})
        g = w.listar_grupos("token", cfg=CFG)
        self.assertEqual(len(g), 2)
        self.assertEqual(g[0].nome, "#17 ACHEI BARATO | PERFUMES")
        self.assertEqual(g[0].participantes, 3)

    def test_grupo_sem_nome_continua_selecionavel(self):
        """Nome vazio não pode sumir da lista — o usuário ainda precisa poder
        escolher aquele grupo."""
        w._requisitar = RespostaGravada({"groups": [{"JID": "123@g.us"}]})
        g = w.listar_grupos("token", cfg=CFG)
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0].nome, "")

    def test_grupo_sem_identificador_e_descartado(self):
        w._requisitar = RespostaGravada({"groups": [{"Name": "sem id"}]})
        self.assertEqual(w.listar_grupos("token", cfg=CFG), [])

    def test_lista_vazia_nao_quebra(self):
        w._requisitar = RespostaGravada({})
        self.assertEqual(w.listar_grupos("token", cfg=CFG), [])


class Provisionamento(unittest.TestCase):
    def setUp(self):
        self._original = w._requisitar

    def tearDown(self):
        w._requisitar = self._original

    def test_sem_credencial_administrativa_orienta_adotar_conta(self):
        """D25b: a plataforma continua conectando contas, só não cria (FR-060)."""
        with self.assertRaises(w.ErroWhatsApp) as ctx:
            w.criar_conta("Nova", cfg=w.Config(url="https://x", admin=""))
        self.assertIn("já existente", ctx.exception.mensagem_usuario)

    def test_criacao_usa_credencial_administrativa(self):
        transporte = RespostaGravada(
            {"token": "tok-novo", "instance": {"id": "i-1", "name": "Nova",
                                               "status": "disconnected"}})
        w._requisitar = transporte
        conta = w.criar_conta("Nova", cfg=CFG)
        self.assertEqual(conta.credencial, "tok-novo")
        self.assertEqual(conta.estado, w.CRIANDO)
        self.assertEqual(transporte.chamadas[0]["headers"]["admintoken"], "admin-de-teste")

    def test_criacao_sem_credencial_na_resposta_falha(self):
        w._requisitar = RespostaGravada({"instance": {"id": "i-1"}})
        with self.assertRaises(w.ErroWhatsApp):
            w.criar_conta("Nova", cfg=CFG)

    def test_sem_admin_a_listagem_e_vazia_e_nao_estoura(self):
        self.assertEqual(w.contas_existentes(cfg=w.Config(url="https://x")), [])


class Protecao(unittest.TestCase):
    def setUp(self):
        self._original = w._requisitar

    def tearDown(self):
        w._requisitar = self._original

    def test_espacamento_corrige_maximo_menor_que_minimo(self):
        transporte = RespostaGravada({})
        w._requisitar = transporte
        w.definir_espacamento("token", 10, 5, cfg=CFG)
        self.assertEqual(transporte.chamadas[0]["corpo"],
                         {"msg_delay_min": 10, "msg_delay_max": 10})

    def test_espacamento_recusa_negativo(self):
        transporte = RespostaGravada({})
        w._requisitar = transporte
        w.definir_espacamento("token", -5, 3, cfg=CFG)
        self.assertEqual(transporte.chamadas[0]["corpo"]["msg_delay_min"], 0)

    def test_limites_indisponiveis_nao_derrubam_o_envio(self):
        """Diagnóstico é apoio: se falhar, a publicação segue seu curso."""
        w._requisitar = RespostaGravada(w.ErroWhatsApp("fora do ar"))
        r = w.limites_do_numero("token", cfg=CFG)
        self.assertFalse(r["disponivel"])
        self.assertIsNone(r["pode_enviar"])


if __name__ == "__main__":
    unittest.main()
