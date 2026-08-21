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

  if (chave === "ritmo") {
    const v = valor ?? {};
    const par = (x: unknown): x is number[] =>
      Array.isArray(x) && x.length === 2 && x.every((n) => typeof n === "number");
    if (!par(v.envios_por_dia) || v.envios_por_dia[0] < 1 || v.envios_por_dia[0] > v.envios_por_dia[1])
      return NextResponse.json({ erro: "envios/dia: mínimo ≥1 e ≤ máximo" }, { status: 400 });
    if (!par(v.inicio_janela) || !par(v.fim_janela) ||
        v.inicio_janela[1] >= v.fim_janela[0])
      return NextResponse.json({ erro: "a janela precisa abrir antes de fechar" }, { status: 400 });
    if (!Array.isArray(v.busca_horas) || v.busca_horas.length === 0 ||
        v.busca_horas.some((h: unknown) => typeof h !== "number" || h < 0 || h > 23))
      return NextResponse.json({ erro: "coletas: horas inteiras entre 0 e 23" }, { status: 400 });
    if (typeof v.validade_horas !== "number" || v.validade_horas < 1)
      return NextResponse.json({ erro: "validade em horas ≥ 1" }, { status: 400 });
    if (typeof v.proporcao_preferidas !== "number" || v.proporcao_preferidas < 0 || v.proporcao_preferidas > 1)
      return NextResponse.json({ erro: "proporção entre 0 e 1" }, { status: 400 });
  }

  if (chave === "clonador") {
    const v = valor ?? {};
    if (typeof v.ativo !== "boolean")
      return NextResponse.json({ erro: "ativo deve ser true/false" }, { status: 400 });
    if (!Array.isArray(v.grupos) || v.grupos.some((g: unknown) =>
        typeof g !== "string" || !/^[0-9]+@g\.us$/.test(g)))
      return NextResponse.json({ erro: "grupos: lista de JIDs terminando em @g.us" }, { status: 400 });
    if (typeof v.intervalo_seg !== "number" || v.intervalo_seg < 60)
      return NextResponse.json({ erro: "intervalo mínimo: 60s" }, { status: 400 });
    if (typeof v.janela_min !== "number" || v.janela_min < 10 || v.janela_min > 720)
      return NextResponse.json({ erro: "janela entre 10 e 720 minutos" }, { status: 400 });
  }

  if (chave === "tracking") {
    if (typeof valor?.ativo !== "boolean")
      return NextResponse.json({ erro: "tracking: ativo deve ser true/false" }, { status: 400 });
    if (valor.ativo && !/^https?:\/\/[^\s]+$/.test(valor.base ?? ""))
      return NextResponse.json({ erro: "tracking ligado exige base https://…" }, { status: 400 });
  }

  if (chave === "canal") {
    if (typeof valor?.grupo !== "string" || !/^[0-9]+@g\.us$/.test(valor.grupo))
      return NextResponse.json({ erro: "destino: JID de grupo terminando em @g.us" }, { status: 400 });
  }

  await executar(
    "INSERT INTO config (perfil, chave, valor, atualizado_em) VALUES (?, ?, ?, ?) " +
    "ON CONFLICT (perfil, chave) DO UPDATE SET valor = excluded.valor, atualizado_em = excluded.atualizado_em",
    [perfil, chave, JSON.stringify(valor), new Date().toISOString()]);
  return NextResponse.json({ ok: true });
}
