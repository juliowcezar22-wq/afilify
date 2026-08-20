"""Adapter de storage — tradução de dialeto e, se houver banco, o PG ao vivo."""
# ── blindagem: NUNCA tocar no banco real ──────────────────────────────
import os as _os, tempfile as _tf
_os.environ.setdefault("ML_BANCO", _os.path.join(_tf.mkdtemp(prefix="afilify-test-"), "t.db"))

import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.storage import traduzir_sql, LinhaCompat

URL_TESTE = os.environ.get("DATABASE_URL_TESTE", "")


class Traducao(unittest.TestCase):
    def test_placeholders(self):
        self.assertEqual(traduzir_sql("SELECT * FROM t WHERE a=? AND b=?"),
                         "SELECT * FROM t WHERE a=%s AND b=%s")

    def test_pragma_e_vacuum_somem(self):
        self.assertIsNone(traduzir_sql("PRAGMA journal_mode=WAL"))
        self.assertIsNone(traduzir_sql("  VACUUM"))

    def test_upsert_passa_intacto(self):
        sql = ("INSERT INTO estado (chave, valor) VALUES (?, ?) "
               "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor")
        self.assertEqual(traduzir_sql(sql).count("%s"), 2)
        self.assertIn("excluded.valor", traduzir_sql(sql))

    def test_linha_por_nome(self):
        r = LinhaCompat([("mlb_id", "MLB1"), ("preco", 9.9)])
        self.assertEqual(r["mlb_id"], "MLB1")
        self.assertEqual(r["preco"], 9.9)


@unittest.skipUnless(URL_TESTE, "sem DATABASE_URL_TESTE — teste ao vivo pulado")
class PostgresAoVivo(unittest.TestCase):
    """Roda quando a connection string chegar. Escreve APENAS no perfil
    'teste-pg' e limpa só ele — lição do incidente de 20/08."""
    PERFIL = "teste-pg"

    @classmethod
    def setUpClass(cls):
        from nucleo.storage import conectar_pg
        cls.con = conectar_pg(URL_TESTE)

    @classmethod
    def tearDownClass(cls):
        cls.con.execute("DELETE FROM ofertas WHERE perfil = ?", (cls.PERFIL,))
        cls.con.execute("DELETE FROM estado WHERE chave LIKE ?", (cls.PERFIL + ":%",))
        cls.con.commit(); cls.con.close()

    def test_upsert_e_leitura_por_nome(self):
        self.con.execute(
            "INSERT INTO ofertas (mlb_id, perfil, nome, url, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (mlb_id) DO UPDATE SET nome=excluded.nome",
            ("TESTE1", self.PERFIL, "Oferta de teste", "https://x", "2026-01-01", "2026-01-01"))
        self.con.commit()
        r = self.con.execute("SELECT nome, status_envio FROM ofertas WHERE mlb_id=?",
                             ("TESTE1",)).fetchone()
        self.assertEqual(r["nome"], "Oferta de teste")
        self.assertEqual(r["status_envio"], "PENDENTE")   # default do DDL

    def test_estado_upsert(self):
        ch = f"{self.PERFIL}:chave"
        for valor in ("a", "b"):
            self.con.execute("INSERT INTO estado (chave, valor) VALUES (?, ?) "
                             "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                             (ch, valor))
        self.con.commit()
        self.assertEqual(self.con.execute(
            "SELECT valor FROM estado WHERE chave=?", (ch,)).fetchone()["valor"], "b")


if __name__ == "__main__":
    unittest.main()
