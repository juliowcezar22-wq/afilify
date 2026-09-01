"""
Contexto — nucleo/contexto.py e a resolução no início do processo.

O que estes testes protegem:

  · o modo antigo (arquivo perfis/*.py) continua produzindo EXATAMENTE os
    mesmos valores — é a operação viva, e ela não pode mudar de compasso
    porque refatoramos;
  · o modo novo (automação criada na interface) produz um contexto
    equivalente, lido do banco;
  · banco indisponível não derruba o motor: ele cai no arquivo.

O segundo caso roda em subprocesso porque o contexto é resolvido no import —
testá-lo de outro jeito seria testar outra coisa.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault(
    "ML_BANCO", os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "ctx.db"))

from nucleo import comum, contexto, perfil  # noqa: E402

# Relativo ao relógio: data cravada envelhece e o teste passa a falhar
# sozinho dias depois, sem nada ter mudado no código.
AGORA = comum.agora().isoformat(timespec="seconds")


class DoPerfil(unittest.TestCase):
    """O jeito de sempre, intacto."""

    def test_perfil_de_perfumes_vira_contexto_fiel(self):
        p = perfil.carregar("perfumes_ml")
        c = contexto.Contexto.do_perfil(p)
        self.assertEqual(c.chave, p.nome)
        self.assertEqual(c.nicho, p.nicho)
        self.assertEqual(c.ritmo.envios_por_dia, tuple(p.envios_por_dia))
        self.assertEqual(c.ritmo.inicio_janela, tuple(p.inicio_janela))
        self.assertEqual(c.ritmo.fim_janela, tuple(p.fim_janela))
        self.assertEqual(c.ritmo.dispersao, p.dispersao)
        self.assertEqual(c.ritmo.proporcao_preferidas, p.proporcao_preferidas)
        self.assertEqual(c.ritmo.busca_horas, list(p.busca_horas))
        self.assertEqual(c.ritmo.validade_horas, p.validade_horas)
        self.assertEqual(c.destino_principal, p.grupo_whatsapp)
        self.assertEqual(c.clone_ativo, p.clone_ativo)
        self.assertEqual(c.origem, "perfil")

    def test_perfil_sem_destino_nao_esta_pronto(self):
        c = contexto.Contexto.do_perfil(perfil.carregar("casa_ml_shopee"))
        pode, motivo = c.pronta_para_publicar()
        self.assertFalse(pode)
        self.assertIn("onde publicar", motivo)   # frase de gente, não de código

    def test_perfil_com_destino_esta_pronto(self):
        c = contexto.Contexto.do_perfil(perfil.carregar("perfumes_ml"))
        self.assertEqual(c.pronta_para_publicar(), (True, ""))


class DoBanco(unittest.TestCase):
    """O jeito novo: automação criada na interface."""

    def setUp(self):
        from nucleo import comum
        comum.BANCO = os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "b.db")
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = comum.abrir_banco()
        self.projeto = str(uuid.uuid4())
        self.automacao = str(uuid.uuid4())
        self.con.execute(
            "INSERT INTO projetos (id, workspace_id, nome, tipo_nicho_id, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', 'Perfumes', 'perfumes', 'ativo', ?, ?)",
            (self.projeto, AGORA, AGORA))
        self.con.execute(
            "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, ritmo, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, 'Ofertas Mercado Livre', 'ativa', ?, ?, ?)",
            (self.automacao, self.projeto,
             json.dumps({"envios_por_dia": [40, 60], "inicio_janela": [9.0, 10.0],
                         "fim_janela": [21.0, 22.0], "busca_horas": [8, 14, 20],
                         "validade_horas": 72, "proporcao_preferidas": 0.0}),
             AGORA, AGORA))
        self.con.execute(
            "INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, "
            "ultimo_estado_em, criado_em, atualizado_em) "
            "VALUES ('cx-1', 'ws-afilify', 'whatsapp', 'Principal', 'conectado', ?, ?, ?)",
            (AGORA, AGORA, AGORA))
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def _destino(self, alvo, nome, ordem=0):
        self.con.execute(
            "INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, "
            "ordem, criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, 'cx-1', ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), self.automacao, alvo, nome, ordem, AGORA, AGORA))
        self.con.commit()

    def test_le_ritmo_da_automacao(self):
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.ritmo.envios_por_dia, (40, 60))
        self.assertEqual(c.ritmo.busca_horas, [8, 14, 20])
        self.assertEqual(c.ritmo.validade_horas, 72)
        self.assertEqual(c.origem, "banco")

    def test_nome_do_projeto_e_do_usuario_nao_slug(self):
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.projeto_nome, "Perfumes")
        self.assertEqual(c.automacao_nome, "Ofertas Mercado Livre")
        self.assertNotIn("-ml", c.projeto_nome)

    def test_varios_destinos_em_ordem(self):
        self._destino("1203@g.us", "Principal", ordem=0)
        self._destino("1204@g.us", "VIP", ordem=1)
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual([d.nome for d in c.destinos], ["Principal", "VIP"])
        self.assertEqual(c.destino_principal, "1203@g.us")

    def test_destino_inativo_fica_de_fora(self):
        self._destino("1203@g.us", "Principal")
        self.con.execute("UPDATE destinos SET ativo = 0")
        self.con.commit()
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.destinos, [])
        self.assertFalse(c.pronta_para_publicar()[0])

    def test_ritmo_ausente_cai_no_padrao(self):
        self.con.execute("UPDATE automacoes SET ritmo = '{}'")
        self.con.commit()
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.ritmo.envios_por_dia, contexto.Ritmo().envios_por_dia)

    def test_ritmo_corrompido_nao_derruba(self):
        self.con.execute("UPDATE automacoes SET ritmo = 'não é json'")
        self.con.commit()
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.ritmo.validade_horas, contexto.Ritmo().validade_horas)

    def test_monitoramento_vira_configuracao_de_clone(self):
        self.con.execute(
            "INSERT INTO fontes (id, workspace_id, automacao_id, tipo, ativa, criterios, "
            "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, 'monitoramento', 1, ?, ?, ?)",
            (str(uuid.uuid4()), self.automacao,
             json.dumps({"grupos": ["1209@g.us"]}), AGORA, AGORA))
        self.con.commit()
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertTrue(c.clone_ativo)
        self.assertEqual(c.clone_grupos, ["1209@g.us"])

    def test_automacao_inexistente_avisa(self):
        with self.assertRaises(ValueError):
            contexto.Contexto.do_banco(self.con, "não-existe")

    def test_lista_automacoes_ativas(self):
        self.assertEqual(contexto.automacoes_ativas(self.con), [self.automacao])
        self.con.execute("UPDATE automacoes SET estado = 'pausada'")
        self.con.commit()
        self.assertEqual(contexto.automacoes_ativas(self.con), [])

    def test_projeto_pausado_tira_a_automacao_da_lista(self):
        self.con.execute("UPDATE projetos SET estado = 'pausado'")
        self.con.commit()
        self.assertEqual(contexto.automacoes_ativas(self.con), [])


class ResolucaoNoProcesso(unittest.TestCase):
    """O contexto é resolvido no início do processo — então o teste sobe um."""

    def _rodar(self, ambiente: dict) -> dict:
        env = {**os.environ, **ambiente}
        codigo = (
            "import sys, json; sys.path.insert(0, %r);"
            "from nucleo import comum;"
            "print(json.dumps({"
            "'chave': comum.PERFIL_ATIVO,"
            "'origem': comum.CONTEXTO.origem,"
            "'cota': list(comum.ENVIOS_POR_DIA),"
            "'validade': comum.VALIDADE_HORAS,"
            "'destino': comum.UAZAPI_GRUPO}))" % RAIZ
        )
        saida = subprocess.run([sys.executable, "-c", codigo], env=env,
                               capture_output=True, text=True, timeout=60)
        if saida.returncode != 0:
            self.fail(f"processo falhou: {saida.stderr[-600:]}")
        return json.loads(saida.stdout.strip().splitlines()[-1])

    def test_sem_automacao_usa_o_arquivo_do_perfil(self):
        pasta = tempfile.mkdtemp(prefix="afilify-test-")
        r = self._rodar({"PERFIL": "perfumes_ml", "AUTOMACAO_ID": "",
                         "ML_BANCO": os.path.join(pasta, "x.db")})
        p = perfil.carregar("perfumes_ml")
        self.assertEqual(r["origem"], "perfil")
        self.assertEqual(r["chave"], p.nome)
        self.assertEqual(r["cota"], list(p.envios_por_dia))
        self.assertEqual(r["validade"], p.validade_horas)
        self.assertEqual(r["destino"], p.grupo_whatsapp)

    def test_com_automacao_le_do_banco(self):
        pasta = tempfile.mkdtemp(prefix="afilify-test-")
        caminho = os.path.join(pasta, "b.db")
        from nucleo import comum
        antes = comum.BANCO
        try:
            comum.BANCO = caminho
            con = comum.abrir_banco()
            proj, auto = str(uuid.uuid4()), str(uuid.uuid4())
            con.execute(
                "INSERT INTO projetos (id, workspace_id, nome, tipo_nicho_id, estado, "
                "criado_em, atualizado_em) VALUES (?, 'ws-afilify', 'Casa', 'casa', 'ativo', ?, ?)",
                (proj, AGORA, AGORA))
            con.execute(
                "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, ritmo, "
                "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, 'Ofertas', 'ativa', ?, ?, ?)",
                (auto, proj, json.dumps({"envios_por_dia": [11, 22], "validade_horas": 99}),
                 AGORA, AGORA))
            con.execute(
                "INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, "
                "ultimo_estado_em, criado_em, atualizado_em) "
                "VALUES ('cx-9', 'ws-afilify', 'whatsapp', 'P', 'conectado', ?, ?, ?)",
                (AGORA, AGORA, AGORA))
            con.execute(
                "INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, "
                "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, 'cx-9', '999@g.us', 'Grupo', ?, ?)",
                (str(uuid.uuid4()), auto, AGORA, AGORA))
            con.commit()
            con.close()
        finally:
            comum.BANCO = antes

        r = self._rodar({"AUTOMACAO_ID": auto, "ML_BANCO": caminho, "PERFIL": "perfumes_ml"})
        self.assertEqual(r["origem"], "banco")
        self.assertEqual(r["chave"], proj)
        self.assertEqual(r["cota"], [11, 22])
        self.assertEqual(r["validade"], 99)
        self.assertEqual(r["destino"], "999@g.us")

    def test_automacao_inexistente_cai_no_perfil_sem_derrubar(self):
        """Projeto novo indisponível é ruim; a operação viva parar é pior."""
        pasta = tempfile.mkdtemp(prefix="afilify-test-")
        r = self._rodar({"AUTOMACAO_ID": "fantasma", "PERFIL": "perfumes_ml",
                         "ML_BANCO": os.path.join(pasta, "y.db")})
        self.assertEqual(r["origem"], "perfil")
        self.assertEqual(r["chave"], perfil.carregar("perfumes_ml").nome)


if __name__ == "__main__":
    unittest.main()


class FonteDaAutomacao(unittest.TestCase):
    """A fonte configurada na tela manda no que e quando procurar.

    Sem isto, o usuário mexeria nos horários da fonte e o motor coletaria em
    outros — configuração que parece funcionar e não funciona.
    """

    def setUp(self):
        from nucleo import comum
        comum.BANCO = os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "f.db")
        self.con = comum.abrir_banco()
        self.projeto, self.automacao = str(uuid.uuid4()), str(uuid.uuid4())
        self.con.execute(
            "INSERT INTO projetos (id, workspace_id, nome, tipo_nicho_id, estado, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', 'P', 'perfumes', 'ativo', ?, ?)",
            (self.projeto, AGORA, AGORA))
        self.con.execute(
            "INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, ritmo, criado_em, atualizado_em) "
            "VALUES (?, 'ws-afilify', ?, 'A', 'ativa', '{}', ?, ?)",
            (self.automacao, self.projeto, AGORA, AGORA))
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def _fonte(self, ativa=1, horarios=None, criterios=None):
        self.con.execute(
            "INSERT INTO fontes (id, workspace_id, automacao_id, tipo, ativa, criterios, agenda, "
            "criado_em, atualizado_em) VALUES (?, 'ws-afilify', ?, 'busca', ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), self.automacao, ativa,
             json.dumps(criterios or {"palavras_chave": ["perfume árabe"]}),
             json.dumps({"horarios": horarios} if horarios else {}), AGORA, AGORA))
        self.con.commit()

    def test_criterios_da_fonte_chegam_ao_contexto(self):
        self._fonte(criterios={"palavras_chave": ["perfume árabe", "perfume importado"]})
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.criterios_busca["palavras_chave"], ["perfume árabe", "perfume importado"])
        self.assertTrue(c.fonte_busca_id)

    def test_horarios_da_fonte_vencem_o_padrao(self):
        self._fonte(horarios=[6, 12, 18, 22])
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.ritmo.busca_horas, [6, 12, 18, 22])

    def test_fonte_desligada_nao_manda_no_ritmo(self):
        self._fonte(ativa=0, horarios=[3])
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertNotEqual(c.ritmo.busca_horas, [3])
        self.assertEqual(c.criterios_busca, {})

    def test_sem_fonte_o_nicho_continua_mandando(self):
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.criterios_busca, {})
        self.assertEqual(c.fonte_busca_id, "")

    def test_agenda_corrompida_nao_derruba(self):
        self.con.execute("INSERT INTO fontes (id, workspace_id, automacao_id, tipo, ativa, "
                         "criterios, agenda, criado_em, atualizado_em) "
                         "VALUES (?, 'ws-afilify', ?, 'busca', 1, '{}', 'não é json', ?, ?)",
                         (str(uuid.uuid4()), self.automacao, AGORA, AGORA))
        self.con.commit()
        c = contexto.Contexto.do_banco(self.con, self.automacao)
        self.assertEqual(c.ritmo.busca_horas, contexto.Ritmo().busca_horas)
