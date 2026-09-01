/**
 * CONEXÕES — contas externas do workspace, persistidas.
 *
 * Aqui mora a diferença entre o que a plataforma de mensagens sabe (quatro
 * estados) e o que o usuário precisa saber (doze): o código venceu? a sessão
 * caiu sozinha ou fui eu que desconectei? estou tentando reconectar?
 *
 * Credencial entra cifrada e sai só para o servidor usar — nunca é devolvida
 * por nenhuma rota, nem mascarada.
 */
import "server-only";
import { randomUUID } from "node:crypto";
import { todas, uma, executar } from "@/lib/dados";
import { cifrar, decifrar } from "@/lib/cripto";
import type { EstadoConexao } from "@/lib/mensageria";

export const WORKSPACE = process.env.WORKSPACE_ID || "ws-afilify";

export type Plataforma = "whatsapp" | "mercadolivre" | "shopee";

export type Conexao = {
  id: string;
  plataforma: Plataforma;
  nome: string;
  estado: EstadoConexao;
  identificadorExterno: string;
  metadados: Metadados;
  ultimoEstadoEm: string;
  ultimaAtividadeEm: string | null;
  expiraEm: string | null;
  motivoUltimaQueda: string;
  criadoEm: string;
};

export type Metadados = {
  perfil?: string;
  numeroMascarado?: string;
  foto?: string;
  /** Quando o código de pareamento atual perde a validade. */
  codigoExpiraEm?: string;
  tipoCodigo?: "qr" | "pareamento";
  /** Tag de afiliado, para Mercado Livre. */
  tag?: string;
  /**
   * A Afilify criou esta conta, ou apenas adotou uma que já existia?
   * Define se remover a conexão pode destruir a conta lá fora — adotada,
   * nunca: ela é do usuário e existia antes de nós.
   */
  provisionadaPelaAfilify?: boolean;
  gruposSincronizadosEm?: string;
};

const agora = () => new Date().toISOString();

function comoConexao(l: Record<string, unknown>): Conexao {
  let metadados: Metadados = {};
  try {
    metadados = JSON.parse(String(l.metadados ?? "{}")) as Metadados;
  } catch {
    /* metadados corrompidos não podem derrubar a listagem */
  }
  return {
    id: String(l.id),
    plataforma: String(l.plataforma) as Plataforma,
    nome: String(l.nome ?? ""),
    estado: String(l.estado) as EstadoConexao,
    identificadorExterno: String(l.identificador_externo ?? ""),
    metadados,
    ultimoEstadoEm: String(l.ultimo_estado_em ?? ""),
    ultimaAtividadeEm: l.ultima_atividade_em ? String(l.ultima_atividade_em) : null,
    expiraEm: l.expira_em ? String(l.expira_em) : null,
    motivoUltimaQueda: String(l.motivo_ultima_queda ?? ""),
    criadoEm: String(l.criado_em ?? ""),
  };
}

export async function listar(plataforma?: Plataforma): Promise<Conexao[]> {
  const cond = plataforma ? " AND plataforma = ?" : "";
  const params: unknown[] = plataforma ? [WORKSPACE, plataforma] : [WORKSPACE];
  const linhas = await todas(
    `SELECT * FROM conexoes WHERE workspace_id = ?${cond} ORDER BY criado_em`,
    params,
  );
  return linhas.map(comoConexao);
}

