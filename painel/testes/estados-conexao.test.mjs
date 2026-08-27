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
