/**
 * Cifra de credenciais — o mesmo formato que o motor usa (nucleo/cripto.py).
 *
 * Credencial de conta externa nunca fica em claro no banco, nunca volta ao
 * navegador, nunca entra em log. AES-256-GCM: além de esconder, detecta
 * adulteração.
 *
 * Formato: `v1.<nonce>.<texto+tag>` em base64url — idêntico ao do motor, para
 * que os dois lados leiam o que o outro gravou (decisão D37).
 */
import "server-only";
import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

const VERSAO = "v1";
const TAM_NONCE = 12;
const TAM_TAG = 16;

export class ErroCripto extends Error {}

function b64e(b: Buffer): string {
  return b.toString("base64url");
}

function b64d(s: string): Buffer {
  return Buffer.from(s, "base64url");
}

function chaveMestra(): Buffer {
  const bruta = (process.env.AFILIFY_CHAVE_MESTRA ?? "").trim();
  if (!bruta)
    throw new ErroCripto(
      "AFILIFY_CHAVE_MESTRA não configurada — sem ela a plataforma não pode guardar credenciais",
    );
  const chave = b64d(bruta);
  if (chave.length !== 32)
    throw new ErroCripto(`AFILIFY_CHAVE_MESTRA precisa ter 32 bytes (tem ${chave.length})`);
  return chave;
}

/** Dá para cifrar neste ambiente? Usado para degradar com aviso claro. */
export function cifraConfigurada(): boolean {
  try {
    chaveMestra();
    return true;
  } catch {
    return false;
  }
}

/**
 * Texto claro → `v1.<nonce>.<cifrado>`.
 * `contexto` entra como dado autenticado: credencial de uma conexão não abre
 * no lugar de outra, mesmo trocando as linhas de lugar no banco.
 */
export function cifrar(valor: string, contexto = ""): string {
  const nonce = randomBytes(TAM_NONCE);
  const cifra = createCipheriv("aes-256-gcm", chaveMestra(), nonce);
  if (contexto) cifra.setAAD(Buffer.from(contexto, "utf8"));
  const texto = Buffer.concat([cifra.update(valor, "utf8"), cifra.final()]);
  // O motor entrega texto+tag juntos; concatenamos para o formato bater.
  return `${VERSAO}.${b64e(nonce)}.${b64e(Buffer.concat([texto, cifra.getAuthTag()]))}`;
}

/** Inverso de cifrar(). Lança ErroCripto se o valor foi adulterado. */
export function decifrar(guardado: string, contexto = ""): string {
  if (!guardado) return "";
  const partes = guardado.split(".");
  if (partes.length !== 3 || partes[0] !== VERSAO)
    throw new ErroCripto("formato de credencial desconhecido");
  const nonce = b64d(partes[1]);
  const selado = b64d(partes[2]);
  if (selado.length <= TAM_TAG) throw new ErroCripto("credencial truncada");
  const texto = selado.subarray(0, selado.length - TAM_TAG);
  const tag = selado.subarray(selado.length - TAM_TAG);
  try {
    const decifra = createDecipheriv("aes-256-gcm", chaveMestra(), nonce);
    decifra.setAuthTag(tag);
    if (contexto) decifra.setAAD(Buffer.from(contexto, "utf8"));
    return Buffer.concat([decifra.update(texto), decifra.final()]).toString("utf8");
  } catch (e) {
    if (e instanceof ErroCripto) throw e;
    throw new ErroCripto("credencial não pôde ser lida — chave trocada ou valor adulterado");
  }
}

/** Para EXIBIR (nunca a credencial em si): "••••1234". */
export function mascarar(valor: string, visiveis = 4): string {
  if (!valor) return "";
  return "••••" + (valor.length > visiveis ? valor.slice(-visiveis) : "");
}
