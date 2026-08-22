import Link from "next/link";
import { todas } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { nomeDoProjeto } from "@/lib/projetos";
import { gruposDaConta, conexaoConfigurada } from "@/lib/whatsapp";
import { hojeISO } from "@/lib/formatos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { SeletorDestino } from "./seletor";

export const dynamic = "force-dynamic";

/** Para onde as ofertas podem ser publicadas — e quais destinos estão em uso. */
export default async function Destinos() {
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);

  const hoje = hojeISO();
  const [cfgs, grupos, enviadasLinhas] = await Promise.all([
    todas(`SELECT perfil, valor FROM config WHERE chave='canal'${proj.sql} ORDER BY perfil`, proj.params),
    gruposDaConta(),
    todas(
      `SELECT e.canal, COUNT(*) AS n FROM entregas e
       WHERE e.status='enviada' AND e.atualizado_em LIKE ? GROUP BY e.canal`,
      [`${hoje}%`],
    ),
  ]);
  const enviadas = Object.fromEntries(
    enviadasLinhas.map((r) => [String(r.canal), Number(r.n)]),
  );

  const destinos = cfgs.map((c) => {
    let grupo = "";
    try {
      grupo = JSON.parse(String(c.valor)).grupo ?? "";
    } catch {}
    return { perfil: String(c.perfil), grupo };
  });
  const emUso = new Map(destinos.map((d) => [d.grupo, d.perfil]));
  const semConexao = !conexaoConfigurada() || grupos.length === 0;

  return (
    <div className="mx-auto max-w-4xl">
      <CabecalhoPagina
        titulo="Destinos"
        descricao="Para onde cada projeto publica. Trocar o destino vale para as próximas publicações."
      />

      {semConexao && (
        <div className="mt-6">
          <EstadoVazio
            compacto
            titulo="WhatsApp sem conexão no momento"
            descricao="Conecte seu WhatsApp para listar os grupos pelo nome e trocar destinos."
            acao={
              <Link href="/conexoes" className="text-sm text-acento hover:underline">
                Ver conexões →
              </Link>
            }
          />
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4">
        {destinos.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum projeto com destino ainda"
            descricao="Assim que o seu projeto estiver ativo, o destino dele aparece aqui."
          />
        ) : (
          destinos.map((d) => (
            <Cartao key={d.perfil} titulo="Destino do projeto">
              <SeletorDestino
                perfil={d.perfil}
                nomeProjeto={nomeDoProjeto(d.perfil)}
                atual={d.grupo}
                grupos={grupos}
                enviadasHoje={enviadas[d.grupo] ?? 0}
              />
            </Cartao>
          ))
        )}
      </div>

      {grupos.length > 0 && (
        <Cartao className="mt-4" titulo={`Grupos da sua conexão (${grupos.length})`}>
          <ul className="grid grid-cols-1 gap-1.5 text-sm">
            {grupos.map((g) => (
              <li key={g.jid} className="flex items-center justify-between gap-3">
                <span className="min-w-0 truncate">{g.nome || "Grupo sem nome"}</span>
                {emUso.has(g.jid) && (
                  <Selo tom="ok" ponto={false}>
                    em uso · {nomeDoProjeto(emUso.get(g.jid))}
                  </Selo>
                )}
              </li>
            ))}
          </ul>
        </Cartao>
      )}
    </div>
  );
}
