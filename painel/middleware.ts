import { NextRequest, NextResponse } from "next/server";
import { verificarToken, SESSAO } from "@/lib/sessao";

export async function middleware(req: NextRequest) {
  const segredo = process.env.AUTH_SECRET;
  if (!segredo) return NextResponse.next(); // dev sem env: painel aberto local
  const sessao = await verificarToken(
    req.cookies.get(SESSAO.NOME_COOKIE)?.value, segredo);
  if (!sessao) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // tudo protegido, exceto login, health, tracking futuro e estáticos
  matcher: ["/((?!login|api/login|api/health|api/webhook|r/|_next|favicon.ico).*)"],
};
