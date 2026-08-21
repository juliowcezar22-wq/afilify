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
def upsert(tabela, pk):
    """Copia a tabela inteira com UPSERT pela PK composta."""
    cols = [c["name"] for c in sq.execute(f"PRAGMA table_info({tabela})")]
    marc = ", ".join("?" * len(cols))
    att = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in pk)
    sql = (f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({marc}) "
           f"ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {att}")
    q = 0
    for r in sq.execute(f"SELECT * FROM {tabela}"):
        pg.execute(sql, tuple(r[c] for c in cols)); q += 1
    print(f"  {tabela}: {q} linha(s)")

upsert("estado", ["chave"])
upsert("entregas", ["mlb_id", "canal"])
upsert("config", ["perfil", "chave"])

# cliques não tem chave natural: copia só se o destino estiver vazio
if pg.execute("SELECT COUNT(*) AS n FROM cliques").fetchone()["n"] == 0:
    for r in sq.execute("SELECT codigo, quando, agente FROM cliques"):
        pg.execute("INSERT INTO cliques (codigo, quando, agente) VALUES (?,?,?)",
                   (r["codigo"], r["quando"], r["agente"]))
pg.commit()
tot = pg.execute("SELECT COUNT(*) AS n FROM ofertas").fetchone()["n"]
print(f"importadas {n} ofertas do SQLite · Postgres agora tem {tot}")
pg.close(); sq.close()
