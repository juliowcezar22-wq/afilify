"use client";
/**
 * Gravação de config a partir de Client Components — UM caminho para os
 * cinco formulários. Nunca lança: rede fora do ar ou resposta não-JSON
 * viram { ok: false } com mensagem legível.
 */

export type Aviso = { tom: "ok" | "erro"; texto: string };

export async function salvarConfig(
  perfil: string,
  chave: string,
  valor: unknown,
): Promise<{ ok: boolean; erro?: string }> {
  try {
    const r = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, chave, valor }),
    });
    if (r.ok) return { ok: true };
    const corpo = await r.json().catch(() => ({}));
    return { ok: false, erro: String(corpo.erro ?? "não foi possível salvar") };
  } catch {
    return { ok: false, erro: "sem conexão com o painel — tente novamente" };
  }
}
