import { NextResponse } from "next/server";
import { executar } from "@/lib/dados";

export const dynamic = "force-dynamic";

/** Grava uma chave de config. O motor lê a cada envio — SEM restart. */
export async function POST(req: Request) {
  const { perfil, chave, valor } = await req.json().catch(() => ({}));
  if (!perfil || !chave) return NextResponse.json({ erro: "perfil e chave obrigatórios" }, { status: 400 });

  // validação (§14): template quebrado não pode chegar ao grupo
  if (chave === "mensagem") {
    const base = String(valor?.base ?? "");
    for (const token of ["{nome}", "{link}", "{preco_promocional}"]) {
      if (!base.includes(token))
        return NextResponse.json({ erro: `o template precisa conter ${token}` }, { status: 400 });
    }
    try { // tokens desconhecidos quebrariam o .format() do Python
      const conhecidos = ["headline","nome","preco_original","preco_promocional","desconto","linha_loja","link"];
      const usados = [...base.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);
      const invalido = usados.find((t) => !conhecidos.includes(t));
      if (invalido) return NextResponse.json({ erro: `variável desconhecida: {${invalido}}` }, { status: 400 });
    } catch {}
  }
  if (chave === "headlines") {
    if (typeof valor !== "object" || Array.isArray(valor))
      return NextResponse.json({ erro: "headlines deve ser um objeto de listas" }, { status: 400 });
    for (const [pool, lista] of Object.entries(valor))
      if (!Array.isArray(lista) || lista.some((x) => typeof x !== "string" || !x.trim()))
        return NextResponse.json({ erro: `pool "${pool}" inválido` }, { status: 400 });
  }

  await executar(
    "INSERT INTO config (perfil, chave, valor, atualizado_em) VALUES (?, ?, ?, ?) " +
    "ON CONFLICT (perfil, chave) DO UPDATE SET valor = excluded.valor, atualizado_em = excluded.atualizado_em",
    [perfil, chave, JSON.stringify(valor), new Date().toISOString()]);
  return NextResponse.json({ ok: true });
}
