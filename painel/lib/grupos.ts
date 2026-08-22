/**
 * Grupos de WhatsApp — tipos e exibição, PUROS (client-safe).
 * O identificador técnico do grupo nunca é primário na UI: use
 * nomeDoGrupo/mascararGrupo; o id inteiro só em "Detalhes técnicos".
 */

export type Grupo = { jid: string; nome: string };

/** "1203…8302@g.us" → "Grupo …8302" (id interno nunca aparece inteiro). */
export function mascararGrupo(jid: string): string {
  const base = jid.split("@")[0] ?? "";
  return base ? `Grupo …${base.slice(-4)}` : "Grupo sem nome";
}

/** Nome de exibição de um grupo; cai no identificador mascarado. */
export function nomeDoGrupo(jid: string, grupos: Grupo[]): string {
  const g = grupos.find((x) => x.jid === jid);
  return g?.nome || mascararGrupo(jid);
}
