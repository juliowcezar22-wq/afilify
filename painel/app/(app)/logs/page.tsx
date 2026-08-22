import { readFile } from "node:fs/promises";
import path from "node:path";
import { todas } from "@/lib/dados";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { CONTROLE } from "@/components/ui/campos";

export const dynamic = "force-dynamic";

const COR: Record<string, string> = {
  "✓": "text-ok",
  "✗": "text-erro",
  "!": "text-alerta",
};

/**
 * Página TÉCNICA (suporte/desenvolvimento) — fora da navegação comum do
 * produto; erros relevantes ao usuário aparecem contextualizados nas
 * próprias páginas (Publicações, Conexões, Fontes).
 * Fonte: tabela de registros do banco; sem linhas, cai no arquivo local
 * apontado pelo ambiente. // harness-ok
 */
export default async function Logs({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;

  let doBanco: Array<{ ts: string; nivel: string; texto: string }> = [];
  try {
    doBanco = (await todas(
      q
        ? `SELECT ts, nivel, texto FROM logs WHERE texto LIKE ? ORDER BY id DESC LIMIT 300`
        : `SELECT ts, nivel, texto FROM logs ORDER BY id DESC LIMIT 300`,
      q ? [`%${q}%`] : [],
    )) as never[];
  } catch {
    /* tabela ainda não migrada */
  }

  let doArquivo: string[] = [];
  if (doBanco.length === 0 && process.env.LOG_PATH) {
    try {
      const bruto = await readFile(path.resolve(process.cwd(), process.env.LOG_PATH), "utf-8");
      doArquivo = bruto
        .split("\n")
        .map((l) => l.replace(/\x1b\[[0-9;]*m/g, ""))
        .filter((l) => l.trim())
        .filter((l) => !q || l.toLowerCase().includes(q.toLowerCase()))
        .slice(-300)
        .reverse();
    } catch {
      /* arquivo indisponível */
    }
  }
  const total = doBanco.length || doArquivo.length;

  return (
    <div className="mx-auto max-w-5xl">
      <CabecalhoPagina
        titulo="Registro técnico"
        descricao="Página de suporte e desenvolvimento — as últimas linhas do registro da automação."
        acoes={
          <form action="/logs">
            <label htmlFor="filtro-logs" className="sr-only">
              Filtrar registro
            </label>
            <input
              id="filtro-logs"
              name="q"
              defaultValue={q ?? ""}
              placeholder="Filtrar…"
              className={`${CONTROLE} w-56 md:w-72`}
            />
          </form>
        }
      />
      <p className="mt-2 rounded-lg border border-alerta/30 bg-alerta/10 px-3 py-2 text-xs text-alerta">
        Conteúdo técnico, no formato bruto da automação. Problemas que pedem a
        sua ação aparecem traduzidos nas páginas do produto.
      </p>

      {total === 0 ? (
        <div className="mt-6">
          <EstadoVazio
            titulo={q ? "Nada encontrado com esse filtro" : "Nenhum registro ainda"}
            descricao={
              q
                ? "Tente outro termo."
                : "Os registros aparecem aqui a partir da primeira execução da automação."
            }
          />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border border-linha bg-carta">
          <table className="w-full text-sm">
            <tbody>
              {doBanco.map((l, i) => (
                <tr key={i} className="border-b border-linha/50 last:border-0">
                  <td className="whitespace-nowrap px-4 py-1.5 font-mono text-xs text-tinta2">
                    {String(l.ts).slice(5, 16).replace("T", " ")}
                  </td>
                  <td className={`px-2 py-1.5 font-mono ${COR[l.nivel] ?? "text-tinta2"}`}>
                    {l.nivel}
                  </td>
                  <td className="px-2 py-1.5">{l.texto}</td>
                </tr>
              ))}
              {doArquivo.map((l, i) => (
                <tr key={i} className="border-b border-linha/50 last:border-0">
                  <td className="px-4 py-1.5 font-mono text-xs" colSpan={3}>
                    {l}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
