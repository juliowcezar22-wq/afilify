import Link from "next/link";
import { todas } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { nomeDoProjeto } from "@/lib/projetos";
import { gruposDaConta, conexaoConfigurada } from "@/lib/whatsapp";
import {
  agoraMs,
  batidaViva,
  dataCurta,
  horaDecimalParaHHMM,
  reais,
  statusOferta,
} from "@/lib/formatos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { FormMonitoramento } from "./form";
import { EditorBusca } from "./editor-busca";
import * as fontes from "@/lib/fontes";
import { listarAutomacoes, listarProjetos } from "@/lib/projetos-repo";

export const dynamic = "force-dynamic";

/** De onde as ofertas surgem: busca automática + monitoramento de grupos. */
export default async function Fontes() {
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);

  // Fontes de busca configuráveis, das automações do projeto ativo. O bloco
  // legado (abaixo) continua servindo os projetos que ainda vêm de arquivo.
  const fontesDeBusca = await (async () => {
    try {
      const projetos = await listarProjetos();
      const saida: Array<{ id: string; projeto: string; automacao: string; fonte: fontes.Fonte }> = [];
      for (const proj of projetos) {
        for (const auto of await listarAutomacoes(proj.id)) {
          for (const f of await fontes.listar(auto.id)) {
            if (f.tipo === "busca")
              saida.push({ id: f.id, projeto: proj.nome, automacao: auto.nome, fonte: f });
          }
        }
      }
      return saida;
    } catch {
      return [];
    }
  })();

  const [cfgClonador, cfgRitmo, grupos, oportunidades, batidas] = await Promise.all([
    todas(`SELECT perfil, valor FROM config WHERE chave='clonador'${proj.sql} ORDER BY perfil`, proj.params),
    todas(`SELECT perfil, valor FROM config WHERE chave='ritmo'${proj.sql} ORDER BY perfil`, proj.params),
    gruposDaConta(),
    todas(
      `SELECT nome, preco_promocional, desconto_pct, rival_preco, status_envio, erro, criado_em
       FROM ofertas WHERE origem='clone'${proj.sql} ORDER BY criado_em DESC LIMIT 10`,
      proj.params,
    ),
    todas("SELECT chave, valor FROM estado WHERE chave LIKE '%:heartbeat'"),
  ]);

  const horasDe = (l: Record<string, unknown>): number[] => {
    try {
      return (JSON.parse(String(l.valor)).busca_horas ?? []) as number[];
    } catch {
      return [];
    }
  };

  // busca "Ativa" só quando a automação dá sinal de vida de verdade
  const agora = agoraMs();
  const viva = new Map(
    batidas.map((b) => [
      String(b.chave).replace(":heartbeat", ""),
      batidaViva(b.valor, agora),
    ]),
  );

  const semConexao = !conexaoConfigurada() || grupos.length === 0;

  return (
    <div className="mx-auto max-w-4xl">
      <CabecalhoPagina
        titulo="Fontes"
        descricao="De onde as suas ofertas surgem: busca automática nas lojas e monitoramento de grupos."
      />

      {/* Fontes configuráveis: o usuário diz o que procurar e testa antes de ligar. */}
      {fontesDeBusca.length > 0 && (
        <div className="mt-6 grid grid-cols-1 gap-4">
          {fontesDeBusca.map((f) => (
            <div key={f.id}>
              <p className="mb-2 text-xs uppercase tracking-wider text-tinta2">
                {f.projeto} · {f.automacao}
              </p>
              <EditorBusca fonteId={f.id} inicial={f.fonte.criterios} ativa={f.fonte.ativa} />
            </div>
          ))}
        </div>
      )}

      {/* Busca automática dos projetos que ainda vêm de arquivo */}
      <Cartao className="mt-6" titulo="Busca automática">
        {cfgRitmo.length === 0 ? (
          <EstadoVazio
            compacto
            titulo="Nenhum projeto configurado ainda"
            descricao="Quando o seu projeto estiver ativo, a busca automática aparece aqui."
          />
        ) : (
          <ul className="grid grid-cols-1 gap-3">
            {cfgRitmo.map((l) => {
              const slug = String(l.perfil);
              const horas = horasDe(l);
              return (
                <li key={slug} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                  <span className="font-medium">{nomeDoProjeto(slug)}</span>
                  {viva.get(slug) ? (
                    <Selo tom="ok">Ativa</Selo>
                  ) : (
                    <Selo tom="alerta">Sem sinal no momento</Selo>
                  )}
                  <span className="text-tinta2">
                    procura promoções{" "}
                    {horas.length > 0
                      ? `às ${horas.map((h) => horaDecimalParaHHMM(h)).join(", ")}`
                      : "ao longo do dia"}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
        <p className="mt-3 text-xs text-tinta3">
          Os horários de busca fazem parte do ritmo do projeto —{" "}
          <Link href="/ritmo" className="text-tinta2 underline hover:text-tinta">
            ajustar em Ritmo &amp; Regras
          </Link>
          .
        </p>
      </Cartao>

      {/* Monitoramento */}
      <div className="mt-4 grid grid-cols-1 gap-4">
        <Cartao titulo="Monitoramento de grupos">
          <p className="mb-4 text-sm text-tinta2">
            A Afilify acompanha grupos escolhidos por você, identifica o produto
            anunciado e traz a oferta para a SUA fila com o SEU link — a mensagem
            é sempre reconstruída no seu formato.
          </p>
          {semConexao && (
            <div className="mb-4">
              <EstadoVazio
                compacto
                titulo="WhatsApp sem conexão no momento"
                descricao="Conecte seu WhatsApp para listar grupos pelo nome e adicionar novos ao monitoramento."
                acao={
                  <Link href="/conexoes" className="text-sm text-acento hover:underline">
                    Ver conexões →
                  </Link>
                }
              />
            </div>
          )}
          {cfgClonador.length === 0 ? (
            <EstadoVazio
              compacto
              titulo="Nenhum projeto com monitoramento ainda"
            />
          ) : (
            <div className="grid grid-cols-1 gap-6">
              {cfgClonador.map((c) => {
                let cfg = {};
                try {
                  cfg = JSON.parse(String(c.valor));
                } catch {}
                return (
                  <FormMonitoramento
                    key={String(c.perfil)}
                    perfil={String(c.perfil)}
                    nomeProjeto={nomeDoProjeto(c.perfil)}
                    inicial={cfg}
                    disponiveis={grupos}
                  />
                );
              })}
            </div>
          )}
        </Cartao>

        <Cartao titulo="Últimas oportunidades do monitoramento">
          {oportunidades.length === 0 ? (
            <EstadoVazio
              compacto
              titulo="Nenhuma oportunidade ainda"
              descricao="Quando um grupo monitorado anunciar um produto que vale a pena, ele aparece aqui."
            />
          ) : (
            <ul className="grid grid-cols-1 gap-2.5 text-sm">
              {oportunidades.map((o, i) => {
                const st = statusOferta(o.status_envio, o.erro);
                return (
                  <li
                    key={i}
                    className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-x-3"
                  >
                    <span className="min-w-0">
                      <span className="block truncate">{String(o.nome)}</span>
                      <span className="text-xs text-tinta3">
                        {o.rival_preco != null && <>visto por {reais(o.rival_preco)} · </>}
                        no seu link por {reais(o.preco_promocional)} (−
                        {Number(o.desconto_pct ?? 0)}%)
                      </span>
                    </span>
                    <Selo tom={st.tom}>{st.rotulo}</Selo>
                    <span className="whitespace-nowrap text-xs tabular-nums text-tinta3">
                      {dataCurta(o.criado_em)}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </Cartao>
      </div>
    </div>
  );
}
