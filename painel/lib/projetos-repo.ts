/**
 * PROJETOS E AUTOMAÇÕES — a espinha do produto, como dado.
 *
 * Um Projeto é uma operação ("Perfumes"). Uma Automação é como um processo
 * funciona dentro dele ("Ofertas Mercado Livre"), e é o que liga e desliga.
 *
 * Nomes aqui são do usuário, nunca slugs. O identificador é interno.
 */
import "server-only";
import { randomUUID } from "node:crypto";
import { todas, uma, executar } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";

export type EstadoProjeto = "ativo" | "pausado" | "arquivado";
export type EstadoAutomacao = "rascunho" | "ativa" | "pausada" | "impedida";

export type Projeto = {
  id: string;
  nome: string;
  tipoNicho: string;
  estado: EstadoProjeto;
  criadoEm: string;
};

export type Automacao = {
  id: string;
  projetoId: string;
  nome: string;
  estado: EstadoAutomacao;
  motivoImpedida: string;
  ritmo: Record<string, unknown>;
  mensagem: Record<string, unknown>;
};

const agora = () => new Date().toISOString();

function json(valor: unknown): Record<string, unknown> {
  try {
    const d = JSON.parse(String(valor ?? "{}"));
    return d && typeof d === "object" ? (d as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

/* ── projetos ───────────────────────────────────────────────────────── */

function comoProjeto(l: Record<string, unknown>): Projeto {
  return {
    id: String(l.id),
    nome: String(l.nome ?? ""),
    tipoNicho: String(l.tipo_nicho_id ?? ""),
    estado: String(l.estado) as EstadoProjeto,
    criadoEm: String(l.criado_em ?? ""),
  };
}

/** Projetos vivos. Arquivados ficam de fora — o histórico deles sobrevive. */
export async function listarProjetos(incluirArquivados = false): Promise<Projeto[]> {
  const cond = incluirArquivados ? "" : " AND estado <> 'arquivado'";
  const linhas = await todas(
    `SELECT * FROM projetos WHERE workspace_id = ?${cond} ORDER BY nome`,
    [WORKSPACE],
  );
  return linhas.map(comoProjeto);
}

export async function obterProjeto(id: string): Promise<Projeto | null> {
  const l = await uma("SELECT * FROM projetos WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
  return l ? comoProjeto(l) : null;
}

export async function criarProjeto(nome: string, tipoNicho: string): Promise<Projeto> {
  const id = randomUUID();
  const ts = agora();
  await executar(
    `INSERT INTO projetos (id, workspace_id, nome, tipo_nicho_id, estado, criado_em, atualizado_em)
     VALUES (?, ?, ?, ?, 'ativo', ?, ?)`,
    [id, WORKSPACE, nome, tipoNicho, ts, ts],
  );
  return (await obterProjeto(id))!;
}

export async function renomearProjeto(id: string, nome: string): Promise<void> {
  await executar(
    "UPDATE projetos SET nome = ?, atualizado_em = ? WHERE id = ? AND workspace_id = ?",
    [nome, agora(), id, WORKSPACE],
  );
}

export async function definirEstadoProjeto(id: string, estado: EstadoProjeto): Promise<void> {
  await executar(
    "UPDATE projetos SET estado = ?, atualizado_em = ? WHERE id = ? AND workspace_id = ?",
    [estado, agora(), id, WORKSPACE],
  );
}

/**
 * Arquivar, não apagar: ofertas e publicações do projeto continuam existindo
 * (FR-007). Um projeto que sumisse levaria embora o histórico que alimenta
 * desempenho e a regra de repetição.
 */
export async function arquivarProjeto(id: string): Promise<void> {
  await executar(
    "UPDATE automacoes SET estado = 'pausada', atualizado_em = ? WHERE projeto_id = ? AND workspace_id = ?",
    [agora(), id, WORKSPACE],
  );
  await definirEstadoProjeto(id, "arquivado");
}

export async function nomeDeProjetoEmUso(nome: string, exceto = ""): Promise<boolean> {
  const l = await uma(
    "SELECT id FROM projetos WHERE workspace_id = ? AND nome = ? AND id <> ?",
    [WORKSPACE, nome, exceto || "-"],
  );
  return Boolean(l);
}

/* ── automações ─────────────────────────────────────────────────────── */

function comoAutomacao(l: Record<string, unknown>): Automacao {
  return {
    id: String(l.id),
    projetoId: String(l.projeto_id),
    nome: String(l.nome ?? ""),
    estado: String(l.estado) as EstadoAutomacao,
    motivoImpedida: String(l.motivo_impedida ?? ""),
    ritmo: json(l.ritmo),
    mensagem: json(l.mensagem),
  };
}

export async function listarAutomacoes(projetoId?: string): Promise<Automacao[]> {
  const cond = projetoId ? " AND projeto_id = ?" : "";
  const params = projetoId ? [WORKSPACE, projetoId] : [WORKSPACE];
  const linhas = await todas(
    `SELECT * FROM automacoes WHERE workspace_id = ?${cond} ORDER BY criado_em`,
    params,
  );
  return linhas.map(comoAutomacao);
}

export async function obterAutomacao(id: string): Promise<Automacao | null> {
  const l = await uma("SELECT * FROM automacoes WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
  return l ? comoAutomacao(l) : null;
}

export async function criarAutomacao(projetoId: string, nome: string): Promise<Automacao> {
  const id = randomUUID();
  const ts = agora();
  await executar(
    `INSERT INTO automacoes (id, workspace_id, projeto_id, nome, estado, motivo_impedida,
       ritmo, mensagem, criado_em, atualizado_em)
     VALUES (?, ?, ?, ?, 'rascunho', '', '{}', '{}', ?, ?)`,
    [id, WORKSPACE, projetoId, nome, ts, ts],
  );
  return (await obterAutomacao(id))!;
}

export async function atualizarAutomacao(
  id: string,
  campos: { nome?: string; ritmo?: unknown; mensagem?: unknown },
): Promise<void> {
  const sets: string[] = ["atualizado_em = ?"];
  const params: unknown[] = [agora()];
  if (campos.nome !== undefined) {
    sets.push("nome = ?");
    params.push(campos.nome);
  }
  if (campos.ritmo !== undefined) {
    sets.push("ritmo = ?");
    params.push(JSON.stringify(campos.ritmo));
  }
  if (campos.mensagem !== undefined) {
    sets.push("mensagem = ?");
    params.push(JSON.stringify(campos.mensagem));
  }
  params.push(id, WORKSPACE);
  await executar(
    `UPDATE automacoes SET ${sets.join(", ")} WHERE id = ? AND workspace_id = ?`,
    params,
  );
}

export async function definirEstadoAutomacao(
  id: string,
  estado: EstadoAutomacao,
  motivo = "",
): Promise<void> {
  await executar(
    "UPDATE automacoes SET estado = ?, motivo_impedida = ?, atualizado_em = ? WHERE id = ? AND workspace_id = ?",
    [estado, motivo, agora(), id, WORKSPACE],
  );
}

export async function removerAutomacao(id: string): Promise<void> {
  await executar("DELETE FROM destinos WHERE automacao_id = ?", [id]);
  await executar("DELETE FROM fontes WHERE automacao_id = ?", [id]);
  await executar("DELETE FROM automacoes WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
}

/* ── limites ────────────────────────────────────────────────────────── */

export async function limite(campo: "max_projetos" | "max_automacoes"): Promise<number> {
  const l = await uma(`SELECT ${campo} AS v FROM limites_plano WHERE workspace_id = ?`, [WORKSPACE]);
  return Number(l?.v ?? (campo === "max_projetos" ? 10 : 20));
}

export async function contar(tabela: "projetos" | "automacoes"): Promise<number> {
  const cond = tabela === "projetos" ? " AND estado <> 'arquivado'" : "";
  const l = await uma(`SELECT COUNT(*) AS n FROM ${tabela} WHERE workspace_id = ?${cond}`, [WORKSPACE]);
  return Number(l?.n ?? 0);
}

/* ── tipos de nicho ─────────────────────────────────────────────────── */

export type TipoNicho = { id: string; nome: string };

export async function tiposDeNicho(): Promise<TipoNicho[]> {
  const linhas = await todas("SELECT id, nome FROM tipos_nicho ORDER BY nome");
  return linhas.map((l) => ({ id: String(l.id), nome: String(l.nome) }));
}