export async function obter(id: string): Promise<Conexao | null> {
  const l = await uma("SELECT * FROM conexoes WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
  return l ? comoConexao(l) : null;
}

/** A credencial em claro, só para uso do servidor. Nunca retorne isto numa resposta. */
export async function credencialDe(id: string): Promise<string> {
  const l = await uma(
    "SELECT credencial_cifrada FROM conexoes WHERE id = ? AND workspace_id = ?",
    [id, WORKSPACE],
  );
  const guardada = String(l?.credencial_cifrada ?? "");
  return guardada ? decifrar(guardada, id) : "";
}

export async function criar(dados: {
  plataforma: Plataforma;
  nome: string;
  credencial: string;
  identificadorExterno?: string;
  estado?: EstadoConexao;
  metadados?: Metadados;
}): Promise<Conexao> {
  const id = randomUUID();
  const ts = agora();
  await executar(
    `INSERT INTO conexoes (id, workspace_id, plataforma, nome, estado, identificador_externo,
       credencial_cifrada, metadados, ultimo_estado_em, motivo_ultima_queda, criado_em, atualizado_em)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)`,
    [
      id,
      WORKSPACE,
      dados.plataforma,
      dados.nome,
      dados.estado ?? "criando",
      dados.identificadorExterno ?? "",
      // o id é o contexto: credencial de uma conexão não abre no lugar de outra
      dados.credencial ? cifrar(dados.credencial, id) : "",
      JSON.stringify(dados.metadados ?? {}),
      ts,
      ts,
      ts,
    ],
  );
  const criada = await obter(id);
  if (!criada) throw new Error("conexão não encontrada logo após criar");
  return criada;
}

export async function definirEstado(
  id: string,
  estado: EstadoConexao,
  extras: { metadados?: Metadados; motivoQueda?: string; expiraEm?: string | null; atividade?: boolean } = {},
): Promise<void> {
  const ts = agora();
  const campos = ["estado = ?", "ultimo_estado_em = ?", "atualizado_em = ?"];
  const params: unknown[] = [estado, ts, ts];

  if (extras.metadados !== undefined) {
    const atual = await obter(id);
    campos.push("metadados = ?");
    params.push(JSON.stringify({ ...(atual?.metadados ?? {}), ...extras.metadados }));
  }
  if (extras.motivoQueda !== undefined) {
    campos.push("motivo_ultima_queda = ?");
    params.push(extras.motivoQueda);
  }
  if (extras.expiraEm !== undefined) {
    campos.push("expira_em = ?");
    params.push(extras.expiraEm);
  }
  if (extras.atividade) {
    campos.push("ultima_atividade_em = ?");
    params.push(ts);
  }
  params.push(id, WORKSPACE);
  await executar(
    `UPDATE conexoes SET ${campos.join(", ")} WHERE id = ? AND workspace_id = ?`,
    params,
  );
}

export async function renomear(id: string, nome: string): Promise<void> {
  await executar(
    "UPDATE conexoes SET nome = ?, atualizado_em = ? WHERE id = ? AND workspace_id = ?",
    [nome, agora(), id, WORKSPACE],
  );
}

export async function remover(id: string): Promise<void> {
  await executar("DELETE FROM grupos_conexao WHERE conexao_id = ?", [id]);
  await executar("DELETE FROM conexoes WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
}

/**
 * Automações que dependem desta conexão — como destino ou como fonte de
 * monitoramento. Remover uma conexão em uso pararia essas automações, então
 * o usuário precisa saber quais são antes de confirmar (FR-022).
 */
export async function automacoesQueDependem(id: string): Promise<Array<{ nome: string; projeto: string }>> {
  const linhas = await todas(
    `SELECT DISTINCT a.nome AS automacao, p.nome AS projeto
       FROM automacoes a
       JOIN projetos p ON p.id = a.projeto_id
       LEFT JOIN destinos d ON d.automacao_id = a.id
       LEFT JOIN fontes  f ON f.automacao_id = a.id
      WHERE a.workspace_id = ? AND a.estado = 'ativa'
        AND (d.conexao_id = ? OR f.conexao_id = ?)`,
    [WORKSPACE, id, id],
  ).catch(() => []);
  return linhas.map((l) => ({ nome: String(l.automacao), projeto: String(l.projeto) }));
}

/* ── grupos ─────────────────────────────────────────────────────────── */

export type Grupo = { identificador: string; nome: string; participantes: number };

export async function gruposDe(conexaoId: string): Promise<Grupo[]> {
  const linhas = await todas(
    "SELECT identificador, nome, participantes FROM grupos_conexao WHERE conexao_id = ? ORDER BY nome",
    [conexaoId],
  );
  return linhas.map((l) => ({
    identificador: String(l.identificador),
    nome: String(l.nome ?? ""),
    participantes: Number(l.participantes ?? 0),
  }));
}

/** Substitui o cache de grupos por inteiro — some da conta, some daqui. */
export async function guardarGrupos(conexaoId: string, grupos: Grupo[]): Promise<number> {
  const ts = agora();
  await executar("DELETE FROM grupos_conexao WHERE conexao_id = ?", [conexaoId]);
  for (const g of grupos) {
    await executar(
      `INSERT INTO grupos_conexao (conexao_id, identificador, nome, participantes, sincronizado_em)
       VALUES (?, ?, ?, ?, ?)`,
      [conexaoId, g.identificador, g.nome, g.participantes, ts],
    );
  }
  await definirEstado(conexaoId, (await obter(conexaoId))!.estado, {
    metadados: { gruposSincronizadosEm: ts },
  });
  return grupos.length;
}

/* ── limites de plano ───────────────────────────────────────────────── */

/**
 * O limite que importa é de conexões ATIVAS ao mesmo tempo — é assim que a
 * plataforma de mensagens cobra a vaga, e foi assim que aprendemos na
 * prática: contar conexões criadas recusaria o usuário cedo demais, com uma
 * conta desconectada ocupando um lugar que ela não ocupa de verdade.
 */
export async function podeAdicionarConexao(): Promise<{ pode: boolean; limite: number; ativas: number }> {
  const l = await uma("SELECT max_conexoes FROM limites_plano WHERE workspace_id = ?", [WORKSPACE]);
  const limite = Number(l?.max_conexoes ?? 5);
  const c = await uma(
    "SELECT COUNT(*) AS n FROM conexoes WHERE workspace_id = ? AND estado = 'conectado'",
    [WORKSPACE],
  );
  const ativas = Number(c?.n ?? 0);
  return { pode: ativas < limite, limite, ativas };
}
