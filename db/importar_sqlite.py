"""
Importa dados/ofertas.db (SQLite) para o Postgres. Idempotente: rodar duas
vezes dá no mesmo (UPSERT em tudo). Usado no cutover da Fase 2 e re-executável
para ensaios.

    DATABASE_URL=postgres://... python3 db/importar_sqlite.py [caminho.db]
"""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nucleo.storage import conectar_pg

origem = sys.argv[1] if len(sys.argv) > 1 else "dados/ofertas.db"
sq = sqlite3.connect(origem); sq.row_factory = sqlite3.Row
pg = conectar_pg()

colunas = [c["name"] for c in sq.execute("PRAGMA table_info(ofertas)")]
marcadores = ", ".join("?" * len(colunas))
atualiza = ", ".join(f"{c}=excluded.{c}" for c in colunas if c != "mlb_id")
sql = (f"INSERT INTO ofertas ({', '.join(colunas)}) VALUES ({marcadores}) "
       f"ON CONFLICT (mlb_id) DO UPDATE SET {atualiza}")
n = 0
for r in sq.execute("SELECT * FROM ofertas"):
    pg.execute(sql, tuple(r[c] for c in colunas)); n += 1
for r in sq.execute("SELECT * FROM estado"):
    pg.execute("INSERT INTO estado (chave, valor) VALUES (?, ?) "
               "ON CONFLICT (chave) DO UPDATE SET valor=excluded.valor",
               (r["chave"], r["valor"]))
pg.commit()
tot = pg.execute("SELECT COUNT(*) AS n FROM ofertas").fetchone()["n"]
print(f"importadas {n} ofertas do SQLite · Postgres agora tem {tot}")
pg.close(); sq.close()
