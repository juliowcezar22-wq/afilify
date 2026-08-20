"""
STORAGE — o mesmo motor falando com SQLite ou Postgres.

    STORAGE=sqlite    (padrão) tudo como sempre foi, zero dependências
    STORAGE=postgres  exige DATABASE_URL e `pip install psycopg[binary]`

O contrato é a API do sqlite3 que o código inteiro já usa:
    con.execute(sql, params) → cursor iterável, .fetchone()/.fetchall()/.rowcount
    linhas acessadas POR NOME (r["coluna"])
    con.commit() / con.close()

A tradução de dialeto acontece aqui e SOMENTE aqui:
    ?        → %s
    PRAGMA   → no-op (conceito que não existe no PG)
    VACUUM   → no-op (autovacuum do PG cuida)
O resto do SQL do projeto (UPSERT com ON CONFLICT/excluded, LIKE com
parâmetro, datas ISO como TEXT) é idêntico nos dois dialetos — por design.
"""

from __future__ import annotations

import os
import re

RE_PLACEHOLDER = re.compile(r"\?")


def traduzir_sql(sql: str) -> str | None:
    """Dialeto SQLite → Postgres. None = comando sem equivalente (ignorar)."""
    limpo = sql.lstrip()
    if limpo.upper().startswith(("PRAGMA", "VACUUM")):
        return None
    return RE_PLACEHOLDER.sub("%s", sql)


class _CursorVazio:
    """Devolvido para comandos ignorados — iterável, vazio, inofensivo."""
    rowcount = 0
    def fetchone(self): return None
    def fetchall(self): return []
    def __iter__(self): return iter(())


class LinhaCompat(dict):
    """Linha do Postgres com a mesma cara do sqlite3.Row (acesso por nome)."""
    __slots__ = ()


def _fabrica_linha(cursor):
    colunas = [d.name for d in cursor.description]
    def montar(valores):
        return LinhaCompat(zip(colunas, valores))
    return montar


class ConexaoPg:
    """Postgres com a API do sqlite3. Reconecta uma vez em queda de conexão;
    faz rollback automático em erro para a conexão nunca ficar envenenada
    (comportamento que o daemon já espera do SQLite)."""

    def __init__(self, url: str):
        import psycopg                      # dependência só deste modo
        self._psycopg = psycopg
        self._url = url
        self._con = self._conectar()

    def _conectar(self):
        return self._psycopg.connect(
            self._url, row_factory=_fabrica_linha, autocommit=False,
            connect_timeout=15,
        )

    def execute(self, sql: str, params=()):
        traduzido = traduzir_sql(sql)
        if traduzido is None:
            return _CursorVazio()
        try:
            return self._con.execute(traduzido, params or None)
        except (self._psycopg.OperationalError, self._psycopg.InterfaceError):
            self._con = self._conectar()    # Postgres reiniciou / rede caiu
            return self._con.execute(traduzido, params or None)
        except self._psycopg.Error:
            self._con.rollback()            # não envenenar a transação
            raise

    def executescript(self, sql: str):
        # psycopg (protocolo estendido) não aceita multi-statement num
        # execute; nosso DDL é simples, sem ';' dentro de strings
        for stmt in sql.split(";"):
            if stmt.strip():
                self.execute(stmt)
        self.commit()

    def commit(self): self._con.commit()
    def rollback(self): self._con.rollback()
    def close(self): self._con.close()


def conectar_pg(url: str = "") -> ConexaoPg:
    """Abre o Postgres e garante o schema (idempotente)."""
    url = url or os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "STORAGE=postgres exige DATABASE_URL no ambiente (.env)."
        )
    con = ConexaoPg(url)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pasta = os.path.join(raiz, "db")
    for arquivo in sorted(os.listdir(pasta)):        # 0001, 0002, …
        if arquivo.endswith(".sql"):
            with open(os.path.join(pasta, arquivo), encoding="utf-8") as f:
                con.executescript(f.read())
    return con
