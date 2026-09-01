/**
 * OFERTAS E PUBLICAÇÕES — a operação do dia, no modelo novo.
 *
 * Duas listas que respondem perguntas diferentes: "o que a Afilify
 * encontrou?" e "o que ela publicou, e o que deu errado?".
 *
 * Todo motivo exibido passa por tradução — o usuário nunca lê o texto cru
 * que veio da plataforma.
 */
import "server-only";
import { todas, uma } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";

export type OfertaLinha = {
  id: string;
  nome: string;
  marca: string;
  preco: number | null;
  precoOriginal: number | null;
  desconto: number | null;
  estado: string;
  motivo: string;
  origem: string;
  quando: string;
};

export type PublicacaoLinha = {
  id: string;
  oferta: string;
  destino: string;
  estado: string;
  tentativa: number;
  ciclo: number;
  motivo: string;
  quando: string | null;
};

/* Estados internos → o que o usuário lê. Um estado sem tradução aqui
   apareceria como palavra de banco na tela. */
const ESTADO_OFERTA: Record<string, string> = {
  nova: "Encontrada",
  pronta: "Aguardando publicação",
  retida: "Aguardando",
  publicada: "Publicada",
  ignorada: "Ignorada",
  expirada: "Expirou antes de publicar",
};

const ESTADO_PUBLICACAO: Record<string, string> = {
  agendada: "Na fila",
  enviando: "Saindo agora",
  enviada: "Publicada",
  falhou: "Não saiu",
  cancelada: "Cancelada",
};

const RETENCAO: Record<string, string> = {
  sem_link: "Aguardando o link de afiliado ser gerado.",
  conexao_mercadolivre:
    "Sua conexão com o Mercado Livre expirou. Reconecte sua conta para continuar gerando ofertas.",
  conexao_destino: "A conta de WhatsApp desta automação está desconectada.",
};

export function rotuloOferta(estado: string): string {
  return ESTADO_OFERTA[estado] ?? "Aguardando";
}

export function rotuloPublicacao(estado: string): string {
  return ESTADO_PUBLICACAO[estado] ?? "Aguardando";
}

/** Motivo em linguagem comum. Texto técnico desconhecido não vaza para a tela. */
export function motivoLegivelDaRetencao(motivo: string): string {
  return RETENCAO[motivo] ?? "Esta oferta está aguardando para ser publicada.";
}

export async function ofertas(projetoId: string, limite = 40): Promise<OfertaLinha[]> {
  const linhas = await todas(
    `SELECT id, nome, marca, preco_promocional, preco_original, desconto_pct, estado,
            motivo_retencao, origem, criado_em
       FROM ofertas_projeto WHERE workspace_id = ? AND projeto_id = ?
      ORDER BY criado_em DESC LIMIT ${Number(limite)}`,
    [WORKSPACE, projetoId],
  ).catch(() => []);
  return linhas.map((l) => ({
    id: String(l.id),
    nome: String(l.nome ?? ""),
    marca: String(l.marca ?? ""),
    preco: l.preco_promocional == null ? null : Number(l.preco_promocional),
    precoOriginal: l.preco_original == null ? null : Number(l.preco_original),
    desconto: l.desconto_pct == null ? null : Number(l.desconto_pct),
    estado: String(l.estado),
    motivo: l.motivo_retencao ? motivoLegivelDaRetencao(String(l.motivo_retencao)) : "",
    origem: String(l.origem) === "monitoramento" ? "Monitoramento" : "Busca automática",
    quando: String(l.criado_em ?? ""),
  }));
}

export async function publicacoes(projetoId: string, limite = 40): Promise<PublicacaoLinha[]> {
  const linhas = await todas(
    `SELECT p.id, p.estado, p.tentativa, p.ciclo, p.motivo_falha, p.enviada_em, p.agendada_para,
            o.nome AS oferta, d.nome AS destino, d.alvo
       FROM publicacoes p
       JOIN ofertas_projeto o ON o.id = p.oferta_id
       JOIN destinos d ON d.id = p.destino_id
      WHERE p.workspace_id = ? AND p.projeto_id = ?
      ORDER BY COALESCE(p.enviada_em, p.agendada_para, p.criado_em) DESC LIMIT ${Number(limite)}`,
    [WORKSPACE, projetoId],
  ).catch(() => []);
  return linhas.map((l) => ({
    id: String(l.id),
    oferta: String(l.oferta ?? ""),
    // Grupo sem nome resolvido continua identificável, sem mostrar o id cru.
    destino: String(l.destino || `Grupo …${String(l.alvo ?? "").split("@")[0].slice(-4)}`),
    estado: String(l.estado),
    tentativa: Number(l.tentativa ?? 1),
    ciclo: Number(l.ciclo ?? 1),
    motivo: String(l.motivo_falha ?? ""),
    quando: (l.enviada_em ?? l.agendada_para ?? null) as string | null,
  }));
}

export async function resumoDoDia(projetoId: string) {
  const hoje = new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
  const conta = async (sql: string, params: unknown[]) =>
    Number((await uma(sql, params).catch(() => null))?.n ?? 0);

  const [encontradas, publicadas, naFila, aguardando, falharam] = await Promise.all([
    conta(
      "SELECT COUNT(*) AS n FROM ofertas_projeto WHERE projeto_id = ? AND criado_em LIKE ?",
      [projetoId, `${hoje}%`],
    ),
    conta(
      "SELECT COUNT(*) AS n FROM publicacoes WHERE projeto_id = ? AND estado = 'enviada' AND enviada_em LIKE ?",
      [projetoId, `${hoje}%`],
    ),
    conta("SELECT COUNT(*) AS n FROM publicacoes WHERE projeto_id = ? AND estado = 'agendada'", [projetoId]),
    conta("SELECT COUNT(*) AS n FROM ofertas_projeto WHERE projeto_id = ? AND estado = 'retida'", [projetoId]),
    conta("SELECT COUNT(*) AS n FROM publicacoes WHERE projeto_id = ? AND estado = 'falhou'", [projetoId]),
  ]);
  return { encontradas, publicadas, naFila, aguardando, falharam };
}
