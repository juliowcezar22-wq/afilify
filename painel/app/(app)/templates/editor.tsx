"use client";
import { useMemo, useState } from "react";

type Cfg = Record<string, unknown>;
type Msg = { base?: string; linha_loja_oficial?: string; rodape?: string };

const reais = (v: unknown) =>
  Number(v ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });

export function Editor({ perfil, cfg, amostra }:
  { perfil: string; cfg: Cfg; amostra: Record<string, unknown> }) {
  const msg0 = (cfg.mensagem ?? {}) as Msg;
  const hl0 = (cfg.headlines ?? {}) as Record<string, string[]>;
  const [base, setBase] = useState(msg0.base ?? "");
  const [linhaLoja, setLinhaLoja] = useState(msg0.linha_loja_oficial ?? "");
  const [rodape, setRodape] = useState(msg0.rodape ?? "");
  const [pools, setPools] = useState<Record<string, string>>(
    Object.fromEntries(Object.entries(hl0).map(([k, v]) => [k, v.join("\n")])));
  const [aviso, setAviso] = useState("");

  const preview = useMemo(() => {
    const primeiro = Object.values(pools)[0]?.split("\n")[0] ?? "HEADLINE";
    const condicao = String(amostra.condicao ?? "");
    const lloja = amostra.loja_oficial && amostra.loja
      ? (linhaLoja || "\n").replace("{loja}", String(amostra.loja)) : "\n";
    let t = base
      .replaceAll("{headline}", primeiro)
      .replaceAll("{nome}", String(amostra.nome ?? "Produto de exemplo 100ml"))
      .replaceAll("{preco_original}", reais(amostra.preco_original))
      .replaceAll("{preco_promocional}",
        reais(amostra.preco_promocional) + (condicao ? ` ${condicao}` : ""))
      .replaceAll("{desconto}", String(amostra.desconto_pct ?? 30))
      .replaceAll("{linha_loja}", lloja)
      .replaceAll("{link}", String(amostra.link_afiliado ?? "https://meli.la/xxxx"));
    if (rodape) t += `\n\n${rodape}`;
    return t;
  }, [base, linhaLoja, rodape, pools, amostra]);

  async function salvar() {
    setAviso("salvando…");
    const headlines = Object.fromEntries(Object.entries(pools).map(
      ([k, v]) => [k, v.split("\n").map((s) => s.trim()).filter(Boolean)]));
    for (const [chave, valor] of [
      ["mensagem", { base, linha_loja_oficial: linhaLoja, rodape }],
      ["headlines", headlines],
    ] as const) {
      const r = await fetch("/api/config", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ perfil, chave, valor }),
      });
      if (!r.ok) { setAviso(`erro: ${(await r.json()).erro}`); return; }
    }
    setAviso("✓ salvo — vale a partir da próxima mensagem");
  }

  const campo = "w-full rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm outline-none focus:border-acento font-mono";

  return (
    <section className="mt-8 rounded-xl border border-linha bg-carta p-6">
      <p className="text-xs uppercase tracking-wider text-acento">{perfil}</p>
      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        <div className="grid gap-4">
          <label className="text-xs text-tinta2">Template da mensagem
            <textarea rows={8} value={base} onChange={(e) => setBase(e.target.value)}
              className={`mt-1 ${campo}`} />
          </label>
          <label className="text-xs text-tinta2">Linha da loja oficial ({"{loja}"})
            <input value={linhaLoja} onChange={(e) => setLinhaLoja(e.target.value)}
              className={`mt-1 ${campo}`} />
          </label>
          <label className="text-xs text-tinta2">Rodapé (vazio = sem rodapé)
            <input value={rodape} onChange={(e) => setRodape(e.target.value)}
              placeholder="_#publicidade · link de afiliado_" className={`mt-1 ${campo}`} />
          </label>
          {Object.entries(pools).map(([pool, texto]) => (
            <label key={pool} className="text-xs text-tinta2">
              Headlines · {pool.replaceAll("_", " ")} (uma por linha)
              <textarea rows={Math.min(6, texto.split("\n").length + 1)} value={texto}
                onChange={(e) => setPools({ ...pools, [pool]: e.target.value })}
                className={`mt-1 ${campo}`} />
            </label>
          ))}
        </div>
        <div>
          <p className="text-xs text-tinta2">Preview (com uma oferta real já publicada)</p>
          <div className="mt-1 whitespace-pre-wrap rounded-xl border border-linha bg-fundo p-4 text-sm leading-relaxed">
            {preview}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button onClick={salvar}
              className="rounded-lg bg-acento px-4 py-2 text-sm font-semibold text-fundo">
              Salvar
            </button>
            <span className="text-xs text-tinta2">{aviso}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
