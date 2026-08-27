import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { SemDados } from "@/components/ui/sem-dados";
import { obterBanco, todas } from "@/lib/dados";
import * as limites from "@/lib/limites";
import * as conexoes from "@/lib/conexoes-servico";

export const dynamic = "force-dynamic";

/**
 * Área técnica — o que existe para diagnosticar, e não para operar.
 *
 * Fica fora da navegação comum de propósito: identificador de conta, estado
 * interno e registro cru não ajudam quem só quer publicar ofertas. Mas
 * quando algo dá errado, alguém precisa ver exatamente isso.
 */
export default async function Tecnico() {
  if (!obterBanco()) return <SemDados />;

  const [plano, uso, contas, comandos, execucoes] = await Promise.all([
    limites.doWorkspace(),
    limites.usoDoDia(),
    conexoes.listar().catch(() => []),
    todas(
      "SELECT tipo, estado, erro, criado_em FROM comandos ORDER BY criado_em DESC LIMIT 15",
    ).catch(() => []),
    todas(
      `SELECT resultado, encontradas, novas, motivo, iniciada_em
         FROM execucoes_fonte ORDER BY iniciada_em DESC LIMIT 15`,
    ).catch(() => []),
  ]);

  return (
    <div className="mx-auto max-w-4xl">
      <CabecalhoPagina
        titulo="Registro técnico"
        descricao="Para diagnóstico. Nada aqui é necessário para operar a Afilify no dia a dia."
      />

      <div className="mt-6 grid grid-cols-1 gap-4">
        <Cartao titulo="Limites da conta">
          <dl className="grid grid-cols-1 gap-1.5 text-sm md:grid-cols-2">
            {[
              ["Conexões", plano.conexoes],
              ["Projetos", plano.projetos],
              ["Automações", plano.automacoes],
              ["Publicações por dia", `${uso.publicacoes} de ${plano.publicacoesDia}`],
              ["Testes de busca por dia", `${uso.testes} de ${plano.testesBuscaDia}`],
              ["Envios por conta, por hora", plano.envriosPorConexaoHora],
            ].map(([rotulo, valor]) => (
              <div key={String(rotulo)} className="flex justify-between gap-4">
                <dt className="text-tinta2">{rotulo}</dt>
                <dd className="tabular-nums">{valor}</dd>
              </div>
            ))}
          </dl>
        </Cartao>

        <Cartao titulo="Contas conectadas">
          {contas.length === 0 ? (
            <p className="text-sm text-tinta2">Nenhuma conta conectada.</p>
          ) : (
            <ul className="grid grid-cols-1 gap-3 text-sm">
              {contas.map((c) => (
                <li key={c.id} className="grid grid-cols-1 gap-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="truncate">{c.nome}</span>
                    <Selo tom={c.precisaAtencao ? "erro" : "ok"}>{c.estado}</Selo>
                  </div>
                  <p className="break-all font-mono text-xs text-tinta3">
                    {c.tecnico.identificador || "—"}
                    {c.tecnico.motivoUltimaQueda ? ` · ${c.tecnico.motivoUltimaQueda}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Cartao>

        <Cartao titulo="Últimos pedidos ao motor">
          {comandos.length === 0 ? (
            <p className="text-sm text-tinta2">Nenhum pedido registrado.</p>
          ) : (
            <ul className="grid grid-cols-1 gap-1.5 font-mono text-xs">
              {comandos.map((c, i) => (
                <li key={i} className="flex flex-wrap justify-between gap-2">
                  <span>
                    {String(c.criado_em).slice(11, 19)} {String(c.tipo)}
                  </span>
                  <span className={String(c.estado) === "falhou" ? "text-erro" : "text-tinta2"}>
                    {String(c.estado)}
                    {c.erro ? ` · ${String(c.erro).slice(0, 60)}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Cartao>

        <Cartao titulo="Últimas coletas">
          {execucoes.length === 0 ? (
            <p className="text-sm text-tinta2">Nenhuma coleta registrada.</p>
          ) : (
            <ul className="grid grid-cols-1 gap-1.5 font-mono text-xs">
              {execucoes.map((e, i) => (
                <li key={i} className="flex flex-wrap justify-between gap-2">
                  <span>{String(e.iniciada_em).slice(0, 19).replace("T", " ")}</span>
                  <span className={String(e.resultado) === "falhou" ? "text-erro" : "text-tinta2"}>
                    {String(e.resultado)} · {String(e.encontradas)} encontradas, {String(e.novas)} novas
                    {e.motivo ? ` · ${String(e.motivo).slice(0, 50)}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      </div>
    </div>
  );
}
