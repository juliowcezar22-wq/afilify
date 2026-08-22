/**
 * Conexão WhatsApp no servidor — lista de grupos da conta conectada.
 * Exibição (nome/máscara) mora em lib/grupos.ts, client-safe.
 */
import "server-only";
import type { Grupo } from "@/lib/grupos";

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
