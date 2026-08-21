"use client";
import { useState } from "react";

export function FormTracking({ perfil, inicial }: {
  perfil: string; inicial: { ativo?: boolean; base?: string };
}) {
  const [ativo, setAtivo] = useState(Boolean(inicial.ativo));
  const [base, setBase] = useState(inicial.base ?? "");
  const [aviso, setAviso] = useState("");

  async function salvar() {
    setAviso("salvando…");
    const r = await fetch("/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, chave: "tracking", valor: { ativo, base } }),
    });
    setAviso(r.ok ? "✓ salvo — vale para as próximas mensagens"
                  : `erro: ${(await r.json()).erro}`);
  }

  return (
    <section className="mt-8 rounded-xl border border-linha bg-carta p-6">
      <div className="flex items-center gap-3">
        <p className="text-xs uppercase tracking-wider text-acento">{perfil}</p>
        <h2 className="text-sm font-semibold">Tracking de cliques</h2>
      </div>
      <p className="mt-2 text-sm text-tinta2">
        Ligado, as mensagens saem com <span className="font-mono text-xs">{"{base}/r/{código}"}</span> e
        cada clique fica registrado antes de redirecionar ao Mercado Livre.
        Só ligue quando o painel tiver endereço público — senão o grupo recebe link morto.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={ativo}
            onChange={(e) => setAtivo(e.target.checked)} className="accent-acento" />
          ativo
        </label>
        <input value={base} onChange={(e) => setBase(e.target.value)}
          placeholder="https://painel.afilify.com.br"
          className="min-w-72 flex-1 rounded-lg border border-linha bg-carta2 px-3 py-2 font-mono text-xs outline-none focus:border-acento" />
        <button onClick={salvar}
          className="rounded-lg bg-acento px-4 py-2 text-sm font-semibold text-fundo">
          Salvar
        </button>
        <span className="text-xs text-tinta2">{aviso}</span>
      </div>
    </section>
  );
}
