/**
 * Contexto de projeto no servidor: lista de projetos (distinct perfil da
 * config) + projeto ativo do cookie. Usado pelo shell e pelas páginas que
 * filtram por projeto.
 */
import "server-only";
import { cache } from "react";
import { cookies } from "next/headers";
import { todas } from "@/lib/dados";
import { COOKIE_PROJETO, comoProjetos, projetoAtivo, type Projeto } from "@/lib/projetos";

export type ContextoProjeto = {
  projetos: Projeto[];
  /** Projeto selecionado, ou null = todos. */
  ativo: Projeto | null;
};

/** Memoizado por request (React cache): layout e página compartilham. */
export const contextoProjeto = cache(async (): Promise<ContextoProjeto> => {
  const [linhas, jar] = await Promise.all([
    todas("SELECT DISTINCT perfil FROM config ORDER BY perfil").catch(() => []),
    cookies(),
  ]);
  const projetos = comoProjetos(linhas.map((l) => l.perfil));
  const ativo = projetoAtivo(jar.get(COOKIE_PROJETO)?.value, projetos);
  return { projetos, ativo };
});

/** Condição SQL de projeto ("AND perfil = ?") respeitando o contexto. */
export function condicaoProjeto(ctx: ContextoProjeto, coluna = "perfil") {
  if (!ctx.ativo) return { sql: "", params: [] as unknown[] };
  return { sql: ` AND ${coluna} = ?`, params: [ctx.ativo.slug] };
}
