import { NextResponse } from "next/server";
import * as servico from "@/lib/projetos-servico";
import { atualizarAutomacao } from "@/lib/projetos-repo";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { acao, nome, ritmo, mensagem } = await req.json().catch(() => ({}));
  try {
    if (acao === "ativar")
      return NextResponse.json({ automacao: await servico.ativar(id) });
    if (acao === "pausar")
      return NextResponse.json({ automacao: await servico.pausar(id) });
    if (acao === "editar") {
      await atualizarAutomacao(id, {
        nome: nome === undefined ? undefined : String(nome),
        ritmo,
        mensagem,
      });
      return NextResponse.json({ ok: true });
    }
    return NextResponse.json(
      { erro: { codigo: "acao_desconhecida", mensagem: "Ação não reconhecida." } },
      { status: 400 },
    );
  } catch (e) {
    return respostaDeErro(e);
  }
}

export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    await servico.removerAutomacao(id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return respostaDeErro(e);
  }
}
