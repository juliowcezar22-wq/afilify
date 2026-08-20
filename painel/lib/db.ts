import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "@/drizzle/schema";

/** Conexão preguiçosa: o painel sobe (e builda) sem banco; as páginas
 *  degradam com aviso em vez de quebrar. */
let _db: ReturnType<typeof drizzle<typeof schema>> | null = null;

export function obterDb() {
  const url = process.env.DATABASE_URL;
  if (!url) return null;
  if (!_db) {
    const cliente = postgres(url, { max: 3, idle_timeout: 20, connect_timeout: 10 });
    _db = drizzle(cliente, { schema });
  }
  return _db;
}
