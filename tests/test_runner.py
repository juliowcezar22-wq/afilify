"""Runner multi-perfil — seleção de perfis e regras de supervisão."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.perfil import Perfil, listar, escolher_para_rodar
from nucleo import perfil as mod_perfil
import runner


class Selecao(unittest.TestCase):
    def test_listar_encontra_os_perfis_do_projeto(self):
        nomes = [p.nome for p in listar()]
        self.assertIn("perfumes-ml", nomes)
        self.assertIn("casa-ml-shopee", nomes)

    def test_perfumes_roda_casa_ainda_nao(self):
        rodar, pulados = escolher_para_rodar(listar())
        self.assertIn("perfumes-ml", [p.nome for p in rodar])
        motivo = dict(pulados).get("casa-ml-shopee", "")
        self.assertIn("GRUPO_WHATSAPP", motivo)   # sem grupo definido ainda

    def test_inativo_e_pulado_com_motivo(self):
        perfis = [Perfil(nome="x", ativo=False, grupo_whatsapp="123@g.us"),
                  Perfil(nome="y", ativo=True, grupo_whatsapp="456@g.us")]
        rodar, pulados = escolher_para_rodar(perfis)
        self.assertEqual([p.nome for p in rodar], ["y"])
        self.assertEqual(pulados, [("x", "ATIVO=False")])


if __name__ == "__main__":
    unittest.main()


class SupervisorPorAutomacao(unittest.TestCase):
    """O supervisor trata igual automação do banco e perfil de arquivo.

    O que isto protege: ligar um projeto na tela precisa subir o processo
    dele sem editar código — e a operação por arquivo não pode parar de
    funcionar por causa disso.
    """

    def test_filho_de_perfil_usa_o_arquivo(self):
        p = mod_perfil.carregar("perfumes_ml")
        f = runner.Filho.de_perfil(p)
        self.assertEqual(f.ambiente["PERFIL"], "perfumes_ml")
        self.assertEqual(f.ambiente["AUTOMACAO_ID"], "")
        self.assertEqual(f.trava, p.nome)

    def test_filho_de_automacao_usa_o_banco(self):
        f = runner.Filho.de_automacao("auto-123", "Perfumes · Ofertas")
        self.assertEqual(f.ambiente["AUTOMACAO_ID"], "auto-123")
        self.assertNotIn("PERFIL", f.ambiente)
        self.assertEqual(f.trava, "auto-123")

    def test_rotulo_e_legivel_nao_slug(self):
        f = runner.Filho.de_automacao("auto-123", "Perfumes · Ofertas Mercado Livre")
        self.assertIn("Perfumes", f.rotulo)
        self.assertNotIn("-ml", f.rotulo)

    def test_travas_diferentes_nao_colidem(self):
        """Duas automações do mesmo projeto precisam de travas distintas."""
        a = runner.Filho.de_automacao("auto-1", "Perfumes · ML")
        b = runner.Filho.de_automacao("auto-2", "Perfumes · Shopee")
        self.assertNotEqual(a.trava, b.trava)

    def test_banco_indisponivel_nao_derruba_o_supervisor(self):
        """Sem banco, a operação por arquivo segue — nunca o contrário.

        O caminho do banco é resolvido no import, então o teste troca a
        variável do módulo: mexer no ambiente aqui não teria efeito nenhum.
        """
        from nucleo import comum
        antes = comum.BANCO
        comum.BANCO = "/pasta/que/nao/existe/x.db"
        try:
            self.assertEqual(runner.automacoes_do_banco(), [])
        finally:
            comum.BANCO = antes
