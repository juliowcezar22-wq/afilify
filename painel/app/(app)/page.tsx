import { obterBanco, todas, uma } from "@/lib/dados";

export const dynamic = "force-dynamic";

const n = (v: unknown) => Number(v ?? 0);

async function contar(cond: string, params: unknown[] = []) {
  return n((await uma(`SELECT COUNT(*) AS n FROM ofertas WHERE ${cond}`, params))?.n);
}

function Carta({ titulo, valor, tom }: { titulo: string; valor: string; tom?: "ok" | "erro" }) {
  return (
    <div className="rounded-xl border border-linha bg-carta p-5">
      <p className="text-xs uppercase tracking-wider text-tinta2">{titulo}</p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${
        tom === "ok" ? "text-acento" : tom === "erro" ? "text-erro" : ""}`}>{valor}</p>
    </div>
  );
}

export default async function Dashboard() {
  const banco = obterBanco();
  if (!banco) {
    return (
      <div className="mx-auto max-w-5xl">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <div className="mt-8 rounded-xl border border-linha bg-carta p-6 text-sm text-tinta2">
          <p className="font-medium text-alerta">Banco não configurado.</p>
          <p className="mt-2">Defina <code className="text-tinta">SQLITE_PATH</code> (operação
          local) ou <code className="text-tinta">DATABASE_URL</code> (Postgres).</p>
        </div>
      </div>
    );
  }

  const hoje = new Date().toLocaleDateString("sv-SE",
    { timeZone: "America/Sao_Paulo" });                       // AAAA-MM-DD
  const [capturadas, publicadas, fila, erros] = await Promise.all([
    contar("criado_em LIKE ?", [`${hoje}%`]),
    contar("status_envio='ENVIADO' AND enviado_em LIKE ?", [`${hoje}%`]),
    contar("status_envio='PENDENTE' AND link_afiliado != ''"),
    contar("status_envio='ERRO'"),
  ]);

  const porPerfil = await todas(
    `SELECT perfil,
            SUM(CASE WHEN status_envio='ENVIADO' AND enviado_em LIKE ? THEN 1 ELSE 0 END) AS hoje,
            SUM(CASE WHEN status_envio='PENDENTE' AND link_afiliado != '' THEN 1 ELSE 0 END) AS fila
     FROM ofertas GROUP BY perfil ORDER BY perfil`, [`${hoje}%`]);

  const batidas = await todas(
    "SELECT chave, valor FROM estado WHERE chave LIKE '%:heartbeat'");
  const agora = Date.now();
  const workers = batidas.map((b) => ({
    perfil: String(b.chave).replace(":heartbeat", ""),
    online: agora - new Date(String(b.valor)).getTime() < 90_000,
  }));

  const ultimas = await todas(
    `SELECT nome, marca, desconto_pct, enviado_em, origem FROM ofertas
     WHERE status_envio='ENVIADO' ORDER BY enviado_em DESC LIMIT 8`);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <p className="mt-1 text-sm text-tinta2">
        Operação ao vivo · banco {banco.motor === "sqlite" ? "SQLite (local)" : "Postgres"}
      </p>

      <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Carta titulo="Capturadas hoje" valor={String(capturadas)} />
        <Carta titulo="Publicadas hoje" valor={String(publicadas)} tom="ok" />
        <Carta titulo="Na fila" valor={String(fila)} />
        <Carta titulo="Com erro" valor={String(erros)} tom={erros > 0 ? "erro" : undefined} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-linha bg-carta p-5">
          <p className="text-xs uppercase tracking-wider text-tinta2">Saúde da operação</p>
          <ul className="mt-3 grid gap-2 text-sm">
            {workers.length === 0 && (
              <li className="text-tinta2">nenhum worker deu sinal ainda</li>
            )}
            {workers.map((w) => (
              <li key={w.perfil} className="flex items-center gap-2">
                <span className={`inline-block h-2 w-2 rounded-full ${
                  w.online ? "bg-ok" : "bg-erro"}`} />
                <span>Worker · {w.perfil}</span>
                <span className="ml-auto text-xs text-tinta2">
                  {w.online ? "online" : "sem sinal há +90s"}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs uppercase tracking-wider text-tinta2">Por projeto</p>
          <ul className="mt-2 grid gap-1 text-sm">
            {porPerfil.map((p) => (
              <li key={String(p.perfil)} className="flex justify-between">
                <span>{String(p.perfil)}</span>
                <span className="tabular-nums text-tinta2">
                  {n(p.hoje)} hoje · {n(p.fila)} na fila</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-linha bg-carta p-5">
          <p className="text-xs uppercase tracking-wider text-tinta2">Últimas publicadas</p>
          <ul className="mt-3 grid gap-2 text-sm">
            {ultimas.map((o, i) => (
              <li key={i} className="flex items-baseline gap-2">
                <span className="text-xs tabular-nums text-tinta2">
                  {String(o.enviado_em ?? "").slice(11, 16)}</span>
                <span className="truncate">{String(o.nome)}</span>
                <span className="ml-auto shrink-0 text-xs text-acento">
                  −{n(o.desconto_pct)}%</span>
                {String(o.origem) === "clone" && (
                  <span className="shrink-0 rounded-full bg-carta2 px-2 text-[10px] text-tinta2">
                    clone</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
