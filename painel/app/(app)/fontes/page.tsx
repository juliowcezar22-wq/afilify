import { todas } from "@/lib/dados";
import { FormFontes } from "./form";

export const dynamic = "force-dynamic";

async function gruposDaConta(): Promise<Array<{ jid: string; nome: string }>> {
  const url = process.env.UAZAPI_URL, token = process.env.UAZAPI_TOKEN;
  if (!url || !token) return [];
  try {
    const r = await fetch(`${url}/group/list`, {
      headers: { token }, signal: AbortSignal.timeout(6000), cache: "no-store" });
    const d = await r.json();
    return (d.groups ?? []).map((g: Record<string, unknown>) =>
      ({ jid: String(g.JID ?? ""), nome: String(g.Name ?? "") }));
  } catch { return []; }
}

export default async function Copiador() {
  const cfgs = await todas("SELECT perfil, valor FROM config WHERE chave='clonador'");
  const grupos = await gruposDaConta();
  const clones = await todas(
    `SELECT nome, marca, desconto_pct, preco_promocional, rival_nome, rival_preco,
            status_envio, criado_em
     FROM ofertas WHERE origem='clone' ORDER BY criado_em DESC LIMIT 15`);

  const reais = (v: unknown) => v == null ? "—"
    : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold">Copiador</h1>
      <p className="mt-1 text-sm text-tinta2">
        Monitora grupos rivais, identifica o produto anunciado e o traz para a SUA fila
        com o SEU link — reconstruído no seu template, nunca copiando a mídia deles.
      </p>

      {cfgs.map((c) => {
        let cfg = {};
        try { cfg = JSON.parse(String(c.valor)); } catch {}
        return <FormFontes key={String(c.perfil)} perfil={String(c.perfil)}
                 inicial={cfg} disponiveis={grupos} />;
      })}

      <div className="mt-8 rounded-xl border border-linha bg-carta p-5">
        <p className="text-xs uppercase tracking-wider text-tinta2">Últimos clones</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-linha text-left text-[11px] uppercase tracking-wider text-tinta2">
              <th className="py-2 pr-3">Produto</th><th className="py-2 pr-3">Rival anunciou</th>
              <th className="py-2 pr-3">No nosso</th><th className="py-2">Status</th>
            </tr></thead>
            <tbody>
              {clones.map((o, i) => (
                <tr key={i} className="border-b border-linha/50">
                  <td className="max-w-sm truncate py-2 pr-3">{String(o.nome)}</td>
                  <td className="whitespace-nowrap py-2 pr-3 text-tinta2">
                    {String(o.rival_nome || "—").slice(0, 28)} · {reais(o.rival_preco)}</td>
                  <td className="whitespace-nowrap py-2 pr-3">
                    {reais(o.preco_promocional)}
                    <span className="ml-1 text-acento">−{Number(o.desconto_pct ?? 0)}%</span></td>
                  <td className="py-2 text-xs">{String(o.status_envio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
