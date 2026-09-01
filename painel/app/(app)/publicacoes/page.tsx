import { todas } from "@/lib/dados";
import * as operacaoNova from "@/lib/operacao";
import { listarProjetos as listarProjetosNovos } from "@/lib/projetos-repo";
import { Cartao as CartaoPub } from "@/components/ui/cartao";
import { Selo as SeloPub } from "@/components/ui/selo";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { nomeDoProjeto } from "@/lib/projetos";
import {
  agoraLocalISO,
  dataCurta,
  hojeISO,
  horaDe,
  horaDecimalParaHHMM,
  motivoLegivel,
  statusEntrega,
} from "@/lib/formatos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { EstadoVazio } from "@/components/ui/estado-vazio";

export const dynamic = "force-dynamic";

const n = (v: unknown) => Number(v ?? 0);

/** O que está aguardando, o que vem em seguida e o que já aconteceu. */
export default async function Publicacoes() {
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);
  const projEntrega = condicaoProjeto(ctx, "e.perfil");
  const hoje = hojeISO();
  // "agora" no fuso da operação — o motor grava timestamps locais (D6)
  const agora = agoraLocalISO();

  // uma leva só de consultas — todas independentes
  const [estado, enviadasLinhas, proximas, novasTentativas, recentes] = await Promise.all([
    todas(
      "SELECT chave, valor FROM estado WHERE chave LIKE '%:plano_do_dia' OR chave LIKE '%:proximo_envio'",
    ),
    todas(
      `SELECT perfil, COUNT(*) AS n FROM ofertas
       WHERE status_envio='ENVIADO' AND enviado_em LIKE ?${proj.sql} GROUP BY perfil`,
      [`${hoje}%`, ...proj.params],
    ),
    // ordem real de saída da automação: monitoramento tem prioridade
    todas(
      `SELECT mlb_id, nome, desconto_pct, origem, perfil FROM ofertas
       WHERE status_envio='PENDENTE' AND link_afiliado != ''
         AND (proxima_tentativa IS NULL OR proxima_tentativa <= ?)${proj.sql}
       ORDER BY CASE WHEN origem='clone' THEN 0 ELSE 1 END, criado_em DESC LIMIT 15`,
      [agora, ...proj.params],
    ),
    todas(
      `SELECT mlb_id, nome, proxima_tentativa, erro FROM ofertas
       WHERE status_envio='PENDENTE' AND proxima_tentativa > ?${proj.sql}
       ORDER BY proxima_tentativa LIMIT 10`,
      [agora, ...proj.params],
    ),
    todas(
      `SELECT e.mlb_id, e.status, e.atualizado_em, e.erro, o.nome
       FROM entregas e LEFT JOIN ofertas o ON o.mlb_id = e.mlb_id
       WHERE 1=1${projEntrega.sql}
       ORDER BY e.atualizado_em DESC LIMIT 20`,
      projEntrega.params,
    ),
  ]);

  // ritmo do dia por projeto — plano de OUTRO dia não é apresentado como
  // de hoje (o motor só reaproveita plano quando plano.data === hoje)
  const planos: Record<
    string,
    { data?: string; cota?: number; inicio?: number; fim?: number; proximo?: string }
  > = {};
  for (const e of estado) {
    const [slug, chave] = String(e.chave).split(":");
    if (ctx.ativo && slug !== ctx.ativo.slug) continue;
    planos[slug] ??= {};
    if (chave === "plano_do_dia") {
      try {
        Object.assign(planos[slug], JSON.parse(String(e.valor)));
      } catch {}
    } else {
      planos[slug].proximo = String(e.valor);
    }
  }
  for (const slug of Object.keys(planos)) {
    if (planos[slug].data && planos[slug].data !== hoje) {
      planos[slug] = { proximo: undefined }; // plano velho: sem cota/janela
    }
  }
  const enviadasHoje = Object.fromEntries(
    enviadasLinhas.map((r) => [String(r.perfil), n(r.n)]),
  );

  const varios = !ctx.ativo && Object.keys(planos).length > 1;


  // Publicações dos projetos criados na interface: uma linha por envio,
  // com destino e motivo legível.
  const publicacoesNovas = await (async () => {
    try {
      const saida: Array<{ projeto: string; linhas: operacaoNova.PublicacaoLinha[] }> = [];
      for (const proj of await listarProjetosNovos()) {
        const linhas = await operacaoNova.publicacoes(proj.id, 20);
        if (linhas.length) saida.push({ projeto: proj.nome, linhas });
      }
      return saida;
    } catch {
      return [];
    }
  })();

  return (
    <div className="mx-auto max-w-5xl">
      {publicacoesNovas.map((g) => (
        <CartaoPub key={g.projeto} className="mb-4" titulo={g.projeto}>
          <ul className="grid grid-cols-1 gap-3">
            {g.linhas.map((p) => (
              <li
                key={p.id}
                className="grid grid-cols-1 gap-1 border-t border-linha pt-3 first:border-0 first:pt-0"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="min-w-0 flex-1 truncate text-sm">{p.oferta}</span>
                  <SeloPub tom={p.estado === "enviada" ? "ok" : p.estado === "falhou" ? "erro" : "neutro"}>
                    {operacaoNova.rotuloPublicacao(p.estado)}
                  </SeloPub>
                </div>
                <p className="text-sm text-tinta2">
                  {p.destino}
                  {p.ciclo > 1 ? " · voltou por queda de preço" : ""}
                  {p.tentativa > 1 ? ` · ${p.tentativa}ª tentativa` : ""}
                </p>
                {p.motivo && <p className="text-sm text-erro">{p.motivo}</p>}
              </li>
            ))}
          </ul>
        </CartaoPub>
      ))}
      <CabecalhoPagina
        titulo="Publicações"
        descricao="O que está por sair e o que já foi publicado nos seus destinos."
      />

      {/* Ritmo de hoje */}
      {Object.keys(planos).length > 0 && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Object.entries(planos).map(([slug, p]) => (
            <Cartao key={slug} titulo={nomeDoProjeto(slug)}>
              {p.cota != null ? (
                <>
                  <p className="text-2xl font-semibold tabular-nums">
                    {enviadasHoje[slug] ?? 0}
                    <span className="text-tinta2">/{p.cota}</span>
                    <span className="ml-2 text-sm font-normal text-tinta2">
                      publicações hoje
                    </span>
                  </p>
                  <p className="mt-1 text-xs text-tinta2">
                    Janela de hoje:{" "}
                    {p.inicio != null ? horaDecimalParaHHMM(p.inicio) : "—"}–
                    {p.fim != null ? horaDecimalParaHHMM(p.fim) : "—"}
                    {p.proximo ? ` · próxima por volta de ${horaDe(p.proximo)}` : ""}
                  </p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-semibold tabular-nums">
                    {enviadasHoje[slug] ?? 0}
                    <span className="ml-2 text-sm font-normal text-tinta2">
                      publicações hoje
                    </span>
                  </p>
                  <p className="mt-1 text-xs text-tinta2">
                    A automação ainda não planejou o dia de hoje.
                  </p>
                </>
              )}
            </Cartao>
          ))}
        </div>
      )}

      {/* Próximas */}
      <Cartao className="mt-4" titulo="Próximas publicações">
        {proximas.length === 0 ? (
          <EstadoVazio
            compacto
            titulo="Nada aguardando publicação"
            descricao="Quando as fontes encontrarem novas ofertas, a fila aparece aqui na ordem de saída."
          />
        ) : (
          <ul className="grid grid-cols-1 gap-2.5 text-sm">
            {proximas.map((o, i) => (
              <li
                key={String(o.mlb_id)}
                className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-baseline gap-x-3"
              >
                <span className="w-6 text-right text-xs tabular-nums text-tinta3">
                  {i + 1}.
                </span>
                <span className="min-w-0">
                  <span className="block truncate">{String(o.nome)}</span>
                  {(varios || String(o.origem) === "clone") && (
                    <span className="mt-0.5 flex items-center gap-2 text-xs text-tinta3">
                      {varios && <span>{nomeDoProjeto(o.perfil)}</span>}
                      {String(o.origem) === "clone" && (
                        <Selo tom="info" ponto={false}>
                          Prioridade
                        </Selo>
                      )}
                    </span>
                  )}
                </span>
                <span className="text-xs font-semibold tabular-nums text-acento">
                  −{n(o.desconto_pct)}%
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-tinta3">
          A ordem é aproximada — ofertas vindas do monitoramento saem primeiro.
        </p>
      </Cartao>

      {/* Novas tentativas — só quando existem */}
      {novasTentativas.length > 0 && (
        <Cartao className="mt-4" titulo="Aguardando nova tentativa">
          <ul className="grid grid-cols-1 gap-2.5 text-sm">
            {novasTentativas.map((o) => (
              <li
                key={String(o.mlb_id)}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3"
              >
                <span className="min-w-0">
                  <span className="block truncate">{String(o.nome)}</span>
                  {motivoLegivel(o.erro) && (
                    <span className="text-xs text-tinta3">{motivoLegivel(o.erro)}</span>
                  )}
                </span>
                <span className="whitespace-nowrap text-xs text-tinta2">
                  nova tentativa às {horaDe(o.proxima_tentativa)}
                </span>
              </li>
            ))}
          </ul>
        </Cartao>
      )}

      {/* Recentes */}
      <Cartao className="mt-4" titulo="Publicações recentes">
        {recentes.length === 0 ? (
          <EstadoVazio
            compacto
            titulo="Nenhuma publicação registrada ainda"
            descricao="O histórico de envios para os seus destinos aparece aqui."
          />
        ) : (
          <ul className="grid grid-cols-1 gap-2.5 text-sm">
            {recentes.map((e, i) => {
              const st = statusEntrega(e.status);
              return (
                <li
                  key={`${e.mlb_id}-${i}`}
                  className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-x-3"
                >
                  <span className="min-w-0">
                    <span className="block truncate">{String(e.nome ?? "Oferta")}</span>
                    {st.tom === "erro" && motivoLegivel(e.erro) && (
                      <span className="text-xs text-erro/80">{motivoLegivel(e.erro)}</span>
                    )}
                  </span>
                  <Selo tom={st.tom}>{st.rotulo}</Selo>
                  <span className="whitespace-nowrap text-xs tabular-nums text-tinta3">
                    {dataCurta(e.atualizado_em)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Cartao>
    </div>
  );
}
