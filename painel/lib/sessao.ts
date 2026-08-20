/**
 * Sessão mínima do MVP: cookie httpOnly assinado com HMAC-SHA256 (Web Crypto,
 * roda no Edge middleware). Um usuário, credencial no ambiente.
 * Na fase SaaS isto é substituído por Auth.js + tabela de usuários — decisão
 * registrada no blueprint (ADR auth).
 */
const NOME_COOKIE = "afilify_sessao";
const DIAS = 7;

function b64url(buf: ArrayBuffer | Uint8Array): string {
  const b = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = "";
  for (const x of b) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function chave(segredo: string) {
  return crypto.subtle.importKey(
    "raw", new TextEncoder().encode(segredo),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"],
  );
}

export async function criarToken(email: string, segredo: string): Promise<string> {
  const corpo = b64url(new TextEncoder().encode(
    JSON.stringify({ e: email, x: Date.now() + DIAS * 864e5 })));
  const ass = await crypto.subtle.sign("HMAC", await chave(segredo),
    new TextEncoder().encode(corpo));
  return `${corpo}.${b64url(ass)}`;
}

export async function verificarToken(token: string | undefined, segredo: string) {
  if (!token || !token.includes(".")) return null;
  const [corpo, ass] = token.split(".");
  const esperado = await crypto.subtle.sign("HMAC", await chave(segredo),
    new TextEncoder().encode(corpo));
  if (b64url(esperado) !== ass) return null;
  try {
    const dados = JSON.parse(atob(corpo.replace(/-/g, "+").replace(/_/g, "/")));
    return dados.x > Date.now() ? { email: dados.e as string } : null;
  } catch { return null; }
}

export const SESSAO = { NOME_COOKIE, DIAS };
