import { readFile } from "node:fs/promises";
import path from "node:path";
import { todas } from "@/lib/dados";

export const dynamic = "force-dynamic";

const COR: Record<string, string> = {
  "✓": "text-ok", "✗": "text-erro", "!": "text-alerta",
};

/* O motor espelha cada linha na tabela `logs` — funciona com motor e
   painel em máquinas diferentes. Sem linhas no banco (motor antigo),
   cai no arquivo local LOG_PATH. */
export default async function Logs({ searchParams }:
  { searchParams: Promise<{ q?: string }> }) {
  const { q } = await searchParams;

  let doBanco: Array<{ ts: string; nivel: string; texto: string }> = [];
  try {
    doBanco = (await todas(
      q ? `SELECT ts, nivel, texto FROM logs WHERE texto LIKE ? ORDER BY id DESC LIMIT 300`
        : `SELECT ts, nivel, texto FROM logs ORDER BY id DESC LIMIT 300`,
      q ? [`%${q}%`] : [],
    )) as never[];
  } catch { /* tabela ainda não migrada */ }

  let doArquivo: string[] = [];
  if (doBanco.length === 0 && process.env.LOG_PATH) {
    try {
      const bruto = await readFile(path.resolve(process.cwd(), process.env.LOG_PATH), "utf-8");
      doArquivo = bruto.split("\n")
        .map((l) => l.replace(/\x1b\[[0-9;]*m/g, ""))
        .filter((l) => l.trim())
        .filter((l) => !q || l.toLowerCase().includes(q.toLowerCase()))
        .slice(-300).reverse();
    } catch { /* arquivo indisponível */ }
  }
  const total = doBanco.length || doArquivo.length;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Logs do motor</h1>
          <p className="mt-1 text-sm text-tinta2">
            últimas {total} linhas · mais recentes primeiro
            {doBanco.length > 0 ? " · direto do banco" : ""}
          </p>
        </div>
        <form action="/logs">
          <input name="q" defaultValue={q ?? ""} placeholder="filtrar (ex.: enviada, clonado, ✗)…"
            className="w-72 rounded-lg border border-linha bg-carta2 px-3 py-1.5 text-sm outline-none focus:border-acento" />
        </form>
      </div>

      {total === 0 ? (
        <div className="mt-8 rounded-xl border border-linha bg-carta p-6 text-sm text-tinta2">
          Nenhuma linha ainda{q ? " com esse filtro" : ""} — o motor grava aqui
          a partir da primeira subida com o espelhamento ligado.
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border border-linha bg-carta">
          <table className="w-full text-sm">
            <tbody>
              {doBanco.map((l, i) => (
                <tr key={i} className="border-b border-linha/50 last:border-0">
                  <td className="whitespace-nowrap px-4 py-1.5 font-mono text-xs text-tinta2">
                    {String(l.ts).slice(5, 16).replace("T", " ")}</td>
                  <td className={`px-2 py-1.5 font-mono ${COR[l.nivel] ?? "text-tinta2"}`}>{l.nivel}</td>
                  <td className="px-2 py-1.5">{l.texto}</td>
                </tr>
              ))}
              {doArquivo.map((l, i) => (
                <tr key={i} className="border-b border-linha/50 last:border-0">
                  <td className="px-4 py-1.5 font-mono text-xs" colSpan={3}>{l}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
