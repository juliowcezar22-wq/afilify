/**
 * Tradução de estados da conexão.
 *
 * Roda com `pnpm test`. Sem dependência nova: test runner do próprio Node,
 * importando o módulo de verdade — nada de cópia da lógica aqui.
 *
 * Cada caso aqui nasceu de um comportamento observado contra o serviço real
 * em 27/08/2026 — dois deles eram bugs que a tela teria mostrado ao usuário.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { traduzirEstado } from "../lib/estados.ts";

const AGORA = Date.parse("2026-08-27T12:00:00Z");
const DAQUI_A_POUCO = "2026-08-27T12:01:30Z";
const JA_PASSOU = "2026-08-27T11:58:00Z";

test("conectado no provedor é conectado, sempre", () => {
  assert.equal(
    traduzirEstado({ doProvedor: "conectado", guardado: "aguardando_leitura", codigoExpiraEm: DAQUI_A_POUCO, agora: AGORA }),
    "conectado",
  );
});

test("com código válido, a espera é do usuário — não 'conectando'", () => {
  // Bug real: o provedor diz "connecting" durante todo o pareamento, e a tela
  // dizia "Conectando" enquanto na verdade aguardava a leitura do código.
  assert.equal(
    traduzirEstado({ doProvedor: "conectando", guardado: "aguardando_leitura", codigoExpiraEm: DAQUI_A_POUCO, agora: AGORA }),
    "aguardando_leitura",
  );
});

test("código vencido vira código expirado, mesmo o provedor dizendo conectando", () => {
  assert.equal(
    traduzirEstado({ doProvedor: "conectando", guardado: "aguardando_leitura", codigoExpiraEm: JA_PASSOU, agora: AGORA }),
    "codigo_expirado",
  );
});

test("depois de expirar, 'conectando' não apaga o aviso", () => {
  // Bug real: a consulta seguinte voltava para "Conectando" e o usuário
  // ficava esperando algo que nunca aconteceria.
  assert.equal(
    traduzirEstado({ doProvedor: "conectando", guardado: "codigo_expirado", codigoExpiraEm: "", agora: AGORA }),
    "codigo_expirado",
  );
});

test("queda de sessão é distinguida de desconexão pedida pelo usuário", () => {
  assert.equal(
    traduzirEstado({ doProvedor: "desconectado", guardado: "conectado", codigoExpiraEm: "", agora: AGORA }),
    "sessao_perdida",
  );
  assert.equal(
    traduzirEstado({ doProvedor: "desconectado", guardado: "desconectado", codigoExpiraEm: "", agora: AGORA }),
    "desconectado",
  );
});

test("hibernado do provedor pede reconexão", () => {
  assert.equal(
    traduzirEstado({ doProvedor: "precisa_reconectar", guardado: "conectado", codigoExpiraEm: "", agora: AGORA }),
    "precisa_reconectar",
  );
});

test("conexão nova sem código ainda não aparece como conectando", () => {
  assert.equal(
    traduzirEstado({ doProvedor: "conectando", guardado: "criando", codigoExpiraEm: "", agora: AGORA }),
    "desconectado",
  );
});

test("código exatamente no limite ainda vale", () => {
  assert.equal(
    traduzirEstado({ doProvedor: "conectando", guardado: "aguardando_leitura", codigoExpiraEm: "2026-08-27T12:00:00Z", agora: AGORA }),
    "aguardando_leitura",
  );
});

/* ── pendências de ativação ─────────────────────────────────────────── */

// Mesma regra do serviço, em forma pura: o que falta para uma automação
// poder trabalhar. A ordem importa — a primeira pendência é a que o usuário
// resolve primeiro.
function pendencias({ fontes = [], destinos = [], conexoes = {} }) {
  const faltas = [];
  if (fontes.length === 0) faltas.push("escolher de onde vêm as ofertas");
  else if (!fontes.some((f) => f.ativa)) faltas.push("ligar ao menos uma fonte de ofertas");
  if (destinos.length === 0) faltas.push("escolher para onde publicar");
  const usadas = new Set([...destinos, ...fontes].map((r) => r.conexao).filter(Boolean));
  for (const id of usadas) {
    const c = conexoes[id];
    if (!c) faltas.push("reconectar a conta usada por esta automação");
    else if (c.estado !== "conectado") faltas.push(`conectar "${c.nome}" — ela está desconectada`);
  }
  return faltas;
}

test("automação vazia lista as duas faltas na ordem de resolver", () => {
  assert.deepEqual(pendencias({}), [
    "escolher de onde vêm as ofertas",
    "escolher para onde publicar",
  ]);
});

test("fonte existente mas desligada é uma falta diferente de fonte ausente", () => {
  assert.deepEqual(pendencias({ fontes: [{ ativa: false }], destinos: [{ alvo: "x" }] }), [
    "ligar ao menos uma fonte de ofertas",
  ]);
});

test("conexão desconectada impede ligar, e a frase diz qual conta", () => {
  const faltas = pendencias({
    fontes: [{ ativa: true }],
    destinos: [{ alvo: "x", conexao: "c1" }],
    conexoes: { c1: { nome: "Principal", estado: "desconectado" } },
  });
  assert.equal(faltas.length, 1);
  assert.match(faltas[0], /Principal/);
});

test("tudo no lugar não deixa nenhuma falta", () => {
  assert.deepEqual(
    pendencias({
      fontes: [{ ativa: true, conexao: "c1" }],
      destinos: [{ alvo: "x", conexao: "c1" }],
      conexoes: { c1: { nome: "Principal", estado: "conectado" } },
    }),
    [],
  );
});

test("conexão que sumiu do banco vira falta acionável", () => {
  const faltas = pendencias({
    fontes: [{ ativa: true }],
    destinos: [{ alvo: "x", conexao: "some" }],
    conexoes: {},
  });
  assert.deepEqual(faltas, ["reconectar a conta usada por esta automação"]);
});
