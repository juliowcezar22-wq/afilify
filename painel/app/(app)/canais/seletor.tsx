"use client";
import { useState } from "react";

export function SeletorDestino({ perfil, atual, grupos, enviadasHoje }: {
  perfil: string; atual: string;
  grupos: Array<{ jid: string; nome: string }>; enviadasHoje: number;
}) {
  const [destino, setDestino] = useState(atual);
  const [aviso, setAviso] = useState("");
  const nome = grupos.find((g) => g.jid === destino)?.nome ?? destino;

  async function salvar() {
    if (destino !== atual &&
        !confirm(`Trocar o destino de "${perfil}" para "${nome}"?\n` +
                 "As PRÓXIMAS mensagens irão para o grupo novo.")) return;
    setAviso("salvando…");
    const r = await fetch("/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, chave: "canal", valor: { grupo: destino } }),
    });
    setAviso(r.ok ? "✓ salvo — próxima mensagem já vai para o destino novo"
                  : `erro: ${(await r.json()).erro}`);
  }

  return (
    <section className="mt-6 rounded-xl border border-linha bg-carta p-6">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-xs uppercase tracking-wider text-acento">{perfil}</p>
        <span className="ml-auto text-xs text-tinta2">{enviadasHoje} entrega(s) hoje neste destino</span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <select value={destino} onChange={(e) => setDestino(e.target.value)}
          className="min-w-72 flex-1 rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm outline-none focus:border-acento">
          {!grupos.some((g) => g.jid === destino) && destino && (
            <option value={destino}>{destino} (fora da conta?)</option>)}
          {grupos.map((g) => (
            <option key={g.jid} value={g.jid}>{g.nome} · {g.jid}</option>))}
        </select>
        <button onClick={salvar}
          className="rounded-lg bg-acento px-4 py-2 text-sm font-semibold text-fundo">
          Salvar destino
        </button>
        <span className="text-xs text-tinta2">{aviso}</span>
      </div>
    </section>
  );
}
