/**
 * As ações sobre projetos e automações.
 *
 * A regra que dá o tom deste arquivo: **uma automação nunca liga pela
 * metade**. Se falta destino, conexão ou fonte, ela não vira "ativa com um
 * problema" — ela recusa a ativação e diz exatamente o que falta, em
 * linguagem de gente.
 */
import "server-only";
import * as repo from "@/lib/projetos-repo";
import * as conexoes from "@/lib/conexoes";
import { todas, uma, executar } from "@/lib/dados";
import { ErroDeAcao } from "@/lib/conexoes-servico";

export { ErroDeAcao };

export type ProjetoExibivel = repo.Projeto & {
  automacoes: AutomacaoExibivel[];
  ofertasHoje: number;
};

export type AutomacaoExibivel = repo.Automacao & {
  destinos: number;
  fontes: number;
  pendencias: string[];
};

/**
 * O que falta para esta automação poder trabalhar.
 *
 * Devolve frases, não códigos: elas aparecem na tela do jeito que saem
 * daqui. Ordem importa — a primeira pendência é a que o usuário resolve
 * primeiro.
 */
export async function pendenciasDe(automacaoId: string): Promise<string[]> {
  const faltas: string[] = [];

  const fontes = await todas(
    "SELECT tipo, ativa, conexao_id FROM fontes WHERE automacao_id = ?",
    [automacaoId],
  );
  const destinos = await todas(
    "SELECT conexao_id FROM destinos WHERE automacao_id = ? AND ativo = 1",
    [automacaoId],
  );

  if (fontes.length === 0) faltas.push("escolher de onde vêm as ofertas");
  else if (!fontes.some((f) => Number(f.ativa) === 1))
    faltas.push("ligar ao menos uma fonte de ofertas");

  if (destinos.length === 0) faltas.push("escolher para onde publicar");

  // Uma conexão caída faz a automação parar sem avisar — melhor não deixar
  // ligar do que ligar e ficar em silêncio.
  const usadas = new Set(
    [...destinos, ...fontes].map((r) => String(r.conexao_id ?? "")).filter(Boolean),
  );
  for (const id of usadas) {
    const c = await conexoes.obter(id);
    if (!c) {
      faltas.push("reconectar a conta usada por esta automação");
      continue;
    }
    if (c.estado !== "conectado")
      faltas.push(`conectar "${c.nome}" — ela está desconectada`);
  }

  return faltas;
}

async function exibivelAutomacao(a: repo.Automacao): Promise<AutomacaoExibivel> {
  const [d, f] = await Promise.all([
    uma("SELECT COUNT(*) AS n FROM destinos WHERE automacao_id = ? AND ativo = 1", [a.id]),
    uma("SELECT COUNT(*) AS n FROM fontes WHERE automacao_id = ?", [a.id]),
  ]);
  return {
    ...a,
    destinos: Number(d?.n ?? 0),
    fontes: Number(f?.n ?? 0),
    pendencias: await pendenciasDe(a.id),
  };
}

export async function listar(): Promise<ProjetoExibivel[]> {
  const projetos = await repo.listarProjetos();
  return Promise.all(
    projetos.map(async (p) => {
      const automacoes = await repo.listarAutomacoes(p.id);
      const hoje = new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
      const n = await uma(
        "SELECT COUNT(*) AS n FROM ofertas_projeto WHERE projeto_id = ? AND criado_em LIKE ?",
        [p.id, `${hoje}%`],
      ).catch(() => null);
      return {
        ...p,
        automacoes: await Promise.all(automacoes.map(exibivelAutomacao)),
        ofertasHoje: Number(n?.n ?? 0),
      };
    }),
  );
}

export async function criarProjeto(nome: string, tipoNicho: string): Promise<repo.Projeto> {
  const limpo = nome.trim();
  if (!limpo) throw new ErroDeAcao("nome_obrigatorio", "Dê um nome ao projeto.");
  if (await repo.nomeDeProjetoEmUso(limpo))
    throw new ErroDeAcao("nome_em_uso", `Você já tem um projeto chamado "${limpo}".`, 409);
  if (!tipoNicho)
    throw new ErroDeAcao("nicho_obrigatorio", "Escolha o tipo de produto deste projeto.");

  const [max, atual] = await Promise.all([repo.limite("max_projetos"), repo.contar("projetos")]);
  if (atual >= max)
    throw new ErroDeAcao(
      "limite_do_plano",
      `Seu plano permite ${max} projetos. Arquive um antes de criar outro.`,
      429,
    );
  return repo.criarProjeto(limpo, tipoNicho);
}

export async function renomearProjeto(id: string, nome: string): Promise<void> {
  const limpo = nome.trim();
  if (!limpo) throw new ErroDeAcao("nome_obrigatorio", "Dê um nome ao projeto.");
  if (await repo.nomeDeProjetoEmUso(limpo, id))
    throw new ErroDeAcao("nome_em_uso", `Você já tem um projeto chamado "${limpo}".`, 409);
  await repo.renomearProjeto(id, limpo);
}

