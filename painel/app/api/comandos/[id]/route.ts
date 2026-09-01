import { NextResponse } from "next/server";
import { consultarComando } from "@/lib/comandos";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

/** Estado e resultado de um pedido feito ao motor. */
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    return NextResponse.json(await consultarComando(id));
  } catch (e) {
    return respostaDeErro(e);
  }
}
