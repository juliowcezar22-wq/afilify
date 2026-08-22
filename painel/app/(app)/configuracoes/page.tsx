import { todas } from "@/lib/dados";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { FormTracking } from "./tracking";

export const dynamic = "force-dynamic";

/** Configurações da CONTA — coisas globais. Regras de automação por
 *  projeto moram em Ritmo & Regras. */
export default async function Configuracoes() {
  const linhas = await todas(
    "SELECT perfil, valor FROM config WHERE chave = 'tracking' ORDER BY perfil",
  ).catch(() => []);
  const porPerfil = linhas.map((l) => {
    let cfg: { ativo?: boolean; base?: string } = {};
    try {
      cfg = JSON.parse(String(l.valor));
    } catch {}
    return { perfil: String(l.perfil), ativo: Boolean(cfg.ativo), base: cfg.base ?? "" };
  });

  return (
    <div className="mx-auto max-w-3xl">
      <CabecalhoPagina
        titulo="Configurações"
        descricao="Preferências da sua conta e do espaço de trabalho."
      />

      <div className="mt-6 grid grid-cols-1 gap-4">
        <Cartao titulo="Links inteligentes">
          <FormTracking inicial={porPerfil} />
        </Cartao>

        <Cartao titulo="Sessão">
          <p className="text-sm text-tinta2">
            Você está conectado ao painel da Afilify.
          </p>
          <form action="/api/sair" method="post" className="mt-3">
            <button className="rounded-lg border border-linha bg-carta2 px-4 py-2 text-sm font-semibold text-tinta hover:bg-carta3">
              Sair da conta
            </button>
          </form>
        </Cartao>

        <Cartao
          titulo="Equipe e assinatura"
          acao={<Selo tom="neutro" ponto={false}>Em breve</Selo>}
        >
          <p className="text-sm text-tinta2">
            Convites para a equipe, perfis de acesso e gestão da assinatura
            chegam nas próximas versões da Afilify.
          </p>
        </Cartao>
      </div>
    </div>
  );
}
