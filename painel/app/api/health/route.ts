import { NextResponse } from "next/server";
import { obterBanco, todas } from "@/lib/dados";

export const dynamic = "force-dynamic";

export async function GET() {
  const banco = obterBanco();
  let estadoBanco: string = "ausente";
  let workers: Array<{ perfil: string; visto_em: string; online: boolean }> = [];
  if (banco) {
    try {
      const linhas = await todas(
        "SELECT chave, valor FROM estado WHERE chave LIKE '%:heartbeat'");
      const agora = Date.now();
      workers = linhas.map((l) => {
        const perfil = String(l.chave).replace(":heartbeat", "");
        const visto = String(l.valor);
        return { perfil, visto_em: visto,
                 online: agora - new Date(visto).getTime() < 90_000 };
      });
      estadoBanco = banco.motor;
    } catch { estadoBanco = "erro"; }
  }
  return NextResponse.json({ ok: true, banco: estadoBanco, workers,
                             ts: new Date().toISOString() });
}
