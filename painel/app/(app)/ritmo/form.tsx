"use client";
import { useId, useState } from "react";
import { horaDecimalParaHHMM, hhmmParaDecimal } from "@/lib/formatos";
import { Botao } from "@/components/ui/botao";
import { CONTROLE } from "@/components/ui/campos";

type Ritmo = {
  envios_por_dia?: number[];
  inicio_janela?: number[];
  fim_janela?: number[];
  busca_horas?: number[];
  validade_horas?: number;
  proporcao_preferidas?: number;
};

const HORAS = Array.from({ length: 24 }, (_, h) => h);

/**
 * Ritmo do projeto em linguagem de produto. O contrato do motor não muda:
 * janelas continuam gravadas em hora decimal (D6) — a conversão HH:MM ↔
 * decimal acontece aqui, na borda.
 */
export function FormRitmo({
  perfil,
  nomeProjeto,
  inicial,
}: {
  perfil: string;
  nomeProjeto: string;
  inicial: Ritmo;
}) {
  const id = useId();
  const [enviosMin, setEnviosMin] = useState(inicial.envios_por_dia?.[0] ?? 60);
  const [enviosMax, setEnviosMax] = useState(inicial.envios_por_dia?.[1] ?? 85);
  const [inicioA, setInicioA] = useState(horaDecimalParaHHMM(inicial.inicio_janela?.[0] ?? 8.75));
  const [inicioB, setInicioB] = useState(horaDecimalParaHHMM(inicial.inicio_janela?.[1] ?? 9.5));
  const [fimA, setFimA] = useState(horaDecimalParaHHMM(inicial.fim_janela?.[0] ?? 22));
  const [fimB, setFimB] = useState(horaDecimalParaHHMM(inicial.fim_janela?.[1] ?? 22.75));
  const [buscaHoras, setBuscaHoras] = useState<number[]>(inicial.busca_horas ?? [7, 15]);
  const [validade, setValidade] = useState(inicial.validade_horas ?? 48);
  const [proporcao, setProporcao] = useState(
    Math.round((inicial.proporcao_preferidas ?? 0.7) * 100),
  );
  const [aviso, setAviso] = useState<{ tom: "ok" | "erro"; texto: string } | null>(null);
  const [salvando, setSalvando] = useState(false);

  function alternarHora(h: number) {
    setBuscaHoras((atual) =>
      atual.includes(h) ? atual.filter((x) => x !== h) : [...atual, h].sort((a, b) => a - b),
    );
  }

  async function salvar() {
    setSalvando(true);
    setAviso(null);
    const valor = {
      envios_por_dia: [Number(enviosMin), Number(enviosMax)],
      inicio_janela: [hhmmParaDecimal(inicioA), hhmmParaDecimal(inicioB)],
      fim_janela: [hhmmParaDecimal(fimA), hhmmParaDecimal(fimB)],
      busca_horas: buscaHoras,
      validade_horas: Number(validade),
      proporcao_preferidas: Math.min(1, Math.max(0, proporcao / 100)),
    };
    const r = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, chave: "ritmo", valor }),
    });
    setAviso(
      r.ok
        ? {
            tom: "ok",
            texto:
              "Salvo. Quantidade e janela valem a partir de amanhã; o restante, imediatamente.",
          }
        : { tom: "erro", texto: String((await r.json()).erro ?? "falha ao salvar") },
    );
    setSalvando(false);
  }

  const campoHora = `${CONTROLE} w-28 text-center tabular-nums`;
  const campoNum = `${CONTROLE} w-24 text-center tabular-nums`;

  return (
    <div>
      <p className="text-sm font-medium">{nomeProjeto}</p>

      <div className="mt-4 grid grid-cols-1 gap-5">
        <fieldset>
          <legend className="text-xs font-medium text-tinta2">
            Publicações por dia
          </legend>
          <p className="mt-0.5 text-xs text-tinta3">
            A Afilify sorteia uma quantidade dentro da faixa, para variar como
            uma pessoa de verdade.
          </p>
          <div className="mt-2 flex items-center gap-2 text-sm text-tinta2">
            <label htmlFor={`${id}-emin`} className="sr-only">
              Mínimo de publicações por dia
            </label>
            <input
              id={`${id}-emin`}
              type="number"
              min={1}
              value={enviosMin}
              onChange={(e) => setEnviosMin(Number(e.target.value))}
              className={campoNum}
            />
            <span>a</span>
            <label htmlFor={`${id}-emax`} className="sr-only">
              Máximo de publicações por dia
            </label>
            <input
              id={`${id}-emax`}
              type="number"
              min={1}
              value={enviosMax}
              onChange={(e) => setEnviosMax(Number(e.target.value))}
              className={campoNum}
            />
            <span>por dia</span>
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs font-medium text-tinta2">Janela de publicação</legend>
          <p className="mt-0.5 text-xs text-tinta3">
            Início e fim também variam dentro das faixas, dia a dia.
          </p>
          <div className="mt-2 grid grid-cols-1 gap-2 text-sm text-tinta2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-14">Começa</span>
              <label htmlFor={`${id}-ia`} className="sr-only">
                Início mais cedo
              </label>
              <input
                id={`${id}-ia`}
                type="time"
                step={900}
                value={inicioA}
                onChange={(e) => setInicioA(e.target.value)}
                className={campoHora}
              />
              <span>a</span>
              <label htmlFor={`${id}-ib`} className="sr-only">
                Início mais tarde
              </label>
              <input
                id={`${id}-ib`}
                type="time"
                step={900}
                value={inicioB}
                onChange={(e) => setInicioB(e.target.value)}
                className={campoHora}
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-14">Termina</span>
              <label htmlFor={`${id}-fa`} className="sr-only">
                Fim mais cedo
              </label>
              <input
                id={`${id}-fa`}
                type="time"
                step={900}
                value={fimA}
                onChange={(e) => setFimA(e.target.value)}
                className={campoHora}
              />
              <span>a</span>
              <label htmlFor={`${id}-fb`} className="sr-only">
                Fim mais tarde
              </label>
              <input
                id={`${id}-fb`}
                type="time"
                step={900}
                value={fimB}
                onChange={(e) => setFimB(e.target.value)}
                className={campoHora}
              />
            </div>
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs font-medium text-tinta2">Horários de busca</legend>
          <p className="mt-0.5 text-xs text-tinta3">
            Em quais horas do dia a Afilify procura promoções novas.
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {HORAS.map((h) => {
              const ativo = buscaHoras.includes(h);
              return (
                <button
                  key={h}
                  type="button"
                  onClick={() => alternarHora(h)}
                  aria-pressed={ativo}
                  className={`rounded-md border px-2 py-1 text-xs tabular-nums transition-colors ${
                    ativo
                      ? "border-acento/60 bg-acento/10 font-semibold text-acento"
                      : "border-linha text-tinta3 hover:border-linha2 hover:text-tinta2"
                  }`}
                >
                  {String(h).padStart(2, "0")}h
                </button>
              );
            })}
          </div>
          {buscaHoras.length === 0 && (
            <p className="mt-1.5 text-xs text-erro">Escolha pelo menos um horário.</p>
          )}
        </fieldset>

        <fieldset>
          <legend className="text-xs font-medium text-tinta2">Validade da oferta</legend>
          <p className="mt-0.5 text-xs text-tinta3">
            Uma oferta que não foi publicada nesse prazo é descartada — preço de
            promoção envelhece rápido.
          </p>
          <div className="mt-2 flex items-center gap-2 text-sm text-tinta2">
            <label htmlFor={`${id}-val`} className="sr-only">
              Validade em horas
            </label>
            <input
              id={`${id}-val`}
              type="number"
              min={1}
              value={validade}
              onChange={(e) => setValidade(Number(e.target.value))}
              className={campoNum}
            />
            <span>horas</span>
          </div>
        </fieldset>

        <details className="group rounded-lg border border-linha p-3">
          <summary className="cursor-pointer select-none text-xs font-medium text-tinta2 hover:text-tinta">
            <span aria-hidden className="mr-1 inline-block transition-transform group-open:rotate-90">
              ▸
            </span>
            Avançado
          </summary>
          <div className="mt-3">
            <label htmlFor={`${id}-prop`} className="block text-xs font-medium text-tinta2">
              Preferência por marcas importadas
            </label>
            <p className="mt-0.5 text-xs text-tinta3">
              Específico de nichos como perfumes: percentual das publicações
              reservado para marcas importadas, quando houver estoque delas na
              fila.
            </p>
            <div className="mt-2 flex items-center gap-2 text-sm text-tinta2">
              <input
                id={`${id}-prop`}
                type="number"
                min={0}
                max={100}
                step={5}
                value={proporcao}
                onChange={(e) => setProporcao(Number(e.target.value))}
                className={campoNum}
              />
              <span>%</span>
            </div>
          </div>
        </details>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <Botao onClick={salvar} disabled={salvando || buscaHoras.length === 0}>
          {salvando ? "Salvando…" : "Salvar"}
        </Botao>
        {aviso && (
          <p role="status" className={`text-sm ${aviso.tom === "ok" ? "text-ok" : "text-erro"}`}>
            {aviso.texto}
          </p>
        )}
      </div>
    </div>
  );
}
