/**
 * DESEMPENHO — o que aconteceu ao longo do tempo.
 *
 * Responde perguntas que o Dashboard não responde: o volume está subindo ou
 * caindo? em que horários publicamos mais? quais marcas rendem?
 *
 * De propósito NÃO repete os números do Dashboard: dois lugares mostrando o
 * mesmo número acabam divergindo, e aí nenhum dos dois merece confiança.
 */
import "server-only";
import { todas, uma } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";

export type PorDia = { dia: string; publicacoes: number; busca: number; monitoramento: number };
export type PorHora = { hora: string; publicacoes: number };
export type PorMarca = { marca: string; publicacoes: number; descontoMedio: number };

function corte(dias: number): string {
  return new Date(Date.now() - dias * 86_400_000)
    .toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
}

export async function porDia(projetoId: string, dias = 14): Promise<PorDia[]> {
  const linhas = await todas(
    `SELECT substr(p.enviada_em, 1, 10) AS dia,
            COUNT(*) AS n,
            SUM(CASE WHEN o.origem = 'monitoramento' THEN 1 ELSE 0 END) AS clones
       FROM publicacoes p JOIN ofertas_projeto o ON o.id = p.oferta_id
      WHERE p.workspace_id = ? AND p.projeto_id = ? AND p.estado = 'enviada'
        AND p.enviada_em >= ?
      GROUP BY dia ORDER BY dia DESC`,
    [WORKSPACE, projetoId, corte(dias)],
  ).catch(() => []);
  return linhas.map((l) => {
    const total = Number(l.n ?? 0);
    const clones = Number(l.clones ?? 0);
    return { dia: String(l.dia), publicacoes: total, busca: total - clones, monitoramento: clones };
  });
}

export async function porHora(projetoId: string, dias = 14): Promise<PorHora[]> {
  const linhas = await todas(
    `SELECT substr(enviada_em, 12, 2) AS hora, COUNT(*) AS n
       FROM publicacoes WHERE workspace_id = ? AND projeto_id = ? AND estado = 'enviada'
        AND enviada_em >= ? GROUP BY hora ORDER BY hora`,
    [WORKSPACE, projetoId, corte(dias)],
  ).catch(() => []);
  return linhas.map((l) => ({ hora: `${l.hora}h`, publicacoes: Number(l.n ?? 0) }));
}

export async function porMarca(projetoId: string, dias = 14, limite = 10): Promise<PorMarca[]> {
  const linhas = await todas(
    `SELECT o.marca, COUNT(*) AS n, AVG(o.desconto_pct) AS desconto
       FROM publicacoes p JOIN ofertas_projeto o ON o.id = p.oferta_id
      WHERE p.workspace_id = ? AND p.projeto_id = ? AND p.estado = 'enviada'
        AND p.enviada_em >= ? AND o.marca <> ''
      GROUP BY o.marca ORDER BY n DESC LIMIT ${Number(limite)}`,
    [WORKSPACE, projetoId, corte(dias)],
  ).catch(() => []);
  return linhas.map((l) => ({
    marca: String(l.marca),
    publicacoes: Number(l.n ?? 0),
    descontoMedio: Math.round(Number(l.desconto ?? 0)),
  }));
}

/**
 * Taxa de aproveitamento: do que foi encontrado, quanto virou publicação.
 *
 * Zero encontradas devolve null, não 0% — "0%" sugere que a busca trabalhou
 * e nada prestou, quando na verdade ela não trabalhou.
 */
export async function aproveitamento(projetoId: string, dias = 14): Promise<number | null> {
  const encontradas = Number(
    (await uma(
      "SELECT COUNT(*) AS n FROM ofertas_projeto WHERE workspace_id = ? AND projeto_id = ? AND criado_em >= ?",
      [WORKSPACE, projetoId, corte(dias)],
    ).catch(() => null))?.n ?? 0,
  );
  if (!encontradas) return null;
  const publicadas = Number(
    (await uma(
      "SELECT COUNT(DISTINCT oferta_id) AS n FROM publicacoes WHERE workspace_id = ? AND projeto_id = ? AND estado = 'enviada' AND enviada_em >= ?",
      [WORKSPACE, projetoId, corte(dias)],
    ).catch(() => null))?.n ?? 0,
  );
  return Math.round((publicadas / encontradas) * 100);
}
