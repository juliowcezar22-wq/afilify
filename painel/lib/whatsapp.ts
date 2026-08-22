/**
 * Conexão WhatsApp no servidor — lista de grupos e utilidades de exibição.
 * O identificador técnico do grupo (JID) nunca é primário na UI; use
 * nomeDoGrupo/mascararGrupo e deixe o id em "Detalhes técnicos".
 */
import "server-only";

export type Grupo = { jid: string; nome: string };

export function conexaoConfigurada(): boolean {
  return Boolean(process.env.UAZAPI_URL && process.env.UAZAPI_TOKEN);
}

/** Grupos da conta conectada; [] quando a conexão não responde. */
export async function gruposDaConta(): Promise<Grupo[]> {
  const url = process.env.UAZAPI_URL,
    token = process.env.UAZAPI_TOKEN;
  if (!url || !token) return [];
  try {
    const r = await fetch(`${url}/group/list`, {
      headers: { token },
      signal: AbortSignal.timeout(6000),
      cache: "no-store",
    });
    const d = await r.json();
    return (d.groups ?? []).map((g: Record<string, unknown>) => ({
      jid: String(g.JID ?? ""), // harness-ok (campo da API, não exibido)
      nome: String(g.Name ?? ""),
    }));
  } catch {
    return [];
  }
}

/** Nome de exibição de um grupo; cai no identificador mascarado. */
export function nomeDoGrupo(jid: string, grupos: Grupo[]): string {
  const g = grupos.find((x) => x.jid === jid);
  if (g?.nome) return g.nome;
  return mascararGrupo(jid);
}

/** "1203…8302@g.us" → "Grupo …8302" (id interno nunca aparece inteiro). */
export function mascararGrupo(jid: string): string {
  const base = jid.split("@")[0] ?? "";
  return base ? `Grupo …${base.slice(-4)}` : "Grupo sem nome";
}
