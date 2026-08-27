/**
 * RITMO — o compasso que o usuário controla.
 *
 * O que é dele: quantas publicações por dia, em que janela de horário, por
 * quanto tempo uma oferta continua válida.
 *
 * O que NÃO é dele e não aparece aqui: dispersão (a forma da distribuição,
 * calibrada contra o comportamento real de um grupo), jitter, intervalo
 * entre destinos, teto de segurança. São decisões da Afilify — pedir que o
 * usuário escolha "0,82" seria transformá-lo em operador do motor.
 *
 * A hora vive como decimal no contrato do motor e como HH:MM na tela. A
 * conversão acontece na borda, aqui.
 */
import "server-only";
import { ErroDeAcao } from "@/lib/conexoes-servico";

export type Ritmo = {
  publicacoesPorDia: [number, number];
  abreEntre: [string, string];
  fechaEntre: [string, string];
  validadeHoras: number;
  proporcaoPreferidas: number;
};

export const RITMO_PADRAO: Ritmo = {
  publicacoesPorDia: [40, 60],
  abreEntre: ["09:00", "10:00"],
  fechaEntre: ["21:00", "22:00"],
  validadeHoras: 48,
  proporcaoPreferidas: 0,
};

export function decimalParaHora(d: number): string {
  const total = Math.round(d * 60);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export function horaParaDecimal(hhmm: string): number {
  const [h, m] = String(hhmm).split(":").map(Number);
  if (!Number.isFinite(h) || !Number.isFinite(m))
    throw new ErroDeAcao("hora_invalida", "Informe o horário no formato 00:00.");
  return h + m / 60;
}

/** O que está guardado (decimal) → o que a tela mostra (HH:MM). */
export function paraTela(guardado: Record<string, unknown>): Ritmo {
  const par = (v: unknown, padrao: [number, number]): [number, number] =>
    Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === "number")
      ? [v[0] as number, v[1] as number]
      : padrao;

  const abre = par(guardado.inicio_janela, [9, 10]);
  const fecha = par(guardado.fim_janela, [21, 22]);
  return {
    publicacoesPorDia: par(guardado.envios_por_dia, RITMO_PADRAO.publicacoesPorDia),
    abreEntre: [decimalParaHora(abre[0]), decimalParaHora(abre[1])],
    fechaEntre: [decimalParaHora(fecha[0]), decimalParaHora(fecha[1])],
    validadeHoras:
      typeof guardado.validade_horas === "number" ? guardado.validade_horas : RITMO_PADRAO.validadeHoras,
    proporcaoPreferidas:
      typeof guardado.proporcao_preferidas === "number" ? guardado.proporcao_preferidas : 0,
  };
}

/** O que a tela envia → o que o motor lê. Valida antes de gravar. */
export function paraMotor(bruto: unknown): Record<string, unknown> {
  const d = (bruto ?? {}) as Record<string, unknown>;

  const cota = d.publicacoesPorDia;
  if (!Array.isArray(cota) || cota.length !== 2)
    throw new ErroDeAcao("cota_invalida", "Informe de quantas a quantas publicações por dia.");
  const [min, max] = cota.map(Number);
  if (!Number.isFinite(min) || !Number.isFinite(max) || min < 1 || min > max)
    throw new ErroDeAcao(
      "cota_invalida",
      "O mínimo de publicações precisa ser ao menos 1 e não pode passar do máximo.",
    );

  const hora = (v: unknown, campo: string): number => {
    if (typeof v !== "string" || !v.trim())
      throw new ErroDeAcao("hora_vazia", `Informe o horário de ${campo}.`);
    return horaParaDecimal(v);
  };

  const abre = (d.abreEntre ?? []) as unknown[];
  const fecha = (d.fechaEntre ?? []) as unknown[];
  const inicio: [number, number] = [hora(abre[0], "abertura"), hora(abre[1], "abertura")];
  const fim: [number, number] = [hora(fecha[0], "fechamento"), hora(fecha[1], "fechamento")];
  if (inicio[1] >= fim[0])
    throw new ErroDeAcao("janela_invalida", "A janela precisa abrir antes de fechar.");

  const validade = Number(d.validadeHoras ?? RITMO_PADRAO.validadeHoras);
  if (!Number.isFinite(validade) || validade < 1)
    throw new ErroDeAcao("validade_invalida", "A validade precisa ser de ao menos 1 hora.");

  const proporcao = Number(d.proporcaoPreferidas ?? 0);
  if (!Number.isFinite(proporcao) || proporcao < 0 || proporcao > 1)
    throw new ErroDeAcao("proporcao_invalida", "A proporção precisa ficar entre 0 e 100%.");

  return {
    envios_por_dia: [Math.round(min), Math.round(max)],
    inicio_janela: inicio,
    fim_janela: fim,
    validade_horas: Math.round(validade),
    proporcao_preferidas: proporcao,
  };
}

/**
 * A partir de quando cada mudança vale.
 *
 * O plano do dia é sorteado uma vez, de manhã: mexer na cota agora não
 * muda o dia que já começou. Dizer isso evita o usuário achar que a
 * configuração não funcionou.
 */
export function quandoPassaAValer(campo: keyof Ritmo): string {
  if (campo === "publicacoesPorDia" || campo === "abreEntre" || campo === "fechaEntre")
    return "vale a partir de amanhã";
  return "vale já na próxima publicação";
}
