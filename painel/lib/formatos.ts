/**
 * Formatação e tradução para linguagem de produto (pt-BR).
 * Puro (sem imports de servidor) — usável em Server e Client Components.
 *
 * Regra do redesign: conversões acontecem AQUI, na borda da UI. O banco e o
 * motor continuam com os formatos internos (hora decimal, status em caps,
 * ISO local) — nenhum contrato muda.
 */

export const FUSO = "America/Sao_Paulo";

/** "2026-08-22" no fuso da operação. */
export function hojeISO(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: FUSO });
}

/** Epoch ms — helper para Server Components (comparações de "agora"). */
export function agoraMs(): number {
  return Date.now();
}

/** ISO UTC de agora — para comparações com timestamps do banco. */
export function agoraISO(): string {
  return new Date().toISOString();
}

/**
 * "2026-08-22T15:47:03" — agora no fuso da OPERAÇÃO, sem sufixo de fuso.
 * O motor grava timestamps locais (isoformat sem offset); comparações de
 * fila devem usar este formato, não o UTC (3h de diferença).
 */
export function agoraLocalISO(): string {
  return new Date().toLocaleString("sv-SE", { timeZone: FUSO }).replace(" ", "T");
}

/** "2026-08-08" — data de N dias atrás no fuso da operação. */
export function dataCorte(dias: number): string {
  return new Date(Date.now() - dias * 864e5).toLocaleDateString("sv-SE", { timeZone: FUSO });
}

export function reais(v: unknown): string {
  if (v == null || v === "") return "—";
  return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** hora decimal do motor → "08:45" (contrato: decimal nunca aparece na UI). */
export function horaDecimalParaHHMM(h: number): string {
  const m = Math.round(h * 60);
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

/** "08:45" → 8.75 (gravação no contrato do motor). */
export function hhmmParaDecimal(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return (Number.isFinite(h) ? h : 0) + (Number.isFinite(m) ? m : 0) / 60;
}

/** Pega "HH:MM" de um timestamp ISO local do motor (sem conversão de fuso). */
export function horaDe(iso: unknown): string {
  const s = String(iso ?? "");
  return s.length >= 16 ? s.slice(11, 16) : "—";
}

/**
 * Data curta humana: "Hoje, 13:32" · "Ontem, 09:10" · "22/08 às 13:32".
 * Os timestamps do motor são ISO no horário local da operação; comparação
 * textual do dia evita conversões de fuso indevidas.
 */
export function dataCurta(iso: unknown): string {
  const s = String(iso ?? "");
  if (s.length < 16) return "—";
  const dia = s.slice(0, 10);
  const hora = s.slice(11, 16);
  const hoje = hojeISO();
  if (dia === hoje) return `Hoje, ${hora}`;
  const ontem = new Date(Date.now() - 864e5).toLocaleDateString("sv-SE", { timeZone: FUSO });
  if (dia === ontem) return `Ontem, ${hora}`;
  return `${dia.slice(8, 10)}/${dia.slice(5, 7)} às ${hora}`;
}

/** "22/08" a partir de "2026-08-22". */
export function diaCurto(isoDia: unknown): string {
  const s = String(isoDia ?? "");
  return s.length >= 10 ? `${s.slice(8, 10)}/${s.slice(5, 7)}` : "—";
}

/* ── Tradução de status/origem (banco → produto) ───────────────────── */

export type Tom = "ok" | "erro" | "alerta" | "neutro" | "info";

/** status_envio da oferta → rótulo e tom de produto. */
export function statusOferta(status: unknown, erro?: unknown): { rotulo: string; tom: Tom } {
  const s = String(status ?? "");
  if (s === "ENVIADO") return { rotulo: "Publicada", tom: "ok" };
  if (s === "PENDENTE") return { rotulo: "Aguardando", tom: "alerta" };
  if (s === "ERRO") {
    if (String(erro ?? "").includes("ignorada")) return { rotulo: "Ignorada", tom: "neutro" };
    return { rotulo: "Precisa de atenção", tom: "erro" };
  }
  return { rotulo: s || "—", tom: "neutro" };
}

/** status da entrega (tabela entregas) → produto. */
export function statusEntrega(status: unknown): { rotulo: string; tom: Tom } {
  const s = String(status ?? "");
  if (s === "enviada") return { rotulo: "Publicada", tom: "ok" };
  if (s === "falhou") return { rotulo: "Falhou", tom: "erro" };
  if (s === "enviando") return { rotulo: "Enviando", tom: "alerta" };
  return { rotulo: s || "—", tom: "neutro" };
}

/** origem da oferta → produto ("clone" é termo interno). */
export function origemOferta(origem: unknown): string {
  const o = String(origem ?? "");
  if (o === "clone") return "Monitoramento";
  if (o === "busca") return "Busca automática";
  return o || "—";
}

/** Motivo de erro do motor → frase legível (sem stack/jargão). */
export function motivoLegivel(erro: unknown): string {
  const e = String(erro ?? "").trim();
  if (!e) return "";
  if (e.includes("ignorada")) return "Ignorada por você";
  const curto = e.length > 90 ? `${e.slice(0, 89)}…` : e;
  return curto;
}
