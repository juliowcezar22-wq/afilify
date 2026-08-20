/**
 * Acesso a dados do painel — UM contrato, DOIS motores:
 *
 *   SQLITE_PATH   → better-sqlite3 (operação local no Mac, dados REAIS já)
 *   DATABASE_URL  → postgres.js   (Neon/Supabase/VPS, pós-cutover)
 *
 * Mesmo SQL nos dois (placeholders `?`, datas TEXT ISO) — espelho da decisão
 * do nucleo/storage.py do motor. Trocar de banco = trocar env, zero código.
 */
import "server-only";
import path from "node:path";

export type Linha = Record<string, unknown>;

interface Banco {
  todas(sql: string, params?: unknown[]): Promise<Linha[]>;
  executar(sql: string, params?: unknown[]): Promise<number>;  // linhas afetadas
  motor: "sqlite" | "postgres";
}

let _banco: Banco | null = null;

function abrirSqlite(caminho: string): Banco {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Database = require("better-sqlite3");
  const db = new Database(path.resolve(process.cwd(), caminho), {
    readonly: false, fileMustExist: true,
  });
  db.pragma("busy_timeout = 5000");   // convive com o daemon (WAL)
  return {
    motor: "sqlite",
    async todas(sql, params = []) { return db.prepare(sql).all(...params) as Linha[]; },
    async executar(sql, params = []) { return db.prepare(sql).run(...params).changes; },
  };
}

function abrirPostgres(url: string): Banco {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const postgres = require("postgres");
  const sql = postgres(url, { max: 3, idle_timeout: 20, connect_timeout: 10 });
  return {
    motor: "postgres",
    async todas(texto, params = []) {
      let i = 0;
      const traduzido = texto.replace(/\?/g, () => `$${++i}`);
      return (await sql.unsafe(traduzido, params as never[])) as unknown as Linha[];
    },
    async executar(texto, params = []) {
      let i = 0;
      const traduzido = texto.replace(/\?/g, () => `$${++i}`);
      const r = await sql.unsafe(traduzido, params as never[]);
      return (r as unknown as { count?: number }).count ?? 0;
    },
  };
}

export function obterBanco(): Banco | null {
  if (_banco) return _banco;
  if (process.env.SQLITE_PATH) _banco = abrirSqlite(process.env.SQLITE_PATH);
  else if (process.env.DATABASE_URL) _banco = abrirPostgres(process.env.DATABASE_URL);
  return _banco;
}

export async function uma(sql: string, params?: unknown[]): Promise<Linha | null> {
  const b = obterBanco();
  if (!b) return null;
  const linhas = await b.todas(sql, params);
  return linhas[0] ?? null;
}

export async function todas(sql: string, params?: unknown[]): Promise<Linha[]> {
  const b = obterBanco();
  if (!b) return [];
  return b.todas(sql, params);
}


export async function executar(sql: string, params?: unknown[]): Promise<number> {
  const b = obterBanco();
  if (!b) throw new Error("banco não configurado");
  return b.executar(sql, params);
}
