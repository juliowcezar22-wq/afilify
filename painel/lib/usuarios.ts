/**
 * USUÁRIOS — contas de quem opera a plataforma.
 *
 * Substitui a credencial única de ambiente. Nesta fase há um usuário só,
 * mas ele já vive no banco, ligado a um workspace — abrir para uma equipe
 * depois vira tela de convite, não migração de dados.
 *
 * Senha nunca é guardada: guarda-se a derivação (scrypt) com sal próprio.
 */
import "server-only";
import { randomBytes, randomUUID, scryptSync, timingSafeEqual } from "node:crypto";
import { todas, uma, executar } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";

export type Usuario = { id: string; email: string; nome: string; workspaceId: string };

/** `sal:hash` — o sal viaja junto para a verificação não precisar de tabela extra. */
export function derivar(senha: string, sal?: string): string {
  const usado = sal ?? randomBytes(16).toString("hex");
  return `${usado}:${scryptSync(senha, usado, 32).toString("hex")}`;
}

export function conferir(senha: string, guardado: string): boolean {
  const [sal, hex] = String(guardado).split(":");
  if (!sal || !hex || hex.length !== 64) return false;
  // Comparação de tempo constante: comparar com === deixaria o tempo de
  // resposta contar quantos caracteres bateram.
  return timingSafeEqual(scryptSync(senha, sal, 32), Buffer.from(hex, "hex"));
}

export async function existeAlgum(): Promise<boolean> {
  const l = await uma("SELECT id FROM usuarios LIMIT 1").catch(() => null);
  return Boolean(l);
}

export async function porEmail(email: string): Promise<(Usuario & { hash: string }) | null> {
  const l = await uma("SELECT * FROM usuarios WHERE email = ?", [email.trim().toLowerCase()]).catch(
    () => null,
  );
  if (!l) return null;
  return {
    id: String(l.id),
    email: String(l.email),
    nome: String(l.nome ?? ""),
    workspaceId: String(l.workspace_id),
    hash: String(l.senha_hash),
  };
}

export async function criar(email: string, senha: string, nome = ""): Promise<Usuario> {
  const id = randomUUID();
  const ts = new Date().toISOString();
  await executar(
    "INSERT INTO usuarios (id, workspace_id, email, senha_hash, nome, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
    [id, WORKSPACE, email.trim().toLowerCase(), derivar(senha), nome, ts],
  );
  return { id, email, nome, workspaceId: WORKSPACE };
}

export async function registrarAcesso(id: string): Promise<void> {
  await executar("UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?", [
    new Date().toISOString(),
    id,
  ]).catch(() => 0);
}

export async function listar(): Promise<Usuario[]> {
  const linhas = await todas("SELECT id, email, nome, workspace_id FROM usuarios ORDER BY criado_em").catch(
    () => [],
  );
  return linhas.map((l) => ({
    id: String(l.id),
    email: String(l.email),
    nome: String(l.nome ?? ""),
    workspaceId: String(l.workspace_id),
  }));
}