/**
 * Duplicar copia a receita, não o histórico: fontes, destinos, mensagem e
 * ritmo vêm junto; ofertas e publicações, não. E nasce pausada — ninguém
 * quer descobrir que uma cópia começou a publicar sozinha.
 */
export async function duplicarProjeto(id: string, nome: string): Promise<repo.Projeto> {
  const origem = await repo.obterProjeto(id);
  if (!origem) throw new ErroDeAcao("nao_encontrado", "Projeto não encontrado.", 404);

  const criado = await criarProjeto(nome || `${origem.nome} (cópia)`, origem.tipoNicho);
  await repo.definirEstadoProjeto(criado.id, "pausado");
  // Reler depois de pausar: devolver o objeto de antes faria a resposta
  // dizer "ativo" para um projeto que está pausado no banco — e a tela
  // mostraria um estado que não existe.
  const novo = (await repo.obterProjeto(criado.id))!;

  for (const a of await repo.listarAutomacoes(id)) {
    const copia = await repo.criarAutomacao(novo.id, a.nome);
    await repo.atualizarAutomacao(copia.id, { ritmo: a.ritmo, mensagem: a.mensagem });
    const ts = new Date().toISOString();
    for (const f of await todas(
      "SELECT tipo, conexao_id, criterios, agenda FROM fontes WHERE automacao_id = ?", [a.id])) {
      await executar(
        `INSERT INTO fontes (id, workspace_id, automacao_id, tipo, conexao_id, ativa,
           criterios, agenda, criado_em, atualizado_em)
         VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)`,
        [crypto.randomUUID(), conexoes.WORKSPACE, copia.id, f.tipo, f.conexao_id,
         f.criterios, f.agenda, ts, ts],
      );
    }
    for (const d of await todas(
      "SELECT conexao_id, alvo, nome, ordem FROM destinos WHERE automacao_id = ?", [a.id])) {
      await executar(
        `INSERT INTO destinos (id, workspace_id, automacao_id, conexao_id, alvo, nome, ordem,
           ativo, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)`,
        [crypto.randomUUID(), conexoes.WORKSPACE, copia.id, d.conexao_id, d.alvo, d.nome,
         d.ordem, ts, ts],
      );
    }
  }
  return novo;
}

export async function arquivarProjeto(id: string): Promise<void> {
  const p = await repo.obterProjeto(id);
  if (!p) throw new ErroDeAcao("nao_encontrado", "Projeto não encontrado.", 404);
  await repo.arquivarProjeto(id);
}

export async function criarAutomacao(projetoId: string, nome: string): Promise<repo.Automacao> {
  const p = await repo.obterProjeto(projetoId);
  if (!p) throw new ErroDeAcao("nao_encontrado", "Projeto não encontrado.", 404);
  const limpo = nome.trim();
  if (!limpo) throw new ErroDeAcao("nome_obrigatorio", "Dê um nome à automação.");

  const [max, atual] = await Promise.all([repo.limite("max_automacoes"), repo.contar("automacoes")]);
  if (atual >= max)
    throw new ErroDeAcao(
      "limite_do_plano",
      `Seu plano permite ${max} automações. Exclua uma antes de criar outra.`,
      429,
    );
  return repo.criarAutomacao(projetoId, limpo);
}

/** Liga a automação — ou recusa dizendo o que falta, sem ligar pela metade. */
export async function ativar(id: string): Promise<repo.Automacao> {
  const a = await repo.obterAutomacao(id);
  if (!a) throw new ErroDeAcao("nao_encontrada", "Automação não encontrada.", 404);

  const faltas = await pendenciasDe(id);
  if (faltas.length > 0) {
    await repo.definirEstadoAutomacao(id, "impedida", faltas[0]);
    throw new ErroDeAcao(
      "automacao_incompleta",
      faltas.length === 1
        ? `Antes de ligar, falta ${faltas[0]}.`
        : `Antes de ligar, faltam ${faltas.length} coisas.`,
      409,
      { pendencias: faltas },
    );
  }

  const projeto = await repo.obterProjeto(a.projetoId);
  if (projeto?.estado === "arquivado")
    throw new ErroDeAcao("projeto_arquivado", "Este projeto está arquivado.", 409);
  if (projeto?.estado === "pausado") await repo.definirEstadoProjeto(a.projetoId, "ativo");

  await repo.definirEstadoAutomacao(id, "ativa");
  return (await repo.obterAutomacao(id))!;
}

/** Pausa: nada novo sai, e o que já estava na fila é preservado. */
export async function pausar(id: string): Promise<repo.Automacao> {
  const a = await repo.obterAutomacao(id);
  if (!a) throw new ErroDeAcao("nao_encontrada", "Automação não encontrada.", 404);
  await repo.definirEstadoAutomacao(id, "pausada");
  return (await repo.obterAutomacao(id))!;
}

export async function removerAutomacao(id: string): Promise<void> {
  const a = await repo.obterAutomacao(id);
  if (!a) throw new ErroDeAcao("nao_encontrada", "Automação não encontrada.", 404);
  await repo.removerAutomacao(id);
}
