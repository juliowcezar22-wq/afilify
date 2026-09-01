import { NextResponse } from "next/server";
import * as servico from "@/lib/projetos-servico";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

/** Renomear, duplicar ou criar automação dentro do projeto. */
export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { acao, nome } = await req.json().catch(() => ({}));
  try {
    if (acao === "renomear") {
      await servico.renomearProjeto(id, String(nome ?? ""));
      return NextResponse.json({ ok: true });
    }
    if (acao === "duplicar")
      return NextResponse.json({ projeto: await servico.duplicarProjeto(id, String(nome ?? "")) });
    if (acao === "nova-automacao")
      return NextResponse.json({
        automacao: await servico.criarAutomacao(id, String(nome ?? "")),
      });
    return NextResponse.json(
      { erro: { codigo: "acao_desconhecida", mensagem: "Ação não reconhecida." } },
      { status: 400 },
    );
  } catch (e) {
    return respostaDeErro(e);
  }
}

/** Arquivar — o histórico do projeto sobrevive. */
export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    await servico.arquivarProjeto(id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return respostaDeErro(e);
  }
}
