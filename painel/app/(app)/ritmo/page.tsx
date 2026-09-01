import { todas } from "@/lib/dados";
import { contextoProjeto, condicaoProjeto } from "@/lib/contexto";
import { nomeDoProjeto } from "@/lib/projetos";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import { FormRitmo } from "./form";

export const dynamic = "force-dynamic";

/** Ritmo & Regras por projeto. Configurações da conta ficam em /configuracoes. */
export default async function Ritmo() {
  const ctx = await contextoProjeto();
  const proj = condicaoProjeto(ctx);
  const linhas = await todas(
    `SELECT perfil, valor FROM config WHERE chave = 'ritmo'${proj.sql} ORDER BY perfil`,
    proj.params,
  );

  return (
    <div className="mx-auto max-w-3xl">
      <CabecalhoPagina
        titulo="Ritmo & Regras"
        descricao="Quanto e quando cada projeto publica. Quantidade e janela novas valem a partir de amanhã; o restante, imediatamente."
      />

      {linhas.length === 0 ? (
        <div className="mt-6">
          <EstadoVazio
            titulo="Nenhum ritmo configurado ainda"
            descricao="Assim que a automação do seu projeto iniciar pela primeira vez, o ritmo aparece aqui para você ajustar."
          />
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4">
          {linhas.map((l) => {
            let cfg = {};
            try {
              cfg = JSON.parse(String(l.valor));
            } catch {}
            return (
              <Cartao key={String(l.perfil)}>
                <FormRitmo
                  perfil={String(l.perfil)}
                  nomeProjeto={nomeDoProjeto(l.perfil)}
                  inicial={cfg}
                />
              </Cartao>
            );
          })}
        </div>
      )}
    </div>
  );
}
