import { NextResponse } from "next/server";
import { sql } from "drizzle-orm";
import { obterDb } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const db = obterDb();
  let banco: "conectado" | "ausente" | "erro" = "ausente";
  if (db) {
    try { await db.execute(sql`SELECT 1`); banco = "conectado"; }
    catch { banco = "erro"; }
  }
  return NextResponse.json({ ok: true, banco, ts: new Date().toISOString() });
}
