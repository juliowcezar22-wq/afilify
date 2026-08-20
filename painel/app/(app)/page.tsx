import { sql } from "drizzle-orm";
import { obterDb } from "@/lib/db";

export const dynamic = "force-dynamic";

type Metricas = {
  capturadasHoje: number; enviadasHoje: number; fila: number;
  erros24h: number; total: number;
};

async function carregar(): Promise<Metricas | null> {
  const db = obterDb();
  if (!db) return null;
  const hoje = new Date().toISOString().slice(0, 10);
  try {
    const q = async (cond: string) =>
      Number((await db.execute(
        sql.raw(`SELECT COUNT(*) AS n FROM ofertas WHERE ${cond}`)))[0]?.n ?? 0);
    return {
      capturadasHoje: await q(`criado_em LIKE '${hoje}%'`),
      enviadasHoje: await q(`status_envio='ENVIADO' AND enviado_em LIKE '${hoje}%'`),
      fila: await q(`status_envio='PENDENTE' AND link_afiliado != ''`),
      erros24h: await q(`status_envio='ERRO'`),
      total: await q(`1=1`),
    };
  } catch { return null; }
}

function Carta({ titulo, valor, tom }: { titulo: string; valor: string; tom?: "ok" | "erro" }) {
  return (
    <div className="rounded-xl border border-linha bg-carta p-5">
      <p className="text-xs uppercase tracking-wider text-tinta2">{titulo}</p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${
        tom === "ok" ? "text-acento" : tom === "erro" ? "text-erro" : ""}`}>
        {valor}
      </p>
    </div>
  );
}

export default async function Dashboard() {
  const m = await carregar();
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <p className="mt-1 text-sm text-tinta2">Visão geral da operação</p>

      {!m ? (
        <div className="mt-8 rounded-xl border border-linha bg-carta p-6 text-sm text-tinta2">
          <p className="font-medium text-alerta">Banco ainda não conectado.</p>
          <p className="mt-2">
            O painel está no ar, mas <code className="text-tinta">DATABASE_URL</code> não
            aponta para o Postgres da operação. Assim que o cutover da Fase 2
            acontecer, estes números acendem sozinhos.
          </p>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Carta titulo="Capturadas hoje" valor={String(m.capturadasHoje)} />
          <Carta titulo="Publicadas hoje" valor={String(m.enviadasHoje)} tom="ok" />
          <Carta titulo="Na fila" valor={String(m.fila)} />
          <Carta titulo="Com erro" valor={String(m.erros24h)}
            tom={m.erros24h > 0 ? "erro" : undefined} />
        </div>
      )}

      <div className="mt-8 rounded-xl border border-linha bg-carta p-5">
        <p className="text-xs uppercase tracking-wider text-tinta2">Saúde da operação</p>
        <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          {[
            ["Postgres", m ? "conectado" : "aguardando cutover"],
            ["Worker (motor Python)", "heartbeat na Fase 3"],
            ["WhatsApp (uazapi)", "heartbeat na Fase 3"],
            ["Clonador", "heartbeat na Fase 3"],
          ].map(([nome, estado]) => (
            <li key={nome} className="flex items-center gap-2">
              <span className={`inline-block h-2 w-2 rounded-full ${
                estado === "conectado" ? "bg-ok" : "bg-tinta2/40"}`} />
              <span>{nome}</span>
              <span className="ml-auto text-xs text-tinta2">{estado}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
