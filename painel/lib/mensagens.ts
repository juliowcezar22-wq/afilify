/**
 * MENSAGENS — como a publicação fica no grupo.
 *
 * O fluxo comum edita a biblioteca de chamadas e o rodapé, e vê o resultado
 * num preview com uma oferta real do PRÓPRIO projeto — preview com produto
 * inventado dá confiança falsa: o texto que engana é justamente o que só
 * quebra com dado de verdade.
 *
 * O modelo com {tokens} fica no modo avançado: parseá-lo em campos seria
 * frágil, e template quebrado vira mensagem torta no grupo.
 */
import "server-only";
import { uma } from "@/lib/dados";
import { WORKSPACE } from "@/lib/conexoes";
import { ErroDeAcao } from "@/lib/conexoes-servico";

export type Mensagem = {
  base: string;
  rodape: string;
  linhaLojaOficial: string;
  chamadas: Record<string, string[]>;
};

/** Rótulos humanos das categorias de chamada. Chave desconhecida vira título. */
const CATEGORIAS: Record<string, string> = {
  relampago: "Relâmpago",
  oferta_do_dia: "Oferta do dia",
  desconto_alto: "Desconto alto",
  desconto_medio: "Desconto médio",
  mais_vendido: "Mais vendido",
  geral: "Geral",
};

const OBRIGATORIOS = ["{nome}", "{link}", "{preco_promocional}"];
const CONHECIDOS = [
  "headline", "nome", "preco_original", "preco_promocional",
  "desconto", "linha_loja", "link",
];

export function rotuloCategoria(chave: string): string {
  return (
    CATEGORIAS[chave] ??
    chave.replace(/[_-]/g, " ").replace(/^./, (c) => c.toUpperCase())
  );
}

export function validar(bruto: unknown): Mensagem {
  const d = (bruto ?? {}) as Record<string, unknown>;
  const base = String(d.base ?? "");

  for (const token of OBRIGATORIOS)
    if (!base.includes(token))
      throw new ErroDeAcao(
        "template_incompleto",
        `A mensagem precisa conter ${token} — sem isso a publicação sai quebrada no grupo.`,
      );

  const usados = [...base.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);
  const invalido = usados.find((t) => !CONHECIDOS.includes(t));
  if (invalido)
    throw new ErroDeAcao(
      "token_desconhecido",
      `A mensagem usa {${invalido}}, que a Afilify não sabe preencher.`,
    );

  const chamadas = (d.chamadas ?? {}) as Record<string, unknown>;
  const limpas: Record<string, string[]> = {};
  for (const [pool, lista] of Object.entries(chamadas)) {
    if (!Array.isArray(lista))
      throw new ErroDeAcao("chamadas_invalidas", `A lista "${rotuloCategoria(pool)}" não foi entendida.`);
    const textos = (lista as unknown[])
      .filter((x): x is string => typeof x === "string" && x.trim() !== "")
      .map((x) => x.trim());
    if (textos.length) limpas[pool] = textos;
  }

  return {
    base,
    rodape: String(d.rodape ?? ""),
    linhaLojaOficial: String(d.linhaLojaOficial ?? ""),
    chamadas: limpas,
  };
}

/** Uma oferta real do projeto, para o preview não mentir. */
export async function ofertaParaPreview(projetoId: string) {
  const l =
    (await uma(
      `SELECT nome, marca, loja, loja_oficial, preco_original, preco_promocional, desconto_pct
         FROM ofertas_projeto WHERE workspace_id = ? AND projeto_id = ?
        ORDER BY criado_em DESC LIMIT 1`,
      [WORKSPACE, projetoId],
    ).catch(() => null)) ?? null;
  if (!l) return null;
  return {
    nome: String(l.nome ?? ""),
    marca: String(l.marca ?? ""),
    loja: String(l.loja ?? ""),
    lojaOficial: Number(l.loja_oficial) === 1,
    precoOriginal: l.preco_original == null ? null : Number(l.preco_original),
    preco: l.preco_promocional == null ? null : Number(l.preco_promocional),
    desconto: l.desconto_pct == null ? null : Number(l.desconto_pct),
  };
}

/** Monta a mensagem como ela sairia — mesma substituição que o motor faz. */
export function preview(
  m: Mensagem,
  oferta: NonNullable<Awaited<ReturnType<typeof ofertaParaPreview>>>,
  chamada?: string,
): string {
  const reais = (v: number | null) =>
    v == null ? "" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const primeira = Object.values(m.chamadas)[0]?.[0] ?? "";
  const valores: Record<string, string> = {
    headline: chamada ?? primeira,
    nome: oferta.nome,
    preco_original: reais(oferta.precoOriginal),
    preco_promocional: reais(oferta.preco),
    desconto: oferta.desconto == null ? "" : `${oferta.desconto}%`,
    linha_loja: oferta.lojaOficial && oferta.loja ? m.linhaLojaOficial.replace("{loja}", oferta.loja) : "",
    link: "https://meli.la/exemplo",
  };

  let texto = m.base.replace(/\{(\w+)\}/g, (_, chave: string) => valores[chave] ?? "");
  if (m.rodape) texto += `\n\n${m.rodape}`;
  // Linhas que ficaram vazias porque o token não se aplica àquela oferta
  // sumiriam no WhatsApp — o preview precisa mostrar o mesmo.
  return texto.replace(/\n{3,}/g, "\n\n").trim();
}
