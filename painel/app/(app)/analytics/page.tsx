import { todas } from "@/lib/dados";

export const dynamic = "force-dynamic";

const fmt = (n: number) => n.toLocaleString("pt-BR");

function Barras({ dados, alt }: {
  dados: Array<{ rotulo: string; valor: number; extra?: string }>; alt?: boolean;
}) {
  const max = Math.max(1, ...dados.map((d) => d.valor));
  return (
    <div className="mt-3 grid gap-1.5">
      {dados.map((d) => (
        <div key={d.rotulo} className="flex items-center gap-3 text-sm">
          <span className="w-24 shrink-0 truncate text-tinta2">{d.rotulo}</span>
          <div className="h-4 flex-1 rounded bg-carta2">
            <div className={`h-4 rounded ${alt ? "bg-acento/40" : "bg-acento"}`}
              style={{ width: `${(d.valor / max) * 100}%` }} />
          </div>
          <span className="w-20 shrink-0 text-right font-mono text-xs tabular-nums">
            {fmt(d.valor)}{d.extra ? ` ${d.extra}` : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

export default async function Analytics() {
  // enviado_em é ISO local (-03:00): substr resolve dia e hora sem conversão.
  // Corte calculado em JS (não datetime('now')) — mesma query serve no Postgres.
  const corte = new Date(Date.now() - 14 * 864e5)
    .toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
  const [porDia, porHora, marcas, origem, kpis] = await Promise.all([
    todas(`SELECT substr(enviado_em,1,10) dia,
                  COUNT(*) n,
                  SUM(CASE WHEN origem='clone' THEN 1 ELSE 0 END) clones
           FROM ofertas WHERE status_envio='ENVIADO'
             AND enviado_em >= ?
           GROUP BY dia ORDER BY dia DESC LIMIT 14`, [corte]),
    todas(`SELECT substr(enviado_em,12,2) hora, COUNT(*) n
           FROM ofertas WHERE status_envio='ENVIADO'
             AND enviado_em >= ?
           GROUP BY hora ORDER BY hora`, [corte]),
    todas(`SELECT marca, COUNT(*) n,
                  AVG(desconto_pct) desc_medio
           FROM ofertas WHERE status_envio='ENVIADO' AND marca != ''
             AND enviado_em >= ?
           GROUP BY marca ORDER BY n DESC LIMIT 12`, [corte]),
    todas(`SELECT origem, COUNT(*) n
           FROM ofertas WHERE status_envio='ENVIADO'
             AND enviado_em >= ?
           GROUP BY origem`, [corte]),
    todas(`SELECT COUNT(*) total,
                  COUNT(DISTINCT substr(enviado_em,1,10)) dias,
                  AVG(desconto_pct) desc_medio,
                  AVG(preco_promocional) ticket
           FROM ofertas WHERE status_envio='ENVIADO'
             AND enviado_em >= ?`, [corte]),
  ]);

  let cliques = 0;
  try {
    const c = await todas(
      "SELECT COUNT(*) n FROM cliques WHERE quando >= ?", [corte]);
    cliques = Number(c[0]?.n ?? 0);
  } catch {} // tabela ainda não migrada neste engine

  const k = kpis[0] ?? {};
  const total = Number(k.total ?? 0);
  const clones = Number(origem.find((o) => o.origem === "clone")?.n ?? 0);
  const cards: Array<[string, string]> = [
    ["publicadas (14d)", fmt(total)],
    ["média por dia", fmt(Math.round(total / Math.max(1, Number(k.dias ?? 1))))],
    ["vindas do copiador", total ? `${Math.round((clones / total) * 100)}%` : "—"],
    ["desconto médio", k.desc_medio ? `${Math.round(Number(k.desc_medio))}%` : "—"],
    ["ticket médio", k.ticket ? `R$ ${Number(k.ticket).toFixed(2)}` : "—"],
    ["cliques rastreados", cliques ? fmt(cliques) : "—"],
  ];

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <p className="mt-1 text-sm text-tinta2">Últimos 14 dias de publicação.</p>

      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-6">
        {cards.map(([r, v]) => (
          <div key={r} className="rounded-xl border border-linha bg-carta p-4">
            <p className="text-[11px] uppercase tracking-wider text-tinta2">{r}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{v}</p>
          </div>
        ))}
      </div>

      <section className="mt-6 rounded-xl border border-linha bg-carta p-6">
        <h2 className="text-sm font-semibold">Publicações por dia
          <span className="ml-2 font-normal text-tinta2">(escuro = copiador)</span></h2>
        <div className="mt-3 grid gap-1.5">
          {porDia.map((d) => {
            const n = Number(d.n), cl = Number(d.clones);
            const max = Math.max(1, ...porDia.map((x) => Number(x.n)));
            return (
              <div key={String(d.dia)} className="flex items-center gap-3 text-sm">
                <span className="w-24 shrink-0 text-tinta2">
                  {String(d.dia).slice(8, 10)}/{String(d.dia).slice(5, 7)}</span>
                <div className="flex h-4 flex-1 gap-px rounded bg-carta2">
                  <div className="h-4 rounded-l bg-acento/40"
                    style={{ width: `${(cl / max) * 100}%` }} />
                  <div className="h-4 rounded-r bg-acento"
                    style={{ width: `${((n - cl) / max) * 100}%` }} />
                </div>
                <span className="w-20 shrink-0 text-right font-mono text-xs tabular-nums">
                  {fmt(n)} · {fmt(cl)}©</span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-linha bg-carta p-6">
          <h2 className="text-sm font-semibold">Horários que mais publicam</h2>
          <Barras dados={porHora.map((h) => ({
            rotulo: `${h.hora}h`, valor: Number(h.n) }))} alt />
        </section>

        <section className="rounded-xl border border-linha bg-carta p-6">
          <h2 className="text-sm font-semibold">Top marcas publicadas</h2>
          <Barras dados={marcas.map((m) => ({
            rotulo: String(m.marca), valor: Number(m.n),
            extra: `· ${Math.round(Number(m.desc_medio))}%` }))} />
        </section>
      </div>
    </div>
  );
}
