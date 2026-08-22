"use client";
import { useId, useState } from "react";
import { Botao } from "@/components/ui/botao";
import { CONTROLE } from "@/components/ui/campos";
import { DetalhesTecnicos } from "@/components/ui/detalhes-tecnicos";

type Cfg = { ativo?: boolean; grupos?: string[]; intervalo_seg?: number; janela_min?: number };
type Grupo = { jid: string; nome: string };

/* Presets legíveis (D12) — o valor gravado continua em segundos/minutos,
   contrato do motor intocado. Valor fora dos presets é preservado. */
const FREQUENCIAS: Array<[number, string]> = [
  [60, "Muito frequente"],
  [180, "Frequente (padrão)"],
  [600, "Econômica"],
];
const JANELAS: Array<[number, string]> = [
  [30, "Só oportunidades recentes"],
  [90, "Equilibrado (padrão)"],
  [240, "Aproveitar o dia inteiro"],
];

export function FormMonitoramento({
  perfil,
  nomeProjeto,
  inicial,
  disponiveis,
}: {
  perfil: string;
  nomeProjeto: string;
  inicial: Cfg;
  disponiveis: Grupo[];
}) {
  const idAtivo = useId();
  const idFreq = useId();
  const idJanela = useId();
  const idAdd = useId();
  const [ativo, setAtivo] = useState(inicial.ativo ?? true);
  const [grupos, setGrupos] = useState<string[]>(inicial.grupos ?? []);
  const [intervalo, setIntervalo] = useState(inicial.intervalo_seg ?? 180);
  const [janela, setJanela] = useState(inicial.janela_min ?? 90);
  const [aviso, setAviso] = useState<{ tom: "ok" | "erro"; texto: string } | null>(null);

  const nomeDe = (jid: string) =>
    disponiveis.find((g) => g.jid === jid)?.nome || `Grupo …${jid.split("@")[0].slice(-4)}`;
  const candidatos = disponiveis.filter((g) => !grupos.includes(g.jid));

  async function salvar() {
    setAviso(null);
    const r = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        perfil,
        chave: "clonador",
        valor: { ativo, grupos, intervalo_seg: intervalo, janela_min: janela },
      }),
    });
    setAviso(
      r.ok
        ? { tom: "ok", texto: "Salvo — o monitoramento já usa a nova configuração." }
        : { tom: "erro", texto: String((await r.json()).erro ?? "falha ao salvar") },
    );
  }

  const opcoes = (presets: Array<[number, string]>, atual: number) =>
    presets.some(([v]) => v === atual)
      ? presets
      : [...presets, [atual, `Personalizada (${atual})`] as [number, string]];

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium">{nomeProjeto}</p>
        <label htmlFor={idAtivo} className="flex items-center gap-2 text-sm text-tinta2">
          <input
            id={idAtivo}
            type="checkbox"
            checked={ativo}
            onChange={(e) => setAtivo(e.target.checked)}
            className="h-4 w-4 accent-[var(--color-acento)]"
          />
          Monitoramento ligado
        </label>
      </div>

      <p className="mt-4 text-xs font-medium text-tinta2">Grupos monitorados</p>
      <ul className="mt-2 grid grid-cols-1 gap-2">
        {grupos.map((jid) => (
          <li
            key={jid}
            className="flex items-center gap-3 rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm"
          >
            <span className="truncate">{nomeDe(jid)}</span>
            <button
              type="button"
              onClick={() => setGrupos(grupos.filter((g) => g !== jid))}
              className="ml-auto text-xs text-tinta2 hover:text-erro"
            >
              Remover
            </button>
          </li>
        ))}
        {grupos.length === 0 && (
          <li className="text-sm text-tinta3">
            Nenhum grupo monitorado — adicione um para começar a receber oportunidades.
          </li>
        )}
      </ul>
      {candidatos.length > 0 && (
        <div className="mt-2">
          <label htmlFor={idAdd} className="sr-only">
            Adicionar grupo para monitorar
          </label>
          <select
            id={idAdd}
            className={`${CONTROLE} w-full`}
            value=""
            onChange={(e) => e.target.value && setGrupos([...grupos, e.target.value])}
          >
            <option value="">+ Adicionar grupo…</option>
            {candidatos.map((g) => (
              <option key={g.jid} value={g.jid}>
                {g.nome || nomeDe(g.jid)}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={idFreq} className="mb-1 block text-xs font-medium text-tinta2">
            Frequência de monitoramento
          </label>
          <select
            id={idFreq}
            className={`${CONTROLE} w-full`}
            value={intervalo}
            onChange={(e) => setIntervalo(Number(e.target.value))}
          >
            {opcoes(FREQUENCIAS, intervalo).map(([v, rot]) => (
              <option key={v} value={v}>
                {rot}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={idJanela} className="mb-1 block text-xs font-medium text-tinta2">
            Considerar oportunidades de
          </label>
          <select
            id={idJanela}
            className={`${CONTROLE} w-full`}
            value={janela}
            onChange={(e) => setJanela(Number(e.target.value))}
          >
            {opcoes(JANELAS, janela).map(([v, rot]) => (
              <option key={v} value={v}>
                {rot}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <Botao onClick={salvar}>Salvar</Botao>
        {aviso && (
          <p role="status" className={`text-sm ${aviso.tom === "ok" ? "text-ok" : "text-erro"}`}>
            {aviso.texto}
          </p>
        )}
      </div>

      <DetalhesTecnicos
        itens={grupos.map((jid, i) => [`grupo monitorado ${i + 1}`, jid])}
      />
    </div>
  );
}
