import { stat } from "node:fs/promises";
import path from "node:path";

export const dynamic = "force-dynamic";

type Estado = "ok" | "alerta" | "erro" | "ausente";

function Cartao({ nome, estado, detalhes }:
  { nome: string; estado: Estado; detalhes: Array<[string, string]> }) {
  const cor = { ok: "bg-ok", alerta: "bg-alerta", erro: "bg-erro", ausente: "bg-tinta2/40" }[estado];
  const rotulo = { ok: "conectado", alerta: "atenção", erro: "erro", ausente: "não configurado" }[estado];
  return (
    <div className="rounded-xl border border-linha bg-carta p-5">
      <div className="flex items-center gap-2">
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${cor}`} />
        <p className="font-medium">{nome}</p>
        <span className="ml-auto text-xs text-tinta2">{rotulo}</span>
      </div>
      <dl className="mt-4 grid gap-1.5 text-sm">
        {detalhes.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4">
            <dt className="text-tinta2">{k}</dt>
            <dd className="truncate text-right tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

async function cookieML() {
  const caminho = process.env.ML_COOKIE_PATH;
  if (!caminho) return { estado: "ausente" as Estado, detalhes: [["cookie", "caminho não configurado"]] as Array<[string, string]> };
  try {
    const s = await stat(path.resolve(process.cwd(), caminho));
    const dias = (Date.now() - s.mtimeMs) / 86_400_000;
    const restam = Math.max(0, 30 - dias);
    const estado: Estado = dias > 28 ? "erro" : dias > 21 ? "alerta" : "ok";
    return { estado, detalhes: [
      ["sessão renovada há", `${dias.toFixed(0)} dia(s)`],
      ["vence em aproximadamente", `${restam.toFixed(0)} dia(s)`],
      ["tag de afiliado", process.env.ML_AFFILIATE_TAG ?? "ceju…3443"],
      ["renovar", "Linkbuilder → F12 → Cookie → .mlcookie"],
    ] as Array<[string, string]> };
  } catch {
    return { estado: "erro" as Estado, detalhes: [["cookie", "arquivo .mlcookie não encontrado"]] as Array<[string, string]> };
  }
}

async function instanciaUazapi() {
  const url = process.env.UAZAPI_URL, token = process.env.UAZAPI_TOKEN;
  if (!url || !token) return { estado: "ausente" as Estado, detalhes: [["credenciais", "UAZAPI_* não configuradas"]] as Array<[string, string]> };
  try {
    const r = await fetch(`${url}/instance/status`, {
      headers: { token }, signal: AbortSignal.timeout(5000), cache: "no-store",
    });
    const d = await r.json();
    const i = d.instance ?? {};
    const conectado = i.status === "connected";
    return { estado: (conectado ? "ok" : "erro") as Estado, detalhes: [
      ["instância", String(i.name ?? "—")],
      ["status", String(i.status ?? "—")],
      ["perfil", String(i.profileName ?? "—")],
      ["token", "•••• (nunca exibido)"],
    ] as Array<[string, string]> };
  } catch {
    return { estado: "erro" as Estado, detalhes: [["status", "sem resposta da uazapi"]] as Array<[string, string]> };
  }
}

function shopee() {
  const id = process.env.SHOPEE_APP_ID, secreto = process.env.SHOPEE_SECRET;
  if (!id || !secreto) return { estado: "ausente" as Estado, detalhes: [["credenciais", "SHOPEE_* não configuradas"]] as Array<[string, string]> };
  return { estado: "ok" as Estado, detalhes: [
    ["app id", id],
    ["secret", "•••• (nunca exibido)"],
    ["tipo", "API oficial — credencial permanente, sem cookie"],
  ] as Array<[string, string]> };
}

export default async function Conexoes() {
  const [ml, ua] = await Promise.all([cookieML(), instanciaUazapi()]);
  const sh = shopee();
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold">Conexões</h1>
      <p className="mt-1 text-sm text-tinta2">Estado das integrações · segredos nunca aparecem aqui</p>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Cartao nome="Mercado Livre" estado={ml.estado} detalhes={ml.detalhes} />
        <Cartao nome="WhatsApp (uazapi)" estado={ua.estado} detalhes={ua.detalhes} />
        <Cartao nome="Shopee" estado={sh.estado} detalhes={sh.detalhes} />
      </div>
    </div>
  );
}
