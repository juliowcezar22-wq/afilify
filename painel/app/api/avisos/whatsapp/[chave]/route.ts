import { NextResponse } from "next/server";
import { registrarAvisoDeConexao } from "@/lib/conexoes-servico";

export const dynamic = "force-dynamic";

/**
 * Avisos da plataforma de mensagens sobre o estado das contas.
 *
 * Pública por necessidade — a plataforma precisa alcançar — e por isso
 * protegida por uma chave secreta no próprio endereço, como já se faz na
 * rota de monitoramento existente.
 *
 * Nunca devolve erro por falha nossa: a plataforma reenviaria o aviso, e um
 * problema de banco aqui viraria uma tempestade de repetições. Quando algo
 * falha do nosso lado, o estado ainda é corrigido na próxima consulta.
 */
export async function POST(req: Request, ctx: { params: Promise<{ chave: string }> }) {
  const { chave } = await ctx.params;
  const esperada = process.env.WEBHOOK_SEGREDO ?? "";
  if (!esperada || chave !== esperada)
    return NextResponse.json({ erro: "não autorizado" }, { status: 401 });

  const evento = await req.json().catch(() => null);
  if (!evento) return NextResponse.json({ ok: true, ignorado: "corpo ilegível" });

  try {
    await registrarAvisoDeConexao(evento);
  } catch {
    /* falha nossa não vira repetição da plataforma */
  }
  return NextResponse.json({ ok: true });
}

export async function GET() {
  return NextResponse.json({ ok: true, servico: "avisos de conexão" });
}
