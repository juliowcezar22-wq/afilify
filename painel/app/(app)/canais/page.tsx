import { todas } from "@/lib/dados";
import { SeletorDestino } from "./seletor";

export const dynamic = "force-dynamic";

async function gruposDaConta() {
  const url = process.env.UAZAPI_URL, token = process.env.UAZAPI_TOKEN;
  if (!url || !token) return [];
  try {
    const r = await fetch(`${url}/group/list`, {
      headers: { token }, signal: AbortSignal.timeout(6000), cache: "no-store" });
    const d = await r.json();
    return (d.groups ?? []).map((g: Record<string, unknown>) => ({
      jid: String(g.JID ?? ""), nome: String(g.Name ?? ""),
    }));
  } catch { return []; }
}

export default async function Canais() {
  const [cfgs, grupos] = await Promise.all([
    todas("SELECT perfil, valor FROM config WHERE chave='canal'"),
    gruposDaConta(),
  ]);
  const hoje = new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
  const enviadas = Object.fromEntries((await todas(
    `SELECT e.canal, COUNT(*) AS n FROM entregas e
     WHERE e.status='enviada' AND e.atualizado_em LIKE ? GROUP BY e.canal`,
    [`${hoje}%`])).map((r) => [String(r.canal), Number(r.n)]));

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-xl font-semibold">Grupos & canais</h1>
      <p className="mt-1 text-sm text-tinta2">
        Para onde cada projeto publica. Trocar o destino vale para as
        <strong className="text-tinta"> próximas</strong> mensagens — as entregas
        já feitas ficam registradas no grupo antigo.
      </p>

      {cfgs.map((c) => {
        let grupo = "";
        try { grupo = JSON.parse(String(c.valor)).grupo ?? ""; } catch {}
        return (
          <SeletorDestino key={String(c.perfil)} perfil={String(c.perfil)}
            atual={grupo} grupos={grupos}
            enviadasHoje={enviadas[grupo] ?? 0} />
        );
      })}

      <div className="mt-8 rounded-xl border border-linha bg-carta p-5">
        <p className="text-xs uppercase tracking-wider text-tinta2">
          Todos os grupos da conta ({grupos.length})
        </p>
        <ul className="mt-3 grid gap-1.5 text-sm">
          {grupos.map((g: { jid: string; nome: string }) => (
            <li key={g.jid} className="flex items-baseline justify-between gap-3">
              <span className="truncate">{g.nome || "(sem nome)"}</span>
              <span className="shrink-0 font-mono text-xs text-tinta2">{g.jid}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
