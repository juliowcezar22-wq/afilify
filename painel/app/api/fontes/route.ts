import { NextResponse } from "next/server";
import * as fontes from "@/lib/fontes";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const automacao = new URL(req.url).searchParams.get("automacao") ?? "";
  try {
    return NextResponse.json({ fontes: await fontes.listar(automacao) });
  } catch (e) {
    return respostaDeErro(e);
  }
}

export async function POST(req: Request) {
  const { automacao, criterios, agenda } = await req.json().catch(() => ({}));
  try {
    const validos = fontes.validarCriterios(criterios);
    return NextResponse.json({
      fonte: await fontes.criar(String(automacao ?? ""), validos, {
        horarios: Array.isArray(agenda?.horarios) ? agenda.horarios.map(Number) : [7, 15],
      }),
    });
  } catch (e) {
    return respostaDeErro(e);
  }
}
