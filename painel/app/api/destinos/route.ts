import { NextResponse } from "next/server";
import * as destinos from "@/lib/destinos";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const automacao = new URL(req.url).searchParams.get("automacao") ?? "";
  try {
    return NextResponse.json({ destinos: await destinos.listar(automacao) });
  } catch (e) {
    return respostaDeErro(e);
  }
}

export async function POST(req: Request) {
  const { automacao, conexao, alvo, nome } = await req.json().catch(() => ({}));
  try {
    const r = await destinos.adicionar(
      String(automacao ?? ""),
      String(conexao ?? ""),
      String(alvo ?? ""),
      String(nome ?? ""),
    );
    return NextResponse.json(r);
  } catch (e) {
    return respostaDeErro(e);
  }
}
