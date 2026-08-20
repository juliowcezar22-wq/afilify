import { NextResponse } from "next/server";
import { executar, uma } from "@/lib/dados";

export const dynamic = "force-dynamic";

/**
 * Ações sobre uma oferta. O painel não fala com a uazapi — quem publica é
 * SEMPRE o worker, no ritmo do plano; aqui só mudamos o estado da fila.
 *   ignorar      tira da fila (ERRO com motivo legível, entrega liberada)
 *   reenfileirar volta ERRO/ENVIADA para a fila (zera tentativas e entrega)
 */
export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { acao } = await req.json().catch(() => ({}));
  const oferta = await uma("SELECT mlb_id, status_envio FROM ofertas WHERE mlb_id = ?", [id]);
  if (!oferta) return NextResponse.json({ erro: "oferta não encontrada" }, { status: 404 });
  const ts = new Date().toISOString();

  if (acao === "ignorar") {
    await executar(
      "UPDATE ofertas SET status_envio='ERRO', erro='ignorada pelo painel', atualizado_em=? WHERE mlb_id=?",
      [ts, id]);
    await executar("DELETE FROM entregas WHERE mlb_id=?", [id]);
    return NextResponse.json({ ok: true, status: "ERRO" });
  }
  if (acao === "reenfileirar") {
    await executar(
      "UPDATE ofertas SET status_envio='PENDENTE', erro='', tentativas=0, " +
      "proxima_tentativa=NULL, atualizado_em=? WHERE mlb_id=?", [ts, id]);
    await executar("DELETE FROM entregas WHERE mlb_id=?", [id]);
    return NextResponse.json({ ok: true, status: "PENDENTE" });
  }
  return NextResponse.json({ erro: `ação desconhecida: ${acao}` }, { status: 400 });
}
