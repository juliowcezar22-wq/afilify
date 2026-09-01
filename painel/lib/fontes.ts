/**
 * FONTES — de onde as ofertas vêm.
 *
 * O fluxo comum tem quatro campos, e só. Paginação, pausas, tentativas,
 * categoria e cabeçalhos não aparecem aqui nem no contrato: a proibição de
 * expor parâmetro técnico vale na borda, não só na tela.
 */
import "server-only";
import { randomUUID } from "node:crypto";
import { todas, uma, executar } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";
import { ErroDeAcao } from "@/lib/conexoes-servico";

export type Criterios = {
  palavras_chave: string[];
  onde: { busca: boolean; pagina_ofertas: boolean };
  desconto_minimo: number;
  preco: { min: number | null; max: number | null };
  excluir: { palavras: string[]; marcas: string[] };
};

export type Fonte = {
  id: string;
  automacaoId: string;
  tipo: "busca" | "monitoramento";
  ativa: boolean;
  criterios: Criterios;
  agenda: { horarios: number[] };
  ultimaExecucao: string | null;
};

const CAMPOS = ["palavras_chave", "onde", "desconto_minimo", "preco", "excluir"];
const MAX_PALAVRAS = 30;

export const CRITERIOS_VAZIOS: Criterios = {
  palavras_chave: [],
  onde: { busca: true, pagina_ofertas: true },
  desconto_minimo: 20,
  preco: { min: null, max: null },
  excluir: { palavras: [], marcas: [] },
};

/**
 * Valida o que chega da tela. Campo desconhecido é recusado — é assim que
 * um parâmetro técnico nunca entra por engano, mesmo que alguém o mande
 * direto pela API.
 */
export function validarCriterios(bruto: unknown): Criterios {
  if (!bruto || typeof bruto !== "object")
    throw new ErroDeAcao("criterios_invalidos", "Não entendi a configuração desta fonte.");
  const d = bruto as Record<string, unknown>;

  for (const chave of Object.keys(d))
    if (!CAMPOS.includes(chave))
      throw new ErroDeAcao(
        "campo_desconhecido",
        "Esta fonte recebeu uma configuração que a Afilify não reconhece.",
      );

  const palavras = Array.isArray(d.palavras_chave)
    ? (d.palavras_chave as unknown[]).filter((p): p is string => typeof p === "string" && p.trim() !== "")
        .map((p) => p.trim())
    : [];
  if (palavras.length === 0)
    throw new ErroDeAcao(
      "sem_palavras",
      "Escreva ao menos uma palavra-chave do que você quer encontrar.",
    );
  if (palavras.length > MAX_PALAVRAS)
    throw new ErroDeAcao(
      "palavras_demais",
      `São muitas palavras-chave (máximo ${MAX_PALAVRAS}). Menos termos, mais específicos, encontram melhor.`,
    );

  const ondeBruto = (d.onde ?? {}) as Record<string, unknown>;
  const onde = {
    busca: Boolean(ondeBruto.busca),
    pagina_ofertas: Boolean(ondeBruto.pagina_ofertas),
  };
  if (!onde.busca && !onde.pagina_ofertas)
    throw new ErroDeAcao("sem_lugar", "Escolha ao menos um lugar para buscar.");

  const desconto = Number(d.desconto_minimo ?? 0);
  if (!Number.isFinite(desconto) || desconto < 0 || desconto > 99)
    throw new ErroDeAcao("desconto_invalido", "O desconto mínimo precisa ser um número entre 0 e 99.");

  const precoBruto = (d.preco ?? {}) as Record<string, unknown>;
  const num = (v: unknown) => (v === null || v === undefined || v === "" ? null : Number(v));
  const min = num(precoBruto.min);
  const max = num(precoBruto.max);
  for (const v of [min, max])
    if (v !== null && (!Number.isFinite(v) || v < 0))
      throw new ErroDeAcao("preco_invalido", "A faixa de preço precisa ter valores positivos.");
  if (min !== null && max !== null && min > max)
    throw new ErroDeAcao("faixa_invertida", "O preço mínimo ficou maior que o máximo.");

  const excluirBruto = (d.excluir ?? {}) as Record<string, unknown>;
  const lista = (v: unknown) =>
    Array.isArray(v)
      ? (v as unknown[]).filter((x): x is string => typeof x === "string" && x.trim() !== "").map((x) => x.trim())
      : [];

  return {
    palavras_chave: palavras,
    onde,
    desconto_minimo: Math.round(desconto),
    preco: { min, max },
    excluir: { palavras: lista(excluirBruto.palavras), marcas: lista(excluirBruto.marcas) },
  };
}

