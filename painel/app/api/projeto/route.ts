import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { COOKIE_PROJETO } from "@/lib/projetos";

export const dynamic = "force-dynamic";

/** Grava o projeto ativo do shell (apenas cookie — nada no banco). */
export async function POST(req: Request) {
  const { projeto } = await req.json().catch(() => ({ projeto: "" }));
  const jar = await cookies();
  const valor = typeof projeto === "string" ? projeto : "";
  if (valor) {
    jar.set(COOKIE_PROJETO, valor, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
  } else {
    jar.delete(COOKIE_PROJETO);
  }
  return NextResponse.json({ ok: true });
}
