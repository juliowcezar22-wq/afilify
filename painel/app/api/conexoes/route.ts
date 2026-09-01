import { NextResponse } from "next/server";
import * as servico from "@/lib/conexoes-servico";
import { respostaDeErro } from "@/lib/resposta";

export const dynamic = "force-dynamic";

/** Conexões do workspace, prontas para exibir (sem credencial, nunca). */
export async function GET(req: Request) {
  const plataforma = new URL(req.url).searchParams.get("plataforma");
  try {
    const conexoes = await servico.listar(
      (plataforma as "whatsapp" | "mercadolivre" | "shopee") || undefined,
    );
    return NextResponse.json({ conexoes, adotaveis: await servico.contasAdotaveis() });
  } catch {
    return NextResponse.json(
      { erro: { codigo: "falha_ao_listar", mensagem: "Não conseguimos carregar suas conexões agora." } },
      { status: 500 },
    );
  }
}

/** Adiciona uma conexão. `adotar` reaproveita uma conta já existente (D25b). */
export async function POST(req: Request) {
  const { plataforma, nome, adotar } = await req.json().catch(() => ({}));
  if (plataforma !== "whatsapp")
    return NextResponse.json(
      { erro: { codigo: "plataforma_indisponivel", mensagem: "Esta plataforma ainda não pode ser conectada por aqui." } },
      { status: 400 },
    );
  try {
    return NextResponse.json({ conexao: await servico.adicionarWhatsApp(String(nome ?? ""), String(adotar ?? "")) });
  } catch (e) {
    return respostaDeErro(e);
  }
}
