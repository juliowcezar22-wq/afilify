import Link from "next/link";
import { todas, uma } from "@/lib/dados";
import { Acoes } from "./acoes";

export const dynamic = "force-dynamic";

const POR_PAGINA = 40;
const n = (v: unknown) => Number(v ?? 0);
const reais = (v: unknown) =>
  v == null ? "—" : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

type Busca = { q?: string; status?: string; origem?: string; pagina?: string };

export default async function Ofertas({ searchParams }: { searchParams: Promise<Busca> }) {
  const b = await searchParams;
  const pagina = Math.max(1, n(b.pagina) || 1);

  const cond: string[] = ["1=1"];
  const params: unknown[] = [];
  if (b.q) { cond.push("(nome LIKE ? OR marca LIKE ? OR mlb_id LIKE ?)");
             params.push(`%${b.q}%`, `%${b.q}%`, `%${b.q}%`); }
  if (b.status) { cond.push("status_envio = ?"); params.push(b.status); }
  if (b.origem) { cond.push("origem = ?"); params.push(b.origem); }
  const onde = cond.join(" AND ");

  const total = n((await uma(`SELECT COUNT(*) AS n FROM ofertas WHERE ${onde}`, params))?.n);
  const linhas = await todas(
    `SELECT mlb_id, nome, marca, preco_original, preco_promocional, desconto_pct,
            status_envio, origem, criado_em, enviado_em, link_afiliado, erro
     FROM ofertas WHERE ${onde}
     ORDER BY criado_em DESC LIMIT ${POR_PAGINA} OFFSET ${(pagina - 1) * POR_PAGINA}`,
    params);
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  const chip = (s: string) =>
    s === "ENVIADO" ? "bg-ok/15 text-ok" :
    s === "ERRO" ? "bg-erro/15 text-erro" : "bg-alerta/15 text-alerta";

  const filtro = (rot: string, chave: "status" | "origem", val: string) => {
    const ativo = b[chave] === val;
    const q = new URLSearchParams(
      Object.entries({ ...b, [chave]: ativo ? "" : val, pagina: "" })
        .filter(([, v]) => v) as [string, string][]);
    return (
      <Link key={rot} href={`/ofertas?${q}`}
        className={`rounded-full border px-3 py-1 text-xs ${
          ativo ? "border-acento text-acento" : "border-linha text-tinta2 hover:text-tinta"}`}>
        {rot}
      </Link>
    );
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Ofertas</h1>
          <p className="mt-1 text-sm text-tinta2">{total} no total · página {pagina}/{paginas}</p>
        </div>
        <form className="flex gap-2" action="/ofertas">
          <input name="q" defaultValue={b.q ?? ""} placeholder="nome, marca ou MLB…"
            className="w-64 rounded-lg border border-linha bg-carta2 px-3 py-1.5 text-sm outline-none focus:border-acento" />
          <button className="rounded-lg bg-acento px-3 py-1.5 text-sm font-semibold text-fundo">
            Buscar
          </button>
        </form>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {filtro("Pendentes", "status", "PENDENTE")}
        {filtro("Enviadas", "status", "ENVIADO")}
        {filtro("Com erro", "status", "ERRO")}
        <span className="mx-1 text-linha">·</span>
        {filtro("Clonadas", "origem", "clone")}
        {filtro("Da busca", "origem", "busca")}
      </div>

      <div className="mt-5 overflow-x-auto rounded-xl border border-linha bg-carta">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-linha text-left text-[11px] uppercase tracking-wider text-tinta2">
              <th className="px-4 py-3">Oferta</th>
              <th className="px-3 py-3">Preço</th>
              <th className="px-3 py-3">Status</th>
              <th className="px-3 py-3">Origem</th>
              <th className="px-3 py-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((o) => (
              <tr key={String(o.mlb_id)} className="border-b border-linha/50 align-top">
                <td className="max-w-md px-4 py-3">
                  <p className="truncate font-medium">{String(o.nome)}</p>
                  <p className="mt-0.5 text-xs text-tinta2">
                    {String(o.marca) || "—"} · {String(o.mlb_id)} ·
                    criada {String(o.criado_em).slice(5, 16).replace("T", " ")}
                    {o.erro ? <span className="text-erro"> · {String(o.erro)}</span> : null}
                  </p>
                </td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">
                  <span className="text-tinta2 line-through">{reais(o.preco_original)}</span>
                  <span className="ml-2">{reais(o.preco_promocional)}</span>
                  <span className="ml-2 text-acento">−{n(o.desconto_pct)}%</span>
                </td>
                <td className="px-3 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${chip(String(o.status_envio))}`}>
                    {String(o.status_envio)}
                  </span>
                </td>
                <td className="px-3 py-3 text-xs text-tinta2">{String(o.origem)}</td>
                <td className="px-3 py-3 text-right">
                  <Acoes id={String(o.mlb_id)} status={String(o.status_envio)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex gap-2 text-sm">
        {pagina > 1 && <Link className="text-acento" href={`/ofertas?${new URLSearchParams({ ...b, pagina: String(pagina - 1) } as Record<string, string>)}`}>← anterior</Link>}
        {pagina < paginas && <Link className="ml-auto text-acento" href={`/ofertas?${new URLSearchParams({ ...b, pagina: String(pagina + 1) } as Record<string, string>)}`}>próxima →</Link>}
      </div>
    </div>
  );
}
