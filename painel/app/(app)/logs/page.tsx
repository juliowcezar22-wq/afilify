import { readFile } from "node:fs/promises";
import path from "node:path";

export const dynamic = "force-dynamic";

/* Lê o log do motor quando roda na mesma máquina (LOG_PATH). Na nuvem esta
   página dá lugar à tabela de eventos (Fase do painel de controle). */
export default async function Logs({ searchParams }:
  { searchParams: Promise<{ q?: string }> }) {
  const { q } = await searchParams;
  const caminho = process.env.LOG_PATH;
  let linhas: string[] = [];
  if (caminho) {
    try {
      const bruto = await readFile(path.resolve(process.cwd(), caminho), "utf-8");
      linhas = bruto.split("\n")
        .map((l) => l.replace(/\x1b\[[0-9;]*m/g, ""))          // sem cores ANSI
        .filter((l) => l.trim())
        .filter((l) => !q || l.toLowerCase().includes(q.toLowerCase()))
        .slice(-300).reverse();
    } catch { /* arquivo indisponível */ }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Logs do motor</h1>
          <p className="mt-1 text-sm text-tinta2">últimas {linhas.length} linhas · mais recentes primeiro</p>
        </div>
        <form action="/logs">
          <input name="q" defaultValue={q ?? ""} placeholder="filtrar (ex.: clonado, enviada, ✗)…"
            className="w-72 rounded-lg border border-linha bg-carta2 px-3 py-1.5 text-sm outline-none focus:border-acento" />
        </form>
      </div>

      {!caminho ? (
        <div className="mt-8 rounded-xl border border-linha bg-carta p-6 text-sm text-tinta2">
          <p className="font-medium text-alerta">LOG_PATH não configurado.</p>
          <p className="mt-2">Localmente, aponte para <code className="text-tinta">dados/agente.log</code>.
          Na nuvem, esta página passa a ler a tabela de eventos.</p>
        </div>
      ) : (
        <pre className="mt-5 max-h-[70vh] overflow-auto rounded-xl border border-linha bg-carta p-4 text-xs leading-relaxed">
          {linhas.map((l, i) => (
            <div key={i} className={
              l.includes("✗") ? "text-erro" :
              l.includes("!") && !l.includes("✓") ? "text-alerta" :
              l.includes("✓") ? "text-ok" : "text-tinta2"}>{l}</div>
          ))}
        </pre>
      )}
    </div>
  );
}
