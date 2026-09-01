/**
 * Projetos — tradução slug interno ↔ nome de produto e contexto ativo.
 * Puro (sem server-only) para uso em qualquer componente; a leitura do
 * cookie/banco fica em quem chama (shell, páginas).
 *
 * "Projeto" na UI = "perfil" do motor (D2 em AFILIFY_DECISIONS.md).
 */

export const COOKIE_PROJETO = "afilify_projeto";

/** Nomes amigáveis dos projetos conhecidos. Novos slugs caem na humanização. */
const NOMES: Record<string, string> = {
  "perfumes-ml": "Perfumes", // harness-ok (mapa interno slug→nome, nunca exibido)
  "casa-ml-shopee": "Casa", // harness-ok
};

/** Sufixos de marketplace que não pertencem ao nome do projeto. */
const MARCADORES = new Set(["ml", "shopee", "amazon", "magalu", "shein", "tiktok"]);

export function nomeDoProjeto(slug: unknown): string {
  const s = String(slug ?? "").trim();
  if (!s) return "—";
  if (NOMES[s]) return NOMES[s];
  const partes = s.split(/[-_]+/).filter((p) => p && !MARCADORES.has(p.toLowerCase()));
  if (partes.length === 0) return s;
  return partes
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase())
    .join(" ");
}

export type Projeto = { slug: string; nome: string };

export function comoProjetos(slugs: unknown[]): Projeto[] {
  return [...new Set(slugs.map((s) => String(s ?? "")).filter(Boolean))]
    .sort()
    .map((slug) => ({ slug, nome: nomeDoProjeto(slug) }));
}

/** Projeto ativo a partir do valor do cookie ("" = todos os projetos). */
export function projetoAtivo(valorCookie: string | undefined, projetos: Projeto[]): Projeto | null {
  if (!valorCookie) return null;
  return projetos.find((p) => p.slug === valorCookie) ?? null;
}
