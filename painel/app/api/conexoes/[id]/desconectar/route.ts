import { NextResponse } from "next/server";
import * as servico from "@/lib/conexoes-servico";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    return NextResponse.json({ conexao: await servico.desconectar(id) });
  } catch (e) {
    return respostaDeErro(e);
  }
}
