import Link from "next/link";
import * as operacao from "@/lib/operacao";
import { listarProjetos as listarProjetosDaConta } from "@/lib/projetos-repo";
import { Cartao as CartaoOp } from "@/components/ui/cartao";
import { Selo as SeloOp } from "@/components/ui/selo";
import { todas, uma } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import {
  reais,
  dataCurta,
  statusOferta,
  origemOferta,
  motivoLegivel,
  SQL_ATENCAO,
  SQL_IGNORADA,
} from "@/lib/formatos";
import { classesBotao } from "@/components/ui/botao";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Selo } from "@/components/ui/selo";
import { Paginacao } from "@/components/ui/paginacao";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { CONTROLE } from "@/components/ui/campos";
import { Acoes } from "./acoes";

export const dynamic = "force-dynamic";

const POR_PAGINA = 40;
const n = (v: unknown) => Number(v ?? 0);

type Busca = { q?: string; status?: string; origem?: string; pagina?: string };

function Filtro({ rotulo, ativo, href }: { rotulo: string; ativo: boolean; href: string }) {
  return (
    <Link
      href={href}
      aria-pressed={ativo}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
        ativo
          ? "border-acento/60 bg-acento/10 text-acento"
          : "border-linha text-tinta2 hover:border-linha2 hover:text-tinta"
      }`}
    >
      {rotulo}
    </Link>
  );
}

function Preco({ o }: { o: Record<string, unknown> }) {
  return (
    <div className="whitespace-nowrap tabular-nums">
      {o.preco_original != null && (
        <span className="text-xs text-tinta3 line-through">{reais(o.preco_original)}</span>
      )}
      <span className="ml-2 font-medium">{reais(o.preco_promocional)}</span>
      <span className="ml-2 text-xs font-semibold text-acento">−{n(o.desconto_pct)}%</span>
    </div>
  );
}

function LinhaSecundaria({ o }: { o: Record<string, unknown> }) {
  const st = statusOferta(o.status_envio, o.erro);
  const motivo = st.tom === "erro" ? motivoLegivel(o.erro) : "";
  return (
    <p className="mt-0.5 truncate text-xs text-tinta3">
      {origemOferta(o.origem)} · {dataCurta(o.criado_em)}
      {String(o.marca ?? "") && <> · {String(o.marca)}</>}
      {motivo && <span className="text-erro"> · {motivo}</span>}
    </p>
  );
}

/** Catálogo das oportunidades encontradas — busca, filtros e ações. */
export default async function Ofertas({ searchParams }: { searchParams: Promise<Busca> }) {
  const b = await searchParams;
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);

  const cond: string[] = ["1=1"];
  const params: unknown[] = [];
  if (b.q) {
    cond.push("(nome LIKE ? OR marca LIKE ? OR mlb_id LIKE ?)");
    params.push(`%${b.q}%`, `%${b.q}%`, `%${b.q}%`);
  }
  // "Com problema" não inclui as que VOCÊ ignorou — elas têm filtro próprio
  if (b.status === "ERRO") cond.push(`(${SQL_ATENCAO})`);
  else if (b.status === "IGNORADA") cond.push(`(${SQL_IGNORADA})`);
  else if (b.status) {
    cond.push("status_envio = ?");
    params.push(b.status);
  }
  if (b.origem) {
    cond.push("origem = ?");
    params.push(b.origem);
  }
  const onde = cond.join(" AND ") + proj.sql;
  const todosParams = [...params, ...proj.params];

  const total = n(
    (await uma(`SELECT COUNT(*) AS n FROM ofertas WHERE ${onde}`, todosParams))?.n,
  );
  // página fora do alcance (bookmark velho) volta para a última existente
  const pagina = Math.min(
    Math.max(1, n(b.pagina) || 1),
    Math.max(1, Math.ceil(total / POR_PAGINA)),
  );
  const linhas = await todas(
    `SELECT mlb_id, nome, marca, url, preco_original, preco_promocional, desconto_pct,
            status_envio, origem, criado_em, erro
     FROM ofertas WHERE ${onde}
     ORDER BY criado_em DESC LIMIT ${POR_PAGINA} OFFSET ${(pagina - 1) * POR_PAGINA}`,
    todosParams,
  );

  const href = (mudancas: Partial<Busca>) => {
    const q = new URLSearchParams(
      Object.entries({ ...b, pagina: "", ...mudancas }).filter(([, v]) => v) as [
        string,
        string,
      ][],
    ).toString();
    return q ? `/ofertas?${q}` : "/ofertas";
  };

  const filtro = (chave: "status" | "origem", valor: string) => ({
    ativo: (b[chave] ?? "") === valor,
    href: href({ [chave]: (b[chave] ?? "") === valor ? "" : valor }),
  });

  const temFiltro = Boolean(b.q || b.status || b.origem);


  // Ofertas dos projetos criados na interface. O bloco legado abaixo segue
  // servindo os projetos que ainda vêm de arquivo.
  const ofertasNovas = await (async () => {
    try {
      const saida: Array<{ projeto: string; linhas: operacao.OfertaLinha[] }> = [];
      for (const proj of await listarProjetosDaConta()) {
        const linhas = await operacao.ofertas(proj.id, 20);
        if (linhas.length) saida.push({ projeto: proj.nome, linhas });
      }
      return saida;
    } catch {
      return [];
    }
  })();

  return (
    <div className="mx-auto max-w-6xl">
      {ofertasNovas.map((g) => (
        <CartaoOp key={g.projeto} className="mb-4" titulo={g.projeto}>
          <ul className="grid grid-cols-1 gap-3">
            {g.linhas.map((o) => (
              <li
                key={o.id}
                className="grid grid-cols-1 gap-1 border-t border-linha pt-3 first:border-0 first:pt-0"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="min-w-0 flex-1 truncate text-sm">{o.nome}</span>
                  <SeloOp
                    tom={o.estado === "publicada" ? "ok" : o.estado === "retida" ? "alerta" : "neutro"}
                  >
                    {operacao.rotuloOferta(o.estado)}
                  </SeloOp>
                </div>
                <p className="text-sm text-tinta2">
                  {o.origem}
                  {o.desconto ? ` · −${o.desconto}%` : ""}
                  {o.preco != null ? ` · ${reais(o.preco)}` : ""}
                </p>
                {o.motivo && <p className="text-sm text-alerta">{o.motivo}</p>}
              </li>
            ))}
          </ul>
        </CartaoOp>
      ))}
      <CabecalhoPagina
        titulo="Ofertas"
        descricao={
          ctx.ativo
            ? `Oportunidades encontradas para ${ctx.ativo.nome}.`
            : "Oportunidades encontradas para os seus projetos."
        }
        acoes={
          <form action="/ofertas" className="flex gap-2">
            {b.status && <input type="hidden" name="status" value={b.status} />}
            {b.origem && <input type="hidden" name="origem" value={b.origem} />}
            <label htmlFor="busca-ofertas" className="sr-only">
              Buscar produto ou marca
            </label>
            <input
              id="busca-ofertas"
              name="q"
              defaultValue={b.q ?? ""}
              placeholder="Buscar produto ou marca…"
              className={`${CONTROLE} w-56 md:w-64`}
            />
            <button type="submit" className={classesBotao("primario")}>
              Buscar
            </button>
          </form>
        }
      />

      <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-2">
        <span className="text-xs text-tinta3">Status</span>
        <Filtro rotulo="Aguardando" {...filtro("status", "PENDENTE")} />
        <Filtro rotulo="Publicadas" {...filtro("status", "ENVIADO")} />
        <Filtro rotulo="Com problema" {...filtro("status", "ERRO")} />
        <Filtro rotulo="Ignoradas" {...filtro("status", "IGNORADA")} />
        <span aria-hidden className="mx-2 h-4 w-px bg-linha" />
        <span className="text-xs text-tinta3">Origem</span>
        <Filtro rotulo="Busca automática" {...filtro("origem", "busca")} />
        <Filtro rotulo="Monitoramento" {...filtro("origem", "clone")} />
        {temFiltro && (
          <Link href="/ofertas" className="ml-1 text-xs text-tinta2 underline hover:text-tinta">
            Limpar
          </Link>
        )}
      </div>

      {linhas.length === 0 ? (
        <div className="mt-6">
          <EstadoVazio
            titulo={temFiltro ? "Nada por aqui com esses filtros" : "Nenhuma oferta ainda"}
            descricao={
              temFiltro
                ? "Tente outra busca ou limpe os filtros."
                : "Assim que as fontes do seu projeto encontrarem promoções, elas aparecem aqui."
            }
            acao={
              temFiltro ? (
                <Link href="/ofertas" className="text-sm text-acento hover:underline">
                  Limpar filtros
                </Link>
              ) : undefined
            }
          />
        </div>
      ) : (
        <>
          {/* Tabela (≥md) — sem overflow horizontal: colunas controladas */}
          <div className="mt-5 hidden rounded-xl border border-linha bg-carta md:block">
            <table className="w-full table-fixed text-sm">
              <thead>
                <tr className="border-b border-linha text-left text-[11px] uppercase tracking-wider text-tinta2">
                  <th className="sticky top-0 rounded-tl-xl bg-carta px-4 py-3">Oferta</th>
                  <th className="sticky top-0 w-56 bg-carta px-3 py-3">Preço</th>
                  <th className="sticky top-0 w-40 bg-carta px-3 py-3">Status</th>
                  <th className="sticky top-0 w-40 rounded-tr-xl bg-carta px-3 py-3 text-right">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((o) => {
                  const st = statusOferta(o.status_envio, o.erro);
                  return (
                    <tr key={String(o.mlb_id)} className="border-b border-linha/50 last:border-0">
                      <td className="px-4 py-3">
                        <p className="line-clamp-2 font-medium leading-snug">
                          {String(o.url) ? (
                            <a
                              href={String(o.url)}
                              target="_blank"
                              rel="noreferrer"
                              className="hover:underline"
                            >
                              {String(o.nome)}
                            </a>
                          ) : (
                            String(o.nome)
                          )}
                        </p>
                        <LinhaSecundaria o={o} />
                      </td>
                      <td className="px-3 py-3">
                        <Preco o={o} />
                      </td>
                      <td className="px-3 py-3">
                        <Selo tom={st.tom}>{st.rotulo}</Selo>
                      </td>
                      <td className="px-3 py-3">
                        <Acoes id={String(o.mlb_id)} status={String(o.status_envio)} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Cartões (<md) */}
          <ul className="mt-5 grid grid-cols-1 gap-3 md:hidden">
            {linhas.map((o) => {
              const st = statusOferta(o.status_envio, o.erro);
              return (
                <li key={String(o.mlb_id)} className="rounded-xl border border-linha bg-carta p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="line-clamp-2 min-w-0 flex-1 text-sm font-medium leading-snug">
                      {String(o.nome)}
                    </p>
                    <span className="shrink-0">
                      <Selo tom={st.tom}>{st.rotulo}</Selo>
                    </span>
                  </div>
                  <div className="mt-2 text-sm">
                    <Preco o={o} />
                  </div>
                  <LinhaSecundaria o={o} />
                  <div className="mt-3">
                    <Acoes id={String(o.mlb_id)} status={String(o.status_envio)} />
                  </div>
                </li>
              );
            })}
          </ul>

          <Paginacao
            total={total}
            pagina={pagina}
            porPagina={POR_PAGINA}
            criarHref={(p) => href({ pagina: String(p) })}
          />
        </>
      )}
    </div>
  );
}
