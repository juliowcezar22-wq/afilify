import { NextResponse } from "next/server";
import * as servico from "@/lib/projetos-servico";
import { tiposDeNicho } from "@/lib/projetos-repo";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [projetos, tipos] = await Promise.all([servico.listar(), tiposDeNicho()]);
    return NextResponse.json({ projetos, tipos });
  } catch (e) {
    return respostaDeErro(e);
  }
}

export async function POST(req: Request) {
  const { nome, tipoNicho } = await req.json().catch(() => ({}));
  try {
    return NextResponse.json({
      projeto: await servico.criarProjeto(String(nome ?? ""), String(tipoNicho ?? "")),
    });
  } catch (e) {
    return respostaDeErro(e);
  }
}
