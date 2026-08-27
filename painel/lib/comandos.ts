/**
 * COMANDOS — o pedido que o painel faz ao motor.
 *
 * Painel e motor são serviços separados que só compartilham o banco. Este é
 * o caminho entre os dois: o painel deixa o pedido, o motor pega e devolve
 * o resultado no mesmo registro.
 *
 * A tela sempre precisa de saída: se o motor está parado, o pedido expira e
 * o usuário lê isso — em vez de esperar para sempre.
 */
import "server-only";
import { randomUUID } from "node:crypto";
import { uma, executar } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";

/** Curto de propósito: é a espera de alguém olhando para a tela. */
const VALIDADE_SEG = 180;

export type EstadoComando = "pendente" | "executando" | "concluido" | "falhou" | "expirado" | "desconhecido";

export async function criarComando(tipo: string, parametros: unknown): Promise<{ id: string }> {
  const id = randomUUID();
  const agora = new Date();
  await executar(
    `INSERT INTO comandos (id, workspace_id, tipo, parametros, estado, resultado, erro,
       expira_em, criado_em, atualizado_em)
     VALUES (?, ?, ?, ?, 'pendente', '{}', '', ?, ?, ?)`,
    [
      id,
      WORKSPACE,
      tipo,
      JSON.stringify(parametros ?? {}),
      new Date(agora.getTime() + VALIDADE_SEG * 1000).toISOString(),
      agora.toISOString(),
      agora.toISOString(),
    ],
  );
  return { id };
}

export async function consultarComando(id: string): Promise<{
  estado: EstadoComando;
  resultado: Record<string, unknown>;
  erro: string;
}> {
  // Expira os vencidos antes de responder: um pedido que ficou para trás
  // não pode aparecer como "ainda processando" indefinidamente.
  const agora = new Date().toISOString();
  await executar(
    "UPDATE comandos SET estado = 'expirado', atualizado_em = ? WHERE estado IN ('pendente','executando') AND expira_em < ?",
    [agora, agora],
  ).catch(() => 0);

  const l = await uma("SELECT estado, resultado, erro FROM comandos WHERE id = ? AND workspace_id = ?", [
    id,
    WORKSPACE,
  ]);
  if (!l) return { estado: "desconhecido", resultado: {}, erro: "" };
  let resultado: Record<string, unknown> = {};
  try {
    resultado = JSON.parse(String(l.resultado ?? "{}")) as Record<string, unknown>;
  } catch {
    /* resultado ilegível não pode derrubar a tela */
  }
  return {
    estado: String(l.estado) as EstadoComando,
    resultado,
    erro: String(l.erro ?? ""),
  };
}