function comoFonte(l: Record<string, unknown>): Fonte {
  const ler = <T,>(v: unknown, padrao: T): T => {
    try {
      return JSON.parse(String(v ?? "")) as T;
    } catch {
      return padrao;
    }
  };
  return {
    id: String(l.id),
    automacaoId: String(l.automacao_id),
    tipo: String(l.tipo) as "busca" | "monitoramento",
    ativa: Number(l.ativa) === 1,
    criterios: ler(l.criterios, CRITERIOS_VAZIOS),
    agenda: ler(l.agenda, { horarios: [7, 15] }),
    ultimaExecucao: l.ultima_execucao_em ? String(l.ultima_execucao_em) : null,
  };
}

export async function listar(automacaoId: string): Promise<Fonte[]> {
  const linhas = await todas(
    "SELECT * FROM fontes WHERE workspace_id = ? AND automacao_id = ? ORDER BY criado_em",
    [WORKSPACE, automacaoId],
  );
  return linhas.map(comoFonte);
}

export async function obter(id: string): Promise<Fonte | null> {
  const l = await uma("SELECT * FROM fontes WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
  return l ? comoFonte(l) : null;
}

export async function criar(
  automacaoId: string,
  criterios: Criterios,
  agenda: { horarios: number[] },
): Promise<Fonte> {
  const id = randomUUID();
  const ts = new Date().toISOString();
  await executar(
    `INSERT INTO fontes (id, workspace_id, automacao_id, tipo, ativa, criterios, agenda,
       criado_em, atualizado_em)
     VALUES (?, ?, ?, 'busca', 0, ?, ?, ?, ?)`,
    [id, WORKSPACE, automacaoId, JSON.stringify(criterios), JSON.stringify(agenda), ts, ts],
  );
  return (await obter(id))!;
}

export async function atualizar(
  id: string,
  campos: { criterios?: Criterios; agenda?: { horarios: number[] }; ativa?: boolean },
): Promise<void> {
  const sets = ["atualizado_em = ?"];
  const params: unknown[] = [new Date().toISOString()];
  if (campos.criterios) {
    sets.push("criterios = ?");
    params.push(JSON.stringify(campos.criterios));
  }
  if (campos.agenda) {
    sets.push("agenda = ?");
    params.push(JSON.stringify(campos.agenda));
  }
  if (campos.ativa !== undefined) {
    sets.push("ativa = ?");
    params.push(campos.ativa ? 1 : 0);
  }
  params.push(id, WORKSPACE);
  await executar(`UPDATE fontes SET ${sets.join(", ")} WHERE id = ? AND workspace_id = ?`, params);
}

export async function remover(id: string): Promise<void> {
  await executar("DELETE FROM fontes WHERE id = ? AND workspace_id = ?", [id, WORKSPACE]);
}

/** Últimas coletas — é como o usuário vê que a fonte rodou, mesmo sem novidade. */
export async function execucoes(fonteId: string, limite = 5) {
  const linhas = await todas(
    `SELECT iniciada_em, terminada_em, resultado, encontradas, novas, motivo
       FROM execucoes_fonte WHERE fonte_id = ? ORDER BY iniciada_em DESC LIMIT ${Number(limite)}`,
    [fonteId],
  );
  return linhas.map((l) => ({
    quando: String(l.iniciada_em),
    resultado: String(l.resultado),
    encontradas: Number(l.encontradas ?? 0),
    novas: Number(l.novas ?? 0),
    motivo: String(l.motivo ?? ""),
  }));
}

/** Testes de busca gastam o mesmo que uma coleta — por isso entram no limite. */
export async function podeTestar(): Promise<{ pode: boolean; limite: number; usados: number }> {
  const l = await uma("SELECT max_testes_busca_dia FROM limites_plano WHERE workspace_id = ?", [WORKSPACE]);
  const limite = Number(l?.max_testes_busca_dia ?? 50);
  const hoje = new Date().toISOString().slice(0, 10);
  const c = await uma(
    "SELECT COUNT(*) AS n FROM comandos WHERE workspace_id = ? AND tipo = 'testar_busca' AND criado_em LIKE ?",
    [WORKSPACE, `${hoje}%`],
  );
  const usados = Number(c?.n ?? 0);
  return { pode: usados < limite, limite, usados };
}
