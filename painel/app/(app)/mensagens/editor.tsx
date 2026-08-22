"use client";
import { useId, useMemo, useState } from "react";
import { Botao } from "@/components/ui/botao";
import { CONTROLE } from "@/components/ui/campos";
import { Cartao } from "@/components/ui/cartao";

type Cfg = Record<string, unknown>;
type Msg = { base?: string; linha_loja_oficial?: string; rodape?: string };

/** Nomes humanos das categorias de chamada (D9). */
const NOMES_POOLS: Record<string, string> = {
  relampago: "Relâmpago",
  oferta_do_dia: "Oferta do dia",
  desconto_alto: "Desconto alto",
  desconto_medio: "Desconto médio",
  mais_vendido: "Mais vendido",
  geral: "Geral",
};
const nomePool = (chave: string) =>
  NOMES_POOLS[chave] ??
  chave.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

const reaisSimples = (v: unknown) =>
  Number(v ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });

export function Editor({
  perfil,
  nomeProjeto,
  cfg,
  amostra,
}: {
  perfil: string;
  nomeProjeto: string;
  cfg: Cfg;
  amostra: Record<string, unknown>;
}) {
  const idRodape = useId();
  const idLoja = useId();
  const idBase = useId();
  const msg0 = (cfg.mensagem ?? {}) as Msg;
  const hl0 = (cfg.headlines ?? {}) as Record<string, string[]>;

  const [base, setBase] = useState(msg0.base ?? "");
  const [linhaLoja, setLinhaLoja] = useState(msg0.linha_loja_oficial ?? "");
  const [rodape, setRodape] = useState(msg0.rodape ?? "");
  const [pools, setPools] = useState<Record<string, string[]>>(
    Object.fromEntries(Object.entries(hl0).map(([k, v]) => [k, [...v]])),
  );
  const [novas, setNovas] = useState<Record<string, string>>({});
  const [aviso, setAviso] = useState<{ tom: "ok" | "erro"; texto: string } | null>(null);
  const [salvando, setSalvando] = useState(false);

  const preview = useMemo(() => {
    const primeira =
      pools.geral?.[0] ?? Object.values(pools).find((p) => p.length > 0)?.[0] ?? "SUA CHAMADA AQUI";
    const condicao = String(amostra.condicao ?? "");
    const lloja =
      amostra.loja_oficial && amostra.loja
        ? (linhaLoja || "\n").replace("{loja}", String(amostra.loja))
        : "\n";
    let t = base
      .replaceAll("{headline}", primeira)
      .replaceAll("{nome}", String(amostra.nome ?? "Produto de exemplo 100ml"))
      .replaceAll("{preco_original}", reaisSimples(amostra.preco_original ?? 319))
      .replaceAll(
        "{preco_promocional}",
        reaisSimples(amostra.preco_promocional ?? 242) + (condicao ? ` ${condicao}` : ""),
      )
      .replaceAll("{desconto}", String(amostra.desconto_pct ?? 30))
      .replaceAll("{linha_loja}", lloja)
      .replaceAll("{link}", String(amostra.link_afiliado ?? "https://meli.la/exemplo"));
    if (rodape) t += `\n\n${rodape}`;
    return t;
  }, [base, linhaLoja, rodape, pools, amostra]);

  function adicionar(pool: string) {
    const texto = (novas[pool] ?? "").trim();
    if (!texto) return;
    setPools({ ...pools, [pool]: [...(pools[pool] ?? []), texto] });
    setNovas({ ...novas, [pool]: "" });
  }

  function remover(pool: string, i: number) {
    setPools({ ...pools, [pool]: pools[pool].filter((_, j) => j !== i) });
  }

  async function salvar() {
    setSalvando(true);
    setAviso(null);
    const headlines = Object.fromEntries(
      Object.entries(pools).map(([k, v]) => [k, v.map((s) => s.trim()).filter(Boolean)]),
    );
    const vazio = Object.entries(headlines).find(([, v]) => v.length === 0);
    if (vazio) {
      setAviso({
        tom: "erro",
        texto: `A categoria "${nomePool(vazio[0])}" precisa de pelo menos uma chamada.`,
      });
      setSalvando(false);
      return;
    }
    for (const [chave, valor] of [
      ["mensagem", { base, linha_loja_oficial: linhaLoja, rodape }],
      ["headlines", headlines],
    ] as const) {
      const r = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ perfil, chave, valor }),
      });
      if (!r.ok) {
        setAviso({ tom: "erro", texto: String((await r.json()).erro ?? "falha ao salvar") });
        setSalvando(false);
        return;
      }
    }
    setAviso({ tom: "ok", texto: "Salvo — vale a partir da próxima publicação." });
    setSalvando(false);
  }

  return (
    <Cartao titulo={nomeProjeto} className="mt-4">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* Edição */}
        <div className="grid min-w-0 grid-cols-1 content-start gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-tinta2">
              Biblioteca de chamadas
            </p>
            <p className="mt-1 text-xs text-tinta3">
              A Afilify abre cada publicação com uma chamada da categoria que
              combina com a oferta, sem repetir a última usada.
            </p>
            <div className="mt-3 grid grid-cols-1 gap-4">
              {Object.entries(pools).map(([pool, itens]) => (
                <div key={pool} className="rounded-lg border border-linha p-3">
                  <p className="text-xs font-semibold text-tinta2">{nomePool(pool)}</p>
                  <ul className="mt-2 grid grid-cols-1 gap-1.5">
                    {itens.map((h, i) => (
                      <li
                        key={`${h}-${i}`}
                        className="flex items-center gap-2 rounded-md bg-carta2 px-2.5 py-1.5 text-sm"
                      >
                        <span className="min-w-0 truncate">{h}</span>
                        <button
                          type="button"
                          onClick={() => remover(pool, i)}
                          aria-label={`Remover chamada "${h}"`}
                          className="ml-auto shrink-0 text-xs text-tinta3 hover:text-erro"
                        >
                          ✕
                        </button>
                      </li>
                    ))}
                    {itens.length === 0 && (
                      <li className="text-xs text-tinta3">
                        Nenhuma chamada — adicione pelo menos uma.
                      </li>
                    )}
                  </ul>
                  <div className="mt-2 flex gap-2">
                    <label htmlFor={`nova-${pool}-${idBase}`} className="sr-only">
                      Nova chamada em {nomePool(pool)}
                    </label>
                    <input
                      id={`nova-${pool}-${idBase}`}
                      value={novas[pool] ?? ""}
                      onChange={(e) => setNovas({ ...novas, [pool]: e.target.value })}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          adicionar(pool);
                        }
                      }}
                      placeholder="Nova chamada…"
                      className={`${CONTROLE} min-w-0 flex-1 py-1.5 text-xs`}
                    />
                    <Botao variante="secundario" tamanho="sm" onClick={() => adicionar(pool)}>
                      Adicionar
                    </Botao>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor={idRodape} className="mb-1 block text-xs font-medium text-tinta2">
              Rodapé da mensagem
            </label>
            <input
              id={idRodape}
              value={rodape}
              onChange={(e) => setRodape(e.target.value)}
              placeholder="Ex.: #publicidade · link de afiliado (vazio = sem rodapé)"
              className={`${CONTROLE} w-full`}
            />
          </div>

          <details className="group rounded-lg border border-linha p-3">
            <summary className="cursor-pointer select-none text-xs font-medium text-tinta2 hover:text-tinta">
              <span aria-hidden className="mr-1 inline-block transition-transform group-open:rotate-90">
                ▸
              </span>
              Modo avançado — estrutura da mensagem
            </summary>
            <div className="mt-3 grid grid-cols-1 gap-4">
              <p className="text-xs text-tinta3">
                A estrutura usa variáveis entre chaves que são preenchidas a cada
                publicação: {"{headline}"}, {"{nome}"}, {"{preco_original}"},{" "}
                {"{preco_promocional}"}, {"{linha_loja}"} e {"{link}"}. O salvar
                é bloqueado se alguma variável obrigatória faltar.
              </p>
              <div>
                <label htmlFor={idBase} className="mb-1 block text-xs font-medium text-tinta2">
                  Estrutura da mensagem
                </label>
                <textarea
                  id={idBase}
                  rows={8}
                  value={base}
                  onChange={(e) => setBase(e.target.value)}
                  className={`${CONTROLE} w-full font-mono text-xs leading-relaxed`}
                />
              </div>
              <div>
                <label htmlFor={idLoja} className="mb-1 block text-xs font-medium text-tinta2">
                  Linha da loja oficial ({"{loja}"} vira o nome da loja)
                </label>
                <input
                  id={idLoja}
                  value={linhaLoja}
                  onChange={(e) => setLinhaLoja(e.target.value)}
                  className={`${CONTROLE} w-full font-mono text-xs`}
                />
              </div>
            </div>
          </details>

          <div className="flex items-center gap-3">
            <Botao onClick={salvar} disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Botao>
            {aviso && (
              <p
                role="status"
                className={`text-sm ${aviso.tom === "ok" ? "text-ok" : "text-erro"}`}
              >
                {aviso.texto}
              </p>
            )}
          </div>
        </div>

        {/* Preview */}
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-tinta2">
            Como vai aparecer no grupo
          </p>
          <div className="mt-3 rounded-xl bg-fundo p-4">
            <div className="max-w-full rounded-lg rounded-tl-none border border-linha bg-carta2 px-3.5 py-2.5 sm:max-w-sm">
              <p className="whitespace-pre-wrap text-sm leading-relaxed [overflow-wrap:anywhere]">
                {preview}
              </p>
              <p className="mt-1.5 text-right text-[10px] text-tinta3">agora</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-tinta3">
            Preview com uma oferta real já publicada — os valores mudam a cada
            publicação.
          </p>
        </div>
      </div>
    </Cartao>
  );
}
