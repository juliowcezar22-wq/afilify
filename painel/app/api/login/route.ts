import { NextResponse } from "next/server";
import { scryptSync, timingSafeEqual } from "node:crypto";
import { criarToken, SESSAO } from "@/lib/sessao";
import * as usuarios from "@/lib/usuarios";

/**
 * Entrada no painel.
 *
 * A conta vive no banco. A credencial de ambiente continua aceita como
 * porta dos fundos do administrador — sem ela, uma instalação com o banco
 * fora do ar ficaria trancada para fora.
 */
export async function POST(req: Request) {
  const { email, senha } = await req.json().catch(() => ({}));
  const segredo = process.env.AUTH_SECRET ?? "";
  if (!segredo)
    return NextResponse.json({ erro: "painel sem credenciais configuradas" }, { status: 503 });

  const informado = String(email ?? "").trim().toLowerCase();
  const conta = await usuarios.porEmail(informado).catch(() => null);

  let autorizado = false;
  if (conta) {
    autorizado = usuarios.conferir(String(senha ?? ""), conta.hash);
    if (autorizado) await usuarios.registrarAcesso(conta.id);
  } else {
    const alvoEmail = (process.env.ADMIN_EMAIL ?? "").trim().toLowerCase();
    const alvoHash = process.env.ADMIN_PASSWORD_HASH ?? ""; // formato salt:hex
    if (alvoEmail && alvoHash && informado === alvoEmail) {
      const [salt, hex] = alvoHash.split(":");
      autorizado =
        hex?.length === 64 &&
        timingSafeEqual(scryptSync(String(senha ?? ""), salt, 32), Buffer.from(hex, "hex"));
    }
  }

  // Mesma resposta para email inexistente e senha errada: dizer qual dos
  // dois falhou entrega a lista de quem tem conta aqui.
  if (!autorizado) return NextResponse.json({ erro: "credenciais inválidas" }, { status: 401 });

  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSAO.NOME_COOKIE, await criarToken(informado, segredo), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: SESSAO.DIAS * 86400,
    path: "/",
  });
  return res;
}
