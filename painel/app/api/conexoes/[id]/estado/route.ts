import { NextResponse } from "next/server";
import * as servico from "@/lib/conexoes-servico";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

/**
 * Estado atual, para a tela que aguarda o pareamento (FR-012).
 * Consultado em intervalo curto SÓ enquanto o código está na tela.
 */
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    return NextResponse.json({ conexao: await servico.sincronizarEstado(id) });
  } catch (e) {
    return respostaDeErro(e);
  }
}
