/**
 * DESTINOS — para onde as publicações vão.
 *
 * Um destino é um grupo dentro de uma conexão. Nomes vêm do cache de grupos;
 * o identificador técnico existe, mas fica na área avançada.
 */
import "server-only";
import { randomUUID } from "node:crypto";
import { todas, uma, executar } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";
import { ErroDeAcao } from "@/lib/conexoes-servico";

export type Destino = {
  id: string;
  automacaoId: string;
  conexaoId: string;
  alvo: string;
  nome: string;
  ordem: number;
  ativo: boolean;
};

function comoDestino(l: Record<string, unknown>): Destino {
  return {
    id: String(l.id),
    automacaoId: String(l.automacao_id),
    conexaoId: String(l.conexao_id),
    alvo: String(l.alvo),
    nome: String(l.nome ?? ""),
    ordem: Number(l.ordem ?? 0),
    ativo: Number(l.ativo) === 1,
  };
}

export async function listar(automacaoId: string): Promise<Destino[]> {
  const linhas = await todas(
    "SELECT * FROM destinos WHERE workspace_id = ? AND automacao_id = ? ORDER BY ordem, criado_em",
    [WORKSPACE, automacaoId],
  );
  return linhas.map(comoDestino);
}

/**
 * Outras automações que já publicam neste mesmo grupo.
 *
 * Não bloqueia — pode ser exatamente o que o usuário quer. Mas ele precisa
 * saber, porque o volume no grupo dobra sem que nenhuma das automações
 * pareça ter mudado.
 */
export async function jaPublicamNoMesmoGrupo(
  alvo: string,
  exceto: string,
): Promise<string[]> {
  const linhas = await todas(
    `SELECT DISTINCT p.nome AS projeto, a.nome AS automacao
       FROM destinos d
       JOIN automacoes a ON a.id = d.automacao_id
       JOIN projetos p ON p.id = a.projeto_id
      WHERE d.workspace_id = ? AND d.alvo = ? AND d.automacao_id <> ? AND d.ativo = 1`,
    [WORKSPACE, alvo, exceto],
  ).catch(() => []);
  return linhas.map((l) => `${l.projeto} · ${l.automacao}`);
}

export async function adicionar(
  automacaoId: string,
  conexaoId: string,
  alvo: string,
  nome: string,
): Promise<{ destino: Destino; aviso?: string }> {
  if (!alvo) throw new ErroDeAcao("sem_alvo", "Escolha um grupo para publicar.");
  if (!conexaoId) throw new ErroDeAcao("sem_conexao", "Escolha de qual conta as mensagens saem.");

  const existente = await uma(
    "SELECT id FROM destinos WHERE automacao_id = ? AND alvo = ?",
    [automacaoId, alvo],
  );
  if (existente)
    throw new ErroDeAcao("destino_repetido", "Esta automação já publica nesse grupo.", 409);

  const outras = await jaPublicamNoMesmoGrupo(alvo, automacaoId);
  const ordem = (await listar(automacaoId)).length;
  const id = randomUUID();
  const ts = new Date().toISOString();
  await executar(
    `INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, ordem, ativo,
       criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)`,
    [id, WORKSPACE, automacaoId, conexaoId, alvo, nome, ordem, ts, ts],
  );
  const destino = comoDestino((await uma("SELECT * FROM destinos WHERE id = ?", [id]))!);
  return {
    destino,
    aviso:
      outras.length > 0
        ? outras.length === 1
          ? `"${outras[0]}" também publica neste grupo — o volume dele vai somar as duas.`
          : `${outras.length} outras automações também publicam neste grupo — o volume dele vai somar todas.`
        : undefined,
  };
}

export async function remover(id: string): Promise<void> {
  // Desativa em vez de apagar: as publicações já feitas apontam para ele, e
  // o histórico do grupo antigo precisa continuar existindo (FR-007).
  await executar(
    "UPDATE destinos SET ativo = 0, atualizado_em = ? WHERE id = ? AND workspace_id = ?",
    [new Date().toISOString(), id, WORKSPACE],
  );
}

export async function reordenar(ids: string[]): Promise<void> {
  const ts = new Date().toISOString();
  for (let i = 0; i < ids.length; i++)
    await executar(
      "UPDATE destinos SET ordem = ?, atualizado_em = ? WHERE id = ? AND workspace_id = ?",
      [i, ts, ids[i], WORKSPACE],
    );
}
