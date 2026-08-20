"use client";
import { useState } from "react";

type Cfg = { ativo?: boolean; grupos?: string[]; intervalo_seg?: number; janela_min?: number };

export function FormFontes({ perfil, inicial, disponiveis }:
  { perfil: string; inicial: Cfg; disponiveis: Array<{ jid: string; nome: string }> }) {
  const [ativo, setAtivo] = useState(inicial.ativo ?? true);
  const [grupos, setGrupos] = useState<string[]>(inicial.grupos ?? []);
  const [intervalo, setIntervalo] = useState(inicial.intervalo_seg ?? 180);
  const [janela, setJanela] = useState(inicial.janela_min ?? 90);
  const [aviso, setAviso] = useState("");
  const nomeDe = (jid: string) => disponiveis.find((g) => g.jid === jid)?.nome ?? jid;
  const candidatos = disponiveis.filter((g) => !grupos.includes(g.jid));

  async function salvar() {
    setAviso("salvando…");
    const r = await fetch("/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, chave: "clonador",
        valor: { ativo, grupos, intervalo_seg: intervalo, janela_min: janela } }),
    });
    setAviso(r.ok ? "✓ salvo — vale no próximo ciclo do monitor" : `erro: ${(await r.json()).erro}`);
  }

  return (
    <section className="mt-6 rounded-xl border border-linha bg-carta p-6">
      <div className="flex items-center gap-3">
        <p className="text-xs uppercase tracking-wider text-acento">{perfil}</p>
        <label className="ml-auto flex items-center gap-2 text-sm">
          <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)}
            className="h-4 w-4 accent-[var(--color-acento)]" />
          monitor ativo
        </label>
      </div>

      <p className="mt-4 text-xs text-tinta2">Grupos monitorados</p>
      <ul className="mt-2 grid gap-2">
        {grupos.map((jid) => (
          <li key={jid} className="flex items-center gap-2 rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm">
            <span className="truncate">{nomeDe(jid)}</span>
            <span className="text-xs text-tinta2">{jid}</span>
            <button onClick={() => setGrupos(grupos.filter((g) => g !== jid))}
              className="ml-auto text-xs text-tinta2 hover:text-erro">remover</button>
          </li>
        ))}
        {grupos.length === 0 && <li className="text-sm text-tinta2">nenhum — o monitor fica parado</li>}
      </ul>
      {candidatos.length > 0 && (
        <select className="mt-2 w-full rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm"
          value="" onChange={(e) => e.target.value && setGrupos([...grupos, e.target.value])}>
          <option value="">+ adicionar grupo da sua conta…</option>
          {candidatos.map((g) => <option key={g.jid} value={g.jid}>{g.nome} · {g.jid}</option>)}
        </select>
      )}

      <div className="mt-4 flex flex-wrap gap-6 text-sm">
        <label className="flex items-center gap-2 text-tinta2">varre a cada
          <input type="number" min={60} step={30} value={intervalo}
            onChange={(e) => setIntervalo(Number(e.target.value))}
            className="w-24 rounded-lg border border-linha bg-carta2 px-2 py-1.5 text-center tabular-nums" /> seg
        </label>
        <label className="flex items-center gap-2 text-tinta2">ignora mensagens com mais de
          <input type="number" min={10} max={720} value={janela}
            onChange={(e) => setJanela(Number(e.target.value))}
            className="w-24 rounded-lg border border-linha bg-carta2 px-2 py-1.5 text-center tabular-nums" /> min
        </label>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <button onClick={salvar} className="rounded-lg bg-acento px-4 py-2 text-sm font-semibold text-fundo">Salvar</button>
        <span className="text-xs text-tinta2">{aviso}</span>
      </div>
    </section>
  );
}
