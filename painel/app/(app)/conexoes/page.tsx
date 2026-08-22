import { stat } from "node:fs/promises";
import path from "node:path";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { DetalhesTecnicos } from "@/components/ui/detalhes-tecnicos";
import { agoraMs, type Tom } from "@/lib/formatos";

export const dynamic = "force-dynamic";

/* Estados de conexão em linguagem de produto. A arquitetura é uma LISTA de
   contas por plataforma — pronta para múltiplas contas quando o backend
   suportar (hoje: no máximo 1 por plataforma, vinda do ambiente). */
type EstadoConexao = "conectado" | "conectando" | "atencao" | "desconectado" | "ausente";

type Conta = {
  nome: string;
  estado: EstadoConexao;
  resumo: string;
  tecnicos: Array<[string, string]>;
};

type Plataforma = {
  plataforma: string;
  contas: Conta[];
};

const APRESENTACAO: Record<EstadoConexao, { rotulo: string; tom: Tom }> = {
  conectado: { rotulo: "Conectado", tom: "ok" },
  conectando: { rotulo: "Conectando…", tom: "alerta" },
  atencao: { rotulo: "Precisa de atenção", tom: "alerta" },
  desconectado: { rotulo: "Desconectado", tom: "erro" },
  ausente: { rotulo: "Não configurada", tom: "neutro" },
};

async function contaWhatsApp(): Promise<Conta[]> {
  const url = process.env.UAZAPI_URL,
    token = process.env.UAZAPI_TOKEN;
  if (!url || !token) return [];
  try {
    const r = await fetch(`${url}/instance/status`, {
      headers: { token },
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    const d = await r.json();
    const i = d.instance ?? {};
    const bruto = String(i.status ?? "");
    const estado: EstadoConexao =
      bruto === "connected" ? "conectado" : bruto === "connecting" ? "conectando" : "desconectado";
    return [
      {
        nome: String(i.profileName ?? i.name ?? "Conta principal"),
        estado,
        resumo:
          estado === "conectado"
            ? "Pronta para publicar nos seus grupos."
            : estado === "conectando"
              ? "Estabelecendo a conexão — isso leva alguns instantes."
              : "Reconecte para voltar a publicar nos seus grupos.",
        tecnicos: [
          ["instância", String(i.name ?? "—")],
          ["status", bruto || "—"],
        ],
      },
    ];
  } catch {
    return [
      {
        nome: "Conta principal",
        estado: "desconectado",
        resumo: "O serviço de WhatsApp não respondeu — tente novamente em instantes.",
        tecnicos: [["status", "sem resposta do provedor"]],
      },
    ];
  }
}

async function contaMercadoLivre(): Promise<Conta[]> {
  const caminho = process.env.ML_COOKIE_PATH;
  if (!caminho) return [];
  const renovacao: Array<[string, string]> = [
    ["renovar sessão", "Linkbuilder → F12 → Cookie → arquivo .mlcookie"], // harness-ok
    ["arquivo", caminho],
  ];
  try {
    const s = await stat(path.resolve(process.cwd(), caminho));
    const dias = (agoraMs() - s.mtimeMs) / 86_400_000;
    const restam = Math.max(0, 30 - dias);
    const estado: EstadoConexao = dias > 28 ? "desconectado" : dias > 21 ? "atencao" : "conectado";
    return [
      {
        nome: "Conta principal",
        estado,
        resumo:
          estado === "conectado"
            ? `Sessão ativa — vence em aproximadamente ${restam.toFixed(0)} dia(s).`
            : estado === "atencao"
              ? `A sessão vence em aproximadamente ${restam.toFixed(0)} dia(s) — renove para não interromper a operação.`
              : "A sessão expirou — renove para a busca de ofertas voltar a funcionar.",
        tecnicos: renovacao,
      },
    ];
  } catch {
    return [
      {
        nome: "Conta principal",
        estado: "desconectado",
        resumo: "A sessão não foi encontrada — renove para conectar.",
        tecnicos: renovacao,
      },
    ];
  }
}

function contaShopee(): Conta[] {
  const id = process.env.SHOPEE_APP_ID,
    secreto = process.env.SHOPEE_SECRET;
  if (!id || !secreto) return [];
  return [
    {
      nome: "Conta principal",
      estado: "conectado",
      resumo: "Conexão oficial — credencial permanente, sem renovação manual.",
      tecnicos: [["identificador do app", `…${id.slice(-4)}`]],
    },
  ];
}

const FUTURAS = ["Amazon", "Magalu", "Shein", "TikTok Shop", "Telegram"];

export default async function Conexoes() {
  const [wa, ml] = await Promise.all([contaWhatsApp(), contaMercadoLivre()]);
  const plataformas: Plataforma[] = [
    { plataforma: "WhatsApp", contas: wa },
    { plataforma: "Mercado Livre", contas: ml },
    { plataforma: "Shopee", contas: contaShopee() },
  ];

  return (
    <div className="mx-auto max-w-4xl">
      <CabecalhoPagina
        titulo="Conexões"
        descricao="As contas que você conectou à Afilify — e se elas estão funcionando."
      />

      <div className="mt-6 grid grid-cols-1 gap-4">
        {plataformas.map(({ plataforma, contas }) => (
          <Cartao key={plataforma} titulo={plataforma}>
            {contas.length === 0 ? (
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-tinta2">Nenhuma conta conectada.</p>
                <Selo tom="neutro">{APRESENTACAO.ausente.rotulo}</Selo>
              </div>
            ) : (
              <ul className="grid grid-cols-1 gap-4">
                {contas.map((c) => {
                  const ap = APRESENTACAO[c.estado];
                  return (
                    <li key={c.nome}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium">{c.nome}</p>
                        <Selo tom={ap.tom}>{ap.rotulo}</Selo>
                      </div>
                      <p className="mt-1 text-sm text-tinta2">{c.resumo}</p>
                      <DetalhesTecnicos itens={c.tecnicos} />
                    </li>
                  );
                })}
              </ul>
            )}
          </Cartao>
        ))}

        <Cartao titulo="Em breve">
          <p className="mb-3 text-sm text-tinta2">
            Novas plataformas chegam à Afilify nas próximas versões:
          </p>
          <ul className="flex flex-wrap gap-2" aria-label="Plataformas em desenvolvimento">
            {FUTURAS.map((p) => (
              <li
                key={p}
                className="rounded-full border border-linha px-3 py-1 text-xs text-tinta3"
              >
                {p}
              </li>
            ))}
          </ul>
        </Cartao>
      </div>
    </div>
  );
}
