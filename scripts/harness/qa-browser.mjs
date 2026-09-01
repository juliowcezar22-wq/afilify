/**
 * QA de navegador — console, rede e layout, nas rotas do fluxo comum.
 *
 * Usa o Chrome já instalado por CDP, sem driver adicional: o objetivo é
 * verificar o que o usuário veria, não montar infraestrutura de teste.
 *
 *   node scripts/harness/qa-browser.mjs <base> <cookie>
 *
 * Falha (saída 1) quando aparece erro de console, requisição quebrada ou
 * a página rola horizontalmente numa largura de celular.
 */
import { spawn } from "node:child_process";
import { setTimeout as espera } from "node:timers/promises";

const BASE = process.argv[2] ?? "http://localhost:3105";
const COOKIE = process.argv[3] ?? "";
const ROTAS = [
  "/", "/ofertas", "/publicacoes", "/projetos", "/fontes",
  "/destinos", "/mensagens", "/ritmo", "/conexoes", "/desempenho",
  "/configuracoes", "/ajuda",
];
const LARGURAS = [1440, 768, 390];
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORTA = 9333;

const chrome = spawn(CHROME, [
  `--remote-debugging-port=${PORTA}`,
  "--headless=new",
  "--no-first-run",
  "--disable-gpu",
  "--user-data-dir=/tmp/afilify-qa-chrome",
]);
process.on("exit", () => chrome.kill());

async function alvo() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORTA}/json/new?about:blank`, { method: "PUT" });
      if (r.ok) return r.json();
    } catch {
      /* o navegador ainda está subindo */
    }
    await espera(250);
  }
  throw new Error("o navegador não respondeu");
}

const aba = await alvo();
const ws = new WebSocket(aba.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));

let seq = 0;
const pendentes = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pendentes.has(m.id)) {
    pendentes.get(m.id)(m);
    pendentes.delete(m.id);
  } else if (m.method) eventos.push(m);
});
let eventos = [];

const cmd = (method, params = {}) =>
  new Promise((resolve) => {
    const id = ++seq;
    pendentes.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });

await cmd("Page.enable");
await cmd("Runtime.enable");
await cmd("Network.enable");
if (COOKIE) {
  const [nome, valor] = COOKIE.split("=");
  await cmd("Network.setCookie", { name: nome, value: valor, url: BASE, path: "/" });
}

const problemas = [];

for (const largura of LARGURAS) {
  await cmd("Emulation.setDeviceMetricsOverride", {
    width: largura, height: 900, deviceScaleFactor: 1, mobile: largura < 500,
  });
  for (const rota of ROTAS) {
    eventos = [];
    await cmd("Page.navigate", { url: BASE + rota });
    await espera(1200);

    const erros = eventos
      .filter((e) => e.method === "Runtime.consoleAPICalled" && e.params.type === "error")
      .map((e) => (e.params.args?.[0]?.value ?? "erro no console"));
    const excecoes = eventos
      .filter((e) => e.method === "Runtime.exceptionThrown")
      .map((e) => e.params.exceptionDetails?.text ?? "exceção");
    const rede = eventos
      .filter((e) => e.method === "Network.responseReceived" && e.params.response.status >= 400)
      .map((e) => `${e.params.response.status} ${e.params.response.url}`);

    const { result } = await cmd("Runtime.evaluate", {
      expression: `JSON.stringify({
        rolagem: document.documentElement.scrollWidth > window.innerWidth + 1,
        largura: document.documentElement.scrollWidth,
        janela: window.innerWidth
      })`,
      returnByValue: true,
    });
    const layout = JSON.parse(result.result.value);

    for (const e of [...erros, ...excecoes]) problemas.push(`${largura}px ${rota}: console — ${e}`);
    for (const r of rede) problemas.push(`${largura}px ${rota}: rede — ${r}`);
    if (layout.rolagem)
      problemas.push(
        `${largura}px ${rota}: rola de lado (${layout.largura}px de conteúdo em ${layout.janela}px)`,
      );
  }
  console.log(`✓ ${largura}px — ${ROTAS.length} rotas verificadas`);
}

ws.close();
chrome.kill();

if (problemas.length) {
  console.log("\n✗ QA de navegador: problemas encontrados");
  for (const p of problemas) console.log("  ·", p);
  process.exit(1);
}
console.log("\n✓ QA de navegador: console limpo, rede sem erro, nenhuma rota rola de lado");
