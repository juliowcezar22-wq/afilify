import Link from "next/link";
import { obterBanco, todas, uma } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { nomeDoProjeto } from "@/lib/projetos";
import { agoraMs, batidaViva, dataCurta, hojeISO, SQL_ATENCAO } from "@/lib/formatos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Indicador } from "@/components/ui/indicador";
import { Selo } from "@/components/ui/selo";
import { SemDados } from "@/components/ui/sem-dados";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import * as conexoes from "@/lib/conexoes-servico";

export const dynamic = "force-dynamic";

const n = (v: unknown) => Number(v ?? 0);

/* O que dizer de cada conexão com problema — a frase precisa apontar a saída,
   não só nomear o estado. */
const MOTIVO_CONEXAO: Record<string, string> = {
  sessao_perdida: "A conexão caiu",
  precisa_reconectar: "Precisa reconectar",
  desconectado: "Desconectada",
  codigo_expirado: "Falta concluir a conexão",
  erro: "Precisa de atenção",
};

/** Responde: está funcionando? o que aconteceu hoje? algo precisa de mim? */
export default async function Dashboard() {
  if (!obterBanco()) return <SemDados />;

  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);
  const hoje = hojeISO();

  const contar = async (cond: string, params: unknown[] = []) =>
    n(
      (
        await uma(
          `SELECT COUNT(*) AS n FROM ofertas WHERE ${cond}${proj.sql}`,
          [...params, ...proj.params],
        )
      )?.n,
    );

  // uma leva só de consultas — todas independentes
  const [encontradas, publicadas, aguardando, atencao, batidas, porProjeto, recentes] =
    await Promise.all([
      contar("criado_em LIKE ?", [`${hoje}%`]),
      contar("status_envio='ENVIADO' AND enviado_em LIKE ?", [`${hoje}%`]),
      // mesmo critério da lista para onde o cartão leva (status Aguardando)
      contar("status_envio='PENDENTE'"),
      contar(SQL_ATENCAO),
      todas("SELECT chave, valor FROM estado WHERE chave LIKE '%:heartbeat'"),
      todas(
        `SELECT perfil,
                SUM(CASE WHEN status_envio='ENVIADO' AND enviado_em LIKE ? THEN 1 ELSE 0 END) AS hoje,
                SUM(CASE WHEN status_envio='PENDENTE' THEN 1 ELSE 0 END) AS fila
         FROM ofertas WHERE 1=1${proj.sql} GROUP BY perfil ORDER BY perfil`,
        [`${hoje}%`, ...proj.params],
      ),
      todas(
        `SELECT nome, desconto_pct, enviado_em FROM ofertas
         WHERE status_envio='ENVIADO'${proj.sql}
         ORDER BY enviado_em DESC LIMIT 8`,
        proj.params,
      ),
    ]);

  // Uma conexão caída para a operação inteira, e o usuário não descobriria
  // pela contagem de ofertas — descobriria pela ausência delas, tarde demais.
  const conexoesComProblema = await conexoes
    .listar()
    .then((cs) => cs.filter((c) => c.precisaAtencao))
    .catch(() => []);

  const agora = agoraMs();
  const saude = batidas
    .map((b) => ({
      slug: String(b.chave).replace(":heartbeat", ""),
      ok: batidaViva(b.valor, agora),
    }))
    .filter((s) => !ctx.ativo || s.slug === ctx.ativo.slug);

  const tudoBem =
    saude.length > 0 && saude.every((s) => s.ok) && atencao === 0 && conexoesComProblema.length === 0;

  return (
    <div className="mx-auto max-w-5xl">
      <CabecalhoPagina
        titulo="Dashboard"
        descricao={
          ctx.ativo ? `Operação de ${ctx.ativo.nome}, agora.` : "Sua operação, agora."
        }
      />

      <div className="mt-6 grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
        <Indicador rotulo="Ofertas encontradas hoje" valor={encontradas} />
        <Indicador rotulo="Publicações hoje" valor={publicadas} tom="ok" />
        <Indicador
          rotulo="Aguardando publicação"
          valor={aguardando}
          href="/ofertas?status=PENDENTE"
        />
        <Indicador
          rotulo="Precisam de atenção"
          valor={atencao}
          tom={atencao > 0 ? "erro" : undefined}
          detalhe={atencao > 0 ? "Ver o que aconteceu →" : undefined}
          href="/ofertas?status=ERRO"
        />
      </div>

      {conexoesComProblema.length > 0 && (
        <div className="mt-4 rounded-xl border border-erro/30 bg-erro/5 p-5">
          <p className="font-medium text-erro">
            {conexoesComProblema.length === 1
              ? "Uma conexão precisa da sua atenção"
              : `${conexoesComProblema.length} conexões precisam da sua atenção`}
          </p>
          <p className="mt-1 text-sm text-tinta2">
            Enquanto isso, as automações que dependem delas não publicam.
          </p>
          <ul className="mt-3 grid grid-cols-1 gap-2 text-sm">
            {conexoesComProblema.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className="truncate">{c.perfil || c.nome}</span>
                <Selo tom="erro">{MOTIVO_CONEXAO[c.estado] ?? "Precisa de atenção"}</Selo>
              </li>
            ))}
          </ul>
          <Link
            href="/conexoes"
            className="mt-3 inline-block text-sm font-semibold text-acento hover:underline"
          >
            Resolver em Conexões →
          </Link>
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Cartao titulo="Saúde da operação">
          {saude.length === 0 ? (
            <EstadoVazio
              compacto
              titulo="Sem sinal da automação ainda"
              descricao="Assim que a automação do seu projeto iniciar, o estado aparece aqui."
            />
          ) : (
            <>
              <div className="flex items-center gap-2">
                {tudoBem ? (
                  <Selo tom="ok">Funcionando normalmente</Selo>
                ) : atencao > 0 ? (
                  <Selo tom="erro">
                    {atencao} {atencao === 1 ? "item precisa" : "itens precisam"} de atenção
                  </Selo>
                ) : (
                  <Selo tom="alerta">Sem sinal da automação</Selo>
                )}
              </div>
              <ul className="mt-4 grid grid-cols-1 gap-2 text-sm">
                {saude.map((s) => (
                  <li key={s.slug} className="flex items-center justify-between gap-3">
                    <span className="truncate">{nomeDoProjeto(s.slug)}</span>
                    {s.ok ? (
                      <Selo tom="ok">Ativa</Selo>
                    ) : (
                      <Selo tom="alerta">Sem sinal no momento</Selo>
                    )}
                  </li>
                ))}
              </ul>
              {atencao > 0 && (
                <Link
                  href="/ofertas?status=ERRO"
                  className="mt-4 inline-block text-sm text-acento hover:underline"
                >
                  Ver itens que precisam de atenção →
                </Link>
              )}
            </>
          )}
          {porProjeto.length > 1 && (
            <>
              <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-tinta2">
                Por projeto
              </p>
              <ul className="mt-2 grid grid-cols-1 gap-1.5 text-sm">
                {porProjeto.map((p) => (
                  <li key={String(p.perfil)} className="flex justify-between gap-3">
                    <span className="truncate">{nomeDoProjeto(p.perfil)}</span>
                    <span className="shrink-0 tabular-nums text-tinta2">
                      {n(p.hoje)} hoje · {n(p.fila)} aguardando
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Cartao>

        <Cartao
          titulo="Publicações recentes"
          acao={
            <Link href="/publicacoes" className="text-xs text-tinta2 hover:text-tinta">
              Ver todas →
            </Link>
          }
        >
          {recentes.length === 0 ? (
            <EstadoVazio
              compacto
              titulo="Nenhuma publicação ainda"
              descricao="As ofertas publicadas nos seus destinos aparecem aqui."
            />
          ) : (
            <ul className="grid grid-cols-1 gap-2.5">
              {recentes.map((o, i) => (
                <li
                  key={i}
                  className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-baseline gap-x-3 text-sm"
                >
                  <span className="whitespace-nowrap text-xs tabular-nums text-tinta3">
                    {dataCurta(o.enviado_em)}
                  </span>
                  <span className="truncate">{String(o.nome)}</span>
                  <span className="text-xs font-semibold tabular-nums text-acento">
                    −{n(o.desconto_pct)}%
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
