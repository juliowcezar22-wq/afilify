import { todas, uma } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { nomeDoProjeto } from "@/lib/projetos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { Editor } from "./editor";

export const dynamic = "force-dynamic";

/** Formato da publicação: chamadas, rodapé e estrutura — com preview. */
export default async function Mensagens() {
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);

  const linhas = await todas(
    `SELECT perfil, chave, valor FROM config
     WHERE chave IN ('mensagem','headlines')${proj.sql} ORDER BY perfil`,
    proj.params,
  );
  const porPerfil: Record<string, Record<string, unknown>> = {};
  for (const l of linhas) {
    porPerfil[String(l.perfil)] ??= {};
    try {
      porPerfil[String(l.perfil)][String(l.chave)] = JSON.parse(String(l.valor));
    } catch {}
  }

  // uma oferta real DO PRÓPRIO PROJETO para o preview ficar honesto
  const amostras: Record<string, Record<string, unknown>> = {};
  await Promise.all(
    Object.keys(porPerfil).map(async (perfil) => {
      const propria = await uma(
        `SELECT nome, marca, loja, loja_oficial, preco_original, preco_promocional,
                desconto_pct, condicao, link_afiliado
         FROM ofertas WHERE status_envio='ENVIADO' AND perfil=?
         ORDER BY loja_oficial DESC, enviado_em DESC LIMIT 1`,
        [perfil],
      );
      if (propria) amostras[perfil] = propria;
    }),
  );

  return (
    <div className="mx-auto max-w-6xl">
      <CabecalhoPagina
        titulo="Mensagens"
        descricao="Como as suas publicações aparecem no grupo. Salvar vale a partir da próxima publicação."
      />

      {Object.keys(porPerfil).length === 0 ? (
        <div className="mt-6">
          <EstadoVazio
            titulo="Nenhum formato de mensagem ainda"
            descricao="Assim que a automação do seu projeto iniciar pela primeira vez, o formato aparece aqui para você personalizar."
          />
        </div>
      ) : (
        <div className="mt-2">
          {Object.entries(porPerfil).map(([perfil, cfg]) => (
            <Editor
              key={perfil}
              perfil={perfil}
              nomeProjeto={nomeDoProjeto(perfil)}
              cfg={cfg}
              amostra={amostras[perfil] ?? {}}
            />
          ))}
        </div>
      )}
    </div>
  );
}
