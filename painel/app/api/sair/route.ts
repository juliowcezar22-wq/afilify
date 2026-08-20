import { NextResponse } from "next/server";
import { SESSAO } from "@/lib/sessao";

export async function POST() {
  const res = NextResponse.redirect(new URL("/login", process.env.PAINEL_URL ?? "http://localhost:3000"));
  res.cookies.set(SESSAO.NOME_COOKIE, "", { maxAge: 0, path: "/" });
  return res;
}
