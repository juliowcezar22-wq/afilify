import { NextResponse } from "next/server";
import * as fontes from "@/lib/fontes";
import { criarComando } from "@/lib/comandos";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { acao, criterios, agenda, ativa } = await req.json().catch(() => ({}));
  try {
    if (acao === "salvar") {
      await fontes.atualizar(id, {
        criterios: criterios ? fontes.validarCriterios(criterios) : undefined,
        agenda: agenda ? { horarios: (agenda.horarios ?? []).map(Number) } : undefined,
        ativa,
      });
      return NextResponse.json({ ok: true });
    }
    if (acao === "testar") {
      const fonte = await fontes.obter(id);
      if (!fonte)
        return NextResponse.json(
          { erro: { codigo: "nao_encontrada", mensagem: "Fonte não encontrada." } },
          { status: 404 },
        );
      const limite = await fontes.podeTestar();
      if (!limite.pode)
        return NextResponse.json(
          {
            erro: {
              codigo: "limite_de_testes",
              mensagem: `Você já usou os ${limite.limite} testes de hoje. Eles voltam amanhã.`,
            },
          },
          { status: 429 },
        );
      // Testa o que está na tela agora, não o que foi salvo — o usuário
      // ajusta e testa antes de salvar.
      const alvo = criterios ? fontes.validarCriterios(criterios) : fonte.criterios;
      return NextResponse.json({ comando: await criarComando("testar_busca", { criterios: alvo }) });
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
    await fontes.remover(id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return respostaDeErro(e);
  }
}
