/**
 * LIMITES DO PLANO — o que a conta pode fazer.
 *
 * Existem desde já para que abrir a plataforma a clientes seja configuração,
 * não migração (D27). Nesta fase os valores são generosos e o usuário
 * praticamente não esbarra neles — mas quando esbarrar, lê o limite e o que
 * fazer, nunca um erro genérico.
 */
import "server-only";
import { uma, executar } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";

export type Limites = {
  conexoes: number;
  projetos: number;
  automacoes: number;
  publicacoesDia: number;
  testesBuscaDia: number;
  envriosPorConexaoHora: number;
};

const PADRAO: Limites = {
  conexoes: 5,
  projetos: 10,
  automacoes: 20,
  publicacoesDia: 500,
  testesBuscaDia: 50,
  envriosPorConexaoHora: 40,
};

export async function doWorkspace(): Promise<Limites> {
  const l = await uma("SELECT * FROM limites_plano WHERE workspace_id = ?", [WORKSPACE]).catch(
    () => null,
  );
  if (!l) return PADRAO;
  const n = (v: unknown, padrao: number) => (Number.isFinite(Number(v)) ? Number(v) : padrao);
  return {
    conexoes: n(l.max_conexoes, PADRAO.conexoes),
    projetos: n(l.max_projetos, PADRAO.projetos),
    automacoes: n(l.max_automacoes, PADRAO.automacoes),
    publicacoesDia: n(l.max_publicacoes_dia, PADRAO.publicacoesDia),
    testesBuscaDia: n(l.max_testes_busca_dia, PADRAO.testesBuscaDia),
    envriosPorConexaoHora: n(l.teto_envios_conexao_hora, PADRAO.envriosPorConexaoHora),
  };
}

export async function garantirExistem(): Promise<void> {
  const l = await uma("SELECT workspace_id FROM limites_plano WHERE workspace_id = ?", [
    WORKSPACE,
  ]).catch(() => null);
  if (l) return;
  await executar(
    `INSERT INTO limites_plano (workspace_id, max_conexoes, max_projetos, max_automacoes,
       max_publicacoes_dia, max_testes_busca_dia, teto_envios_conexao_hora, atualizado_em)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      WORKSPACE,
      PADRAO.conexoes,
      PADRAO.projetos,
      PADRAO.automacoes,
      PADRAO.publicacoesDia,
      PADRAO.testesBuscaDia,
      PADRAO.envriosPorConexaoHora,
      new Date().toISOString(),
    ],
  ).catch(() => 0);
}

/** Quanto do dia já foi usado — para a tela avisar antes de bater o teto. */
export async function usoDoDia(): Promise<{ publicacoes: number; testes: number }> {
  const hoje = new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
  const conta = async (sql: string, params: unknown[]) =>
    Number((await uma(sql, params).catch(() => null))?.n ?? 0);
  return {
    publicacoes: await conta(
      "SELECT COUNT(*) AS n FROM publicacoes WHERE workspace_id = ? AND estado = 'enviada' AND enviada_em LIKE ?",
      [WORKSPACE, `${hoje}%`],
    ),
    testes: await conta(
      "SELECT COUNT(*) AS n FROM comandos WHERE workspace_id = ? AND tipo = 'testar_busca' AND criado_em LIKE ?",
      [WORKSPACE, `${hoje}%`],
    ),
  };
}
