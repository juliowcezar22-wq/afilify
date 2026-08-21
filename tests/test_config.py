"""Config dinâmica (Fase 5): override do painel, fallback e seed."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sqlite3, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nucleo.comum as comum
from nucleo.comum import (
    abrir_banco, config_json, gravar_config, garantir_config,
    montar_mensagem, sortear_headline,
)


def linha_fake(**kw):
    base = dict(nome="Perfume Lattafa Asad 100ml", condicao="", preco_original=369.0,
                preco_promocional=239.0, desconto_pct=35, badge="PROMOÇÃO GERAL",
                link_afiliado="https://meli.la/abc", url="https://ml.com/x",
                loja="Lipx", loja_oficial=1)
    base.update(kw)
    con = sqlite3.connect(":memory:"); con.row_factory = sqlite3.Row
    con.execute(f"CREATE TABLE t ({', '.join(base)})")
    con.execute(f"INSERT INTO t VALUES ({', '.join('?'*len(base))})", list(base.values()))
    return con.execute("SELECT * FROM t").fetchone()


class Config(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM config"); self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_fallback_sem_config(self):
        self.assertEqual(config_json(self.con, "headlines", {"x": 1}), {"x": 1})
        m = montar_mensagem(linha_fake(), self.con)     # usa as constantes
        self.assertIn("Loja Oficial Lipx no ML", m)

    def test_override_muda_a_mensagem_sem_restart(self):
        gravar_config(self.con, "mensagem", {
            "base": "{headline}\n{nome} por R$ {preco_promocional}\n{linha_loja}{link}",
            "linha_loja_oficial": "\n✅ Vendido pela loja oficial {loja}\n",
            "rodape": "_#publi_",
        })
        m = montar_mensagem(linha_fake(), self.con)
        self.assertIn("✅ Vendido pela loja oficial Lipx", m)
        self.assertIn("_#publi_", m)
        self.assertNotIn("Loja Oficial Lipx no ML", m)   # o formato antigo saiu

    def test_override_de_headlines(self):
        gravar_config(self.con, "headlines", {"geral": ["SÓ ESTA"],
                                              "desconto_medio": ["SÓ ESTA"]})
        for _ in range(5):
            self.assertEqual(sortear_headline(self.con, linha_fake()), "SÓ ESTA")

    def test_seed_grava_uma_vez_e_respeita_edicao(self):
        self.assertEqual(garantir_config(self.con), 5)   # +canal
        self.assertEqual(garantir_config(self.con), 0)   # idempotente
        gravar_config(self.con, "headlines", {"geral": ["EDITADA"]})
        self.assertEqual(garantir_config(self.con), 0)   # seed NUNCA sobrescreve
        self.assertEqual(config_json(self.con, "headlines", {})["geral"], ["EDITADA"])

    def test_config_corrompida_nao_derruba(self):
        self.con.execute(
            "INSERT INTO config (perfil, chave, valor, atualizado_em) VALUES (?,?,?,?)",
            (comum.PERFIL_ATIVO, "mensagem", "{json quebrado", "2026-01-01"))
        self.con.commit()
        m = montar_mensagem(linha_fake(), self.con)      # cai no fallback
        self.assertIn("R$ 239,00", m)


class Clonador(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM config"); self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_padrao_vem_do_perfil(self):
        cfg = comum.clonador_cfg(self.con)
        self.assertEqual(cfg["ativo"], comum.PERFIL.clone_ativo)
        self.assertEqual(cfg["grupos"], list(comum.PERFIL.clone_grupos))

    def test_desligar_pelo_painel_para_o_bloco4(self):
        from mercadolivre.clonador import bloco4_clonar
        gravar_config(self.con, "clonador", {"ativo": False})
        self.assertEqual(bloco4_clonar(self.con), 0)   # sem rede, sem varredura

    def test_adicionar_rival_pelo_painel(self):
        gravar_config(self.con, "clonador", {"grupos": ["a@g.us", "b@g.us"]})
        self.assertEqual(len(comum.clonador_cfg(self.con)["grupos"]), 2)


class Canal(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM config"); self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_padrao_e_o_grupo_do_perfil(self):
        self.assertEqual(comum.canal_cfg(self.con)["grupo"], comum.UAZAPI_GRUPO)

    def test_trocar_destino_pelo_painel(self):
        gravar_config(self.con, "canal", {"grupo": "999@g.us"})
        self.assertEqual(comum.canal_cfg(self.con)["grupo"], "999@g.us")


class Ritmo(unittest.TestCase):
    def setUp(self):
        if "afilify-test" not in comum.BANCO:
            raise RuntimeError(f"RECUSADO: banco real ({comum.BANCO})")
        self.con = abrir_banco()
        self.con.execute("DELETE FROM config"); self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_padrao_vem_do_perfil(self):
        cfg = comum.ritmo_cfg(self.con)
        self.assertEqual(tuple(cfg["envios_por_dia"]), tuple(comum.ENVIOS_POR_DIA))
        self.assertEqual(cfg["busca_horas"], list(comum.BUSCA_HORAS))

    def test_override_do_painel_vence(self):
        gravar_config(self.con, "ritmo", {"envios_por_dia": [10, 16],
                                          "busca_horas": [9, 18]})
        cfg = comum.ritmo_cfg(self.con)
        self.assertEqual(cfg["envios_por_dia"], [10, 16])
        self.assertEqual(cfg["busca_horas"], [9, 18])
        # chaves não editadas continuam do perfil
        self.assertEqual(cfg["validade_horas"], comum.VALIDADE_HORAS)

    def test_plano_do_dia_respeita_override(self):
        from mercadolivre.agente import plano_do_dia
        gravar_config(self.con, "ritmo", {"envios_por_dia": [7, 7],
                                          "busca_horas": [11]})
        p = plano_do_dia(self.con, comum.agora())
        self.assertEqual(p["cota"], 7)
        self.assertEqual(p["coletas"], [11])


if __name__ == "__main__":
    unittest.main()
