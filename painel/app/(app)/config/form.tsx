"use client";
import { useState } from "react";

type Ritmo = {
  envios_por_dia?: number[]; inicio_janela?: number[]; fim_janela?: number[];
  busca_horas?: number[]; validade_horas?: number; proporcao_preferidas?: number;
};

const hhmm = (h: number) => {
  const m = Math.round(h * 60);
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
};

export function FormRitmo({ perfil, inicial }: { perfil: string; inicial: Ritmo }) {
  const [v, setV] = useState<Required<Ritmo>>({
    envios_por_dia: inicial.envios_por_dia ?? [60, 85],
    inicio_janela: inicial.inicio_janela ?? [8.75, 9.5],
    fim_janela: inicial.fim_janela ?? [22, 22.75],
    busca_horas: inicial.busca_horas ?? [7, 15],
    validade_horas: inicial.validade_horas ?? 48,
    proporcao_preferidas: inicial.proporcao_preferidas ?? 0.7,
  });
  const [aviso, setAviso] = useState("");

  async function salvar() {
    setAviso("salvando…");
    const r = await fetch("/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, chave: "ritmo", valor: v }),
    });
    setAviso(r.ok ? "✓ salvo" : `erro: ${(await r.json()).erro}`);
  }

  const campo = "w-24 rounded-lg border border-linha bg-carta2 px-2 py-1.5 text-sm text-center tabular-nums outline-none focus:border-acento";
  const Par = ({ rotulo, chave, passo = 1 }:
    { rotulo: string; chave: "envios_por_dia" | "inicio_janela" | "fim_janela"; passo?: number }) => (
    <label className="flex items-center justify-between gap-3 text-sm">
      <span className="text-tinta2">{rotulo}</span>
      <span className="flex items-center gap-2">
        <input type="number" step={passo} value={v[chave][0]} className={campo}
          onChange={(e) => setV({ ...v, [chave]: [Number(e.target.value), v[chave][1]] })} />
        <span className="text-tinta2">a</span>
        <input type="number" step={passo} value={v[chave][1]} className={campo}
          onChange={(e) => setV({ ...v, [chave]: [v[chave][0], Number(e.target.value)] })} />
        {chave !== "envios_por_dia" && (
          <span className="w-24 text-xs text-tinta2">({hhmm(v[chave][0])}–{hhmm(v[chave][1])})</span>
        )}
      </span>
    </label>
  );

  return (
    <section className="mt-8 rounded-xl border border-linha bg-carta p-6">
      <p className="text-xs uppercase tracking-wider text-acento">{perfil}</p>
      <div className="mt-4 grid gap-4">
        <Par rotulo="Ofertas por dia (sorteado entre)" chave="envios_por_dia" />
        <Par rotulo="Início da janela (hora decimal)" chave="inicio_janela" passo={0.25} />
        <Par rotulo="Fim da janela (hora decimal)" chave="fim_janela" passo={0.25} />
        <label className="flex items-center justify-between gap-3 text-sm">
          <span className="text-tinta2">Coletas (horas, separadas por vírgula)</span>
          <input value={v.busca_horas.join(", ")} className="w-56 rounded-lg border border-linha bg-carta2 px-3 py-1.5 text-sm outline-none focus:border-acento"
            onChange={(e) => setV({ ...v, busca_horas: e.target.value.split(",")
              .map((x) => parseInt(x.trim(), 10)).filter((x) => !isNaN(x)) })} />
        </label>
        <label className="flex items-center justify-between gap-3 text-sm">
          <span className="text-tinta2">Validade da oferta (horas)</span>
          <input type="number" value={v.validade_horas} className={campo}
            onChange={(e) => setV({ ...v, validade_horas: Number(e.target.value) })} />
        </label>
        <label className="flex items-center justify-between gap-3 text-sm">
          <span className="text-tinta2">Proporção de importados (0–1)</span>
          <input type="number" step={0.05} min={0} max={1} value={v.proporcao_preferidas} className={campo}
            onChange={(e) => setV({ ...v, proporcao_preferidas: Number(e.target.value) })} />
        </label>
      </div>
      <div className="mt-5 flex items-center gap-3">
        <button onClick={salvar} className="rounded-lg bg-acento px-4 py-2 text-sm font-semibold text-fundo">Salvar</button>
        <span className="text-xs text-tinta2">{aviso}</span>
      </div>
    </section>
  );
}
