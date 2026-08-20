import { todas, uma } from "@/lib/dados";

export const dynamic = "force-dynamic";

const n = (v: unknown) => Number(v ?? 0);
const hhmm = (h: number) => {
  const m = Math.round(h * 60);
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
};

export default async function Fila() {
  const hoje = new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });

  // plano do dia + próximo envio, por perfil (chaves "perfil:chave" do estado)
  const estado = await todas(
    "SELECT chave, valor FROM estado WHERE chave LIKE '%:plano_do_dia' OR chave LIKE '%:proximo_envio'");
  const planos: Record<string, { cota?: number; inicio?: number; fim?: number; proximo?: string }> = {};
  for (const e of estado) {
    const [perfil, chave] = String(e.chave).split(":");
    planos[perfil] ??= {};
    if (chave === "plano_do_dia") {
      try { Object.assign(planos[perfil], JSON.parse(String(e.valor))); } catch {}
    } else planos[perfil].proximo = String(e.valor);
  }
  const enviadasHoje = Object.fromEntries((await todas(
    "SELECT perfil, COUNT(*) AS n FROM ofertas WHERE status_envio='ENVIADO' AND enviado_em LIKE ? GROUP BY perfil",
    [`${hoje}%`])).map((r) => [String(r.perfil), n(r.n)]));

  // ordem aproximada do publisher: clone fura a fila, depois mais recentes
  const proximas = await todas(
    `SELECT mlb_id, nome, marca, desconto_pct, origem, perfil FROM ofertas
     WHERE status_envio='PENDENTE' AND link_afiliado != ''
       AND (proxima_tentativa IS NULL OR proxima_tentativa <= ?)
     ORDER BY CASE WHEN origem='clone' THEN 0 ELSE 1 END, criado_em DESC LIMIT 15`,
    [new Date().toISOString()]);

  const emEspera = await todas(
    `SELECT mlb_id, nome, tentativas, proxima_tentativa, erro FROM ofertas
     WHERE status_envio='PENDENTE' AND proxima_tentativa > ? ORDER BY proxima_tentativa`,
    [new Date().toISOString()]);

  const entregas = await todas(
    `SELECT e.mlb_id, e.status, e.tentativa, e.id_externo, e.atualizado_em, o.nome
     FROM entregas e LEFT JOIN ofertas o ON o.mlb_id = e.mlb_id
     ORDER BY e.atualizado_em DESC LIMIT 20`);

  const chip = (s: string) =>
    s === "enviada" ? "bg-ok/15 text-ok" :
    s === "falhou" ? "bg-erro/15 text-erro" : "bg-alerta/15 text-alerta";

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold">Fila de publicação</h1>
      <p className="mt-1 text-sm text-tinta2">O worker publica no ritmo do plano — o painel só observa e ordena.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {Object.entries(planos).map(([perfil, p]) => (
          <div key={perfil} className="rounded-xl border border-linha bg-carta p-5">
            <p className="text-xs uppercase tracking-wider text-tinta2">{perfil}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums">
              {enviadasHoje[perfil] ?? 0}<span className="text-tinta2">/{p.cota ?? "—"}</span>
              <span className="ml-2 text-sm font-normal text-tinta2">hoje</span>
            </p>
            <p className="mt-1 text-xs text-tinta2">
              janela {p.inicio != null ? hhmm(p.inicio) : "—"}–{p.fim != null ? hhmm(p.fim) : "—"}
              {p.proximo ? ` · próximo envio ${String(p.proximo).slice(11, 16)}` : ""}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-linha bg-carta p-5">
        <p className="text-xs uppercase tracking-wider text-tinta2">
          Próximas a sair <span className="normal-case">(ordem aproximada · clone fura a fila)</span>
        </p>
        <ul className="mt-3 grid gap-2 text-sm">
          {proximas.map((o, i) => (
            <li key={String(o.mlb_id)} className="flex items-baseline gap-2">
              <span className="w-5 text-xs tabular-nums text-tinta2">{i + 1}.</span>
              <span className="truncate">{String(o.nome)}</span>
              {String(o.origem) === "clone" && (
                <span className="shrink-0 rounded-full bg-carta2 px-2 text-[10px] text-tinta2">clone</span>)}
              <span className="ml-auto shrink-0 text-xs text-acento">−{n(o.desconto_pct)}%</span>
            </li>
          ))}
        </ul>
      </div>

      {emEspera.length > 0 && (
        <div className="mt-6 rounded-xl border border-linha bg-carta p-5">
          <p className="text-xs uppercase tracking-wider text-alerta">Em espera de retry</p>
          <ul className="mt-3 grid gap-2 text-sm">
            {emEspera.map((o) => (
              <li key={String(o.mlb_id)} className="flex items-baseline gap-2">
                <span className="truncate">{String(o.nome)}</span>
                <span className="ml-auto shrink-0 text-xs text-tinta2">
                  tentativa {n(o.tentativas)} · volta {String(o.proxima_tentativa).slice(11, 16)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-linha bg-carta">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-linha text-left text-[11px] uppercase tracking-wider text-tinta2">
            <th className="px-4 py-3">Entrega</th><th className="px-3 py-3">Status</th>
            <th className="px-3 py-3">Tent.</th><th className="px-3 py-3">Quando</th>
          </tr></thead>
          <tbody>
            {entregas.map((e) => (
              <tr key={`${e.mlb_id}`} className="border-b border-linha/50">
                <td className="max-w-sm truncate px-4 py-2">{String(e.nome ?? e.mlb_id)}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${chip(String(e.status))}`}>
                    {String(e.status)}</span></td>
                <td className="px-3 py-2 tabular-nums">{n(e.tentativa)}</td>
                <td className="px-3 py-2 text-xs text-tinta2">
                  {String(e.atualizado_em).slice(5, 16).replace("T", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
