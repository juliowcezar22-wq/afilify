import { NextResponse } from "next/server";
import * as destinos from "@/lib/destinos";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    await destinos.remover(id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return respostaDeErro(e);
  }
}
