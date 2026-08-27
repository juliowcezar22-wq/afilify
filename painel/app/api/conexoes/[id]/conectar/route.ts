import { NextResponse } from "next/server";
import * as servico from "@/lib/conexoes-servico";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

/**
 * Gera o código de pareamento.
 * Sem `telefone`: QR para escanear. Com `telefone`: código digitável.
 */
export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { telefone } = await req.json().catch(() => ({}));
  try {
    return NextResponse.json(await servico.gerarCodigo(id, String(telefone ?? "").replace(/\D/g, "")));
  } catch (e) {
    return respostaDeErro(e);
  }
}
