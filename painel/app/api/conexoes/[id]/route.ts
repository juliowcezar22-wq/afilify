import { NextResponse } from "next/server";
import * as servico from "@/lib/conexoes-servico";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

/** Renomear. */
export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { nome } = await req.json().catch(() => ({}));
  try {
    await servico.renomear(id, String(nome ?? ""));
    return NextResponse.json({ ok: true });
  } catch (e) {
    return respostaDeErro(e);
  }
}

/**
 * Remover. Sem `confirmar`, recusa com 409 quando automações ativas dependem
 * da conexão — e devolve quais, para o usuário decidir sabendo (FR-022).
 */
export async function DELETE(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { confirmar } = await req.json().catch(() => ({}));
  try {
    return NextResponse.json({ ok: true, ...(await servico.remover(id, Boolean(confirmar))) });
  } catch (e) {
    return respostaDeErro(e);
  }
}
