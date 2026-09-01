/**
 * Formatação e tradução para linguagem de produto (pt-BR).
 * Puro (sem imports de servidor) — usável em Server e Client Components.
 *
 * Regra do redesign: conversões acontecem AQUI, na borda da UI. O banco e o
 * motor continuam com os formatos internos (hora decimal, status em caps,
 * ISO local com offset) — nenhum contrato muda.
 */

export const FUSO = "America/Sao_Paulo";

/** "2026-08-22" no fuso da operação. */
export function hojeISO(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: FUSO });
}

/** Epoch ms — helper para Server Components (regra de pureza do lint). */
export function agoraMs(): number {
  return Date.now();
}

/**
 * "2026-08-22T15:47:03" — agora no fuso da OPERAÇÃO, sem sufixo de fuso.
 * O motor grava timestamps locais; comparações de fila usam este formato,
 * não o UTC (3h de diferença).
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

/**
 * "08:45" → 8.75 (gravação no contrato do motor).
 * Entrada vazia/malformada → NaN — quem chama DEVE validar
 * (Number.isFinite) antes de gravar; um campo de hora limpo jamais pode
 * virar meia-noite silenciosamente.
 */
export function hhmmParaDecimal(t: string): number {
  const m = /^(\d{1,2}):(\d{2})$/.exec(t.trim());
  if (!m) return NaN;
  return Number(m[1]) + Number(m[2]) / 60;
}

/** Pega "HH:MM" de um timestamp ISO local do motor (sem conversão de fuso). */
export function horaDe(iso: unknown): string {
  const s = String(iso ?? "");
  return s.length >= 16 ? s.slice(11, 16) : "—";
}

/* cache diário barato para dataCurta (chamada por linha em listas) */
let _diaCache = { chave: 0, hoje: "", ontem: "" };
function diasDeReferencia() {
  const chave = Math.floor(Date.now() / 60_000); // renova a cada minuto
  if (_diaCache.chave !== chave) {
    _diaCache = {
      chave,
      hoje: hojeISO(),
      ontem: new Date(Date.now() - 864e5).toLocaleDateString("sv-SE", { timeZone: FUSO }),
    };
  }
  return _diaCache;
}

/**
 * Data curta humana: "Hoje, 13:32" · "Ontem, 09:10" · "22/08 às 13:32".
 * Timestamps do motor são ISO no horário local da operação; comparação
 * textual do dia evita conversões de fuso indevidas.
 */
export function dataCurta(iso: unknown): string {
  const s = String(iso ?? "");
  if (s.length < 16) return "—";
  const dia = s.slice(0, 10);
  const hora = s.slice(11, 16);
  const ref = diasDeReferencia();
  if (dia === ref.hoje) return `Hoje, ${hora}`;
  if (dia === ref.ontem) return `Ontem, ${hora}`;
  return `${dia.slice(8, 10)}/${dia.slice(5, 7)} às ${hora}`;
}

/** "22/08" a partir de "2026-08-22". */
export function diaCurto(isoDia: unknown): string {
  const s = String(isoDia ?? "");
  return s.length >= 10 ? `${s.slice(8, 10)}/${s.slice(5, 7)}` : "—";
}

/* ── Saúde da automação (batida de vida) ───────────────────────────── */

/**
 * Uma iteração do ciclo da automação pode passar de 90s durante coletas;
 * 5 minutos evita alarme falso sem esconder parada real (D21).
 */
export const LIMITE_BATIDA_MS = 5 * 60_000;

/** true = a automação deu sinal de vida dentro do limite. */
export function batidaViva(valor: unknown, agora: number): boolean {
  const t = new Date(String(valor ?? "")).getTime();
  return Number.isFinite(t) && agora - t < LIMITE_BATIDA_MS;
}

/* ── Tradução de status/origem (banco → produto) ───────────────────── */

export type Tom = "ok" | "erro" | "alerta" | "neutro" | "info";

/** Marca interna que o painel grava ao ignorar uma oferta (D11). */
export const MARCA_IGNORADA = "ignorada";

/** Condição SQL de "precisa de atenção": ERRO real, não ignorada. */
export const SQL_ATENCAO = `status_envio='ERRO' AND erro NOT LIKE '%${MARCA_IGNORADA}%'`;
/** Condição SQL de "ignorada pelo usuário". */
export const SQL_IGNORADA = `status_envio='ERRO' AND erro LIKE '%${MARCA_IGNORADA}%'`;

/** status_envio da oferta → rótulo e tom de produto. */
export function statusOferta(status: unknown, erro?: unknown): { rotulo: string; tom: Tom } {
  const s = String(status ?? "");
  if (s === "ENVIADO") return { rotulo: "Publicada", tom: "ok" };
  if (s === "PENDENTE") return { rotulo: "Aguardando", tom: "alerta" };
  if (s === "ERRO") {
    if (String(erro ?? "").includes(MARCA_IGNORADA)) return { rotulo: "Ignorada", tom: "neutro" };
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

/**
 * Motivo de erro do motor → frase legível. O motor grava payloads crus
 * (códigos HTTP, corpo de resposta do provedor); nada disso pode vazar
 * para a experiência comum — na dúvida, frase genérica honesta.
 */
export function motivoLegivel(erro: unknown): string {
  const e = String(erro ?? "").trim();
  if (!e) return "";
  if (e.includes(MARCA_IGNORADA)) return "Ignorada por você";
  const baixo = e.toLowerCase();
  if (baixo.includes("desconect")) return "WhatsApp desconectado no momento do envio";
  if (/(https?:|uazapi|http [0-9]|traceback|exception|json|\{|\}|<)/i.test(e)) {
    return "Falha técnica no envio — nova tentativa automática";
  }
  return e.length > 90 ? `${e.slice(0, 89)}…` : e;
}
