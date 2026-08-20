import { NextResponse } from "next/server";
import { scryptSync, timingSafeEqual } from "node:crypto";
import { criarToken, SESSAO } from "@/lib/sessao";

export async function POST(req: Request) {
  const { email, senha } = await req.json().catch(() => ({}));
  const alvoEmail = process.env.ADMIN_EMAIL ?? "";
  const alvoHash = process.env.ADMIN_PASSWORD_HASH ?? ""; // formato salt:hex
  const segredo = process.env.AUTH_SECRET ?? "";
  if (!alvoEmail || !alvoHash || !segredo)
    return NextResponse.json({ erro: "painel sem credenciais configuradas" }, { status: 503 });
  const [salt, hex] = alvoHash.split(":");
  const calc = scryptSync(String(senha ?? ""), salt, 32);
  const ok = email === alvoEmail &&
    hex.length === 64 && timingSafeEqual(calc, Buffer.from(hex, "hex"));
  if (!ok) return NextResponse.json({ erro: "credenciais inválidas" }, { status: 401 });

  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSAO.NOME_COOKIE, await criarToken(email, segredo), {
    httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production",
    maxAge: SESSAO.DIAS * 86400, path: "/",
  });
  return res;
}
