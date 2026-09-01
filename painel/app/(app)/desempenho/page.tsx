import Link from "next/link";
import { todas } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { dataCorte, diaCurto } from "@/lib/formatos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { Indicador } from "@/components/ui/indicador";

export const dynamic = "force-dynamic";

const fmt = (v: number) => v.toLocaleString("pt-BR");
const PERIODOS = [7, 14, 30] as const;

function Barras({
  dados,
  alt,
}: {
  dados: Array<{ rotulo: string; valor: number; extra?: string }>;
  alt?: boolean;
}) {
  const max = Math.max(1, ...dados.map((d) => d.valor));
  return (
    <div className="mt-3 grid grid-cols-1 gap-1.5">
      {dados.map((d) => (
        <div key={d.rotulo} className="flex items-center gap-3 text-sm">
          <span className="w-20 shrink-0 truncate text-tinta2">{d.rotulo}</span>
          <div className="h-4 min-w-0 flex-1 rounded bg-carta2">
            <div
              className={`h-4 max-w-full rounded ${alt ? "bg-acento/40" : "bg-acento"}`}
              style={{ width: `${(d.valor / max) * 100}%` }}
            />
          </div>
          <span className="w-20 shrink-0 text-right text-xs tabular-nums text-tinta2">
            {fmt(d.valor)}
            {d.extra ? ` ${d.extra}` : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Padrões ao longo do período — o "agora" mora no Dashboard. */
export default async function Desempenho({
  searchParams,
}: {
  searchParams: Promise<{ periodo?: string }>;
}) {
  const { periodo } = await searchParams;
  const dias = PERIODOS.includes(Number(periodo) as (typeof PERIODOS)[number])
    ? Number(periodo)
    : 14;
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);
  const corte = dataCorte(dias);

  const [porDia, porHora, marcas, origem, kpis] = await Promise.all([
    todas(
      `SELECT substr(enviado_em,1,10) dia,
              COUNT(*) n,
              SUM(CASE WHEN origem='clone' THEN 1 ELSE 0 END) monitoramento
       FROM ofertas WHERE status_envio='ENVIADO' AND enviado_em >= ?${proj.sql}
       GROUP BY dia ORDER BY dia DESC LIMIT ${dias}`,
      [corte, ...proj.params],
    ),
    todas(
      `SELECT substr(enviado_em,12,2) hora, COUNT(*) n
       FROM ofertas WHERE status_envio='ENVIADO' AND enviado_em >= ?${proj.sql}
       GROUP BY hora ORDER BY hora`,
      [corte, ...proj.params],
    ),
    todas(
      `SELECT marca, COUNT(*) n, AVG(desconto_pct) desc_medio
       FROM ofertas WHERE status_envio='ENVIADO' AND marca != '' AND enviado_em >= ?${proj.sql}
       GROUP BY marca ORDER BY n DESC LIMIT 12`,
      [corte, ...proj.params],
    ),
    todas(
      `SELECT origem, COUNT(*) n
       FROM ofertas WHERE status_envio='ENVIADO' AND enviado_em >= ?${proj.sql}
       GROUP BY origem`,
      [corte, ...proj.params],
    ),
    todas(
      `SELECT COUNT(*) total,
              COUNT(DISTINCT substr(enviado_em,1,10)) dias,
              AVG(desconto_pct) desc_medio,
              AVG(preco_promocional) ticket
       FROM ofertas WHERE status_envio='ENVIADO' AND enviado_em >= ?${proj.sql}`,
      [corte, ...proj.params],
    ),
  ]);

  // cliques respeitam o projeto ativo (join via código do link da oferta);
  // null = recurso indisponível neste ambiente (≠ 0 cliques)
  let cliques: number | null = null;
  try {
    const c = ctx.ativo
      ? await todas(
          `SELECT COUNT(*) n FROM cliques c
           JOIN ofertas o ON o.codigo = c.codigo
           WHERE c.quando >= ? AND o.perfil = ?`,
          [corte, ctx.ativo.slug],
        )
      : await todas("SELECT COUNT(*) n FROM cliques WHERE quando >= ?", [corte]);
    cliques = Number(c[0]?.n ?? 0);
  } catch {
    /* contagem de cliques ainda não disponível neste ambiente */
  }

  const k = kpis[0] ?? {};
  const total = Number(k.total ?? 0);
  const doMonitoramento = Number(origem.find((o) => String(o.origem) === "clone")?.n ?? 0);
  const cards: Array<[string, string]> = [
    [`Publicações (${dias}d)`, fmt(total)],
    ["Média por dia", fmt(Math.round(total / Math.max(1, Number(k.dias ?? 1))))],
    ["Vindas do monitoramento", total ? `${Math.round((doMonitoramento / total) * 100)}%` : "—"],
    ["Desconto médio", k.desc_medio ? `${Math.round(Number(k.desc_medio))}%` : "—"],
    ["Preço médio publicado", k.ticket ? `R$ ${Number(k.ticket).toFixed(2)}` : "—"],
    // 0 clique é informação real; "—" só quando o recurso não existe aqui
    ["Cliques no período", cliques == null ? "—" : fmt(cliques)],
  ];

  const maxDia = Math.max(1, ...porDia.map((x) => Number(x.n)));

  return (
    <div className="mx-auto max-w-4xl">
      <CabecalhoPagina
        titulo="Desempenho"
        descricao={
          ctx.ativo
            ? `Padrões de ${ctx.ativo.nome} no período.`
            : "Padrões da sua operação no período."
        }
        acoes={
          <nav aria-label="Período" className="flex gap-1 rounded-lg border border-linha p-1">
            {PERIODOS.map((p) => (
              <Link
                key={p}
                href={`/desempenho?periodo=${p}`}
                aria-current={p === dias ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                  p === dias ? "bg-carta2 text-tinta" : "text-tinta2 hover:text-tinta"
                }`}
              >
                {p} dias
              </Link>
            ))}
          </nav>
        }
      />

      {total === 0 ? (
        <div className="mt-6">
          <EstadoVazio
            titulo="Sem publicações no período"
            descricao="Quando houver publicações, os padrões por dia, horário e marca aparecem aqui."
          />
        </div>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            {cards.map(([r, v]) => (
              <Indicador key={r} rotulo={r} valor={v} compacto />
            ))}
          </div>

          <Cartao className="mt-6" titulo="Publicações por dia">
            <p className="flex items-center gap-4 text-xs text-tinta3">
              <span className="flex items-center gap-1.5">
                <span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-acento" /> Busca automática
              </span>
              <span className="flex items-center gap-1.5">
                <span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-acento/40" /> Monitoramento
              </span>
            </p>
            <div className="mt-3 grid grid-cols-1 gap-1.5">
              {porDia.map((d) => {
                const total = Number(d.n),
                  mon = Number(d.monitoramento);
                return (
                  <div key={String(d.dia)} className="flex items-center gap-3 text-sm">
                    <span className="w-20 shrink-0 text-tinta2">{diaCurto(d.dia)}</span>
                    <div className="flex h-4 min-w-0 flex-1 gap-px overflow-hidden rounded bg-carta2">
                      <div
                        className="h-4 bg-acento/40"
                        style={{ width: `${(mon / maxDia) * 100}%` }}
                      />
                      <div
                        className="h-4 bg-acento"
                        style={{ width: `${((total - mon) / maxDia) * 100}%` }}
                      />
                    </div>
                    <span className="w-20 shrink-0 text-right text-xs tabular-nums text-tinta2">
                      {fmt(total)}
                    </span>
                  </div>
                );
              })}
            </div>
          </Cartao>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Cartao titulo="Horários que mais publicam">
              <Barras
                alt
                dados={porHora.map((h) => ({ rotulo: `${h.hora}h`, valor: Number(h.n) }))}
              />
            </Cartao>
            <Cartao titulo="Marcas mais publicadas">
              <Barras
                dados={marcas.map((m) => ({
                  rotulo: String(m.marca),
                  valor: Number(m.n),
                  extra: `· ${Math.round(Number(m.desc_medio))}%`,
                }))}
              />
            </Cartao>
          </div>
        </>
      )}
    </div>
  );
}
