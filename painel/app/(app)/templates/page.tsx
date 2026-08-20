import { todas, uma } from "@/lib/dados";
import { Editor } from "./editor";

export const dynamic = "force-dynamic";

export default async function Templates() {
  const linhas = await todas("SELECT perfil, chave, valor FROM config ORDER BY perfil");
  const porPerfil: Record<string, Record<string, unknown>> = {};
  for (const l of linhas) {
    porPerfil[String(l.perfil)] ??= {};
    try { porPerfil[String(l.perfil)][String(l.chave)] = JSON.parse(String(l.valor)); } catch {}
  }
  // uma oferta real para o preview ficar honesto
  const amostra = await uma(
    `SELECT nome, marca, loja, loja_oficial, preco_original, preco_promocional,
            desconto_pct, condicao, link_afiliado
     FROM ofertas WHERE status_envio='ENVIADO' AND loja_oficial=1
     ORDER BY enviado_em DESC LIMIT 1`);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold">Templates & headlines</h1>
      <p className="mt-1 text-sm text-tinta2">
        Salvar aplica na <strong className="text-tinta">próxima mensagem</strong> do grupo — sem deploy, sem restart.
      </p>
      {Object.keys(porPerfil).length === 0 ? (
        <p className="mt-8 text-sm text-alerta">Sem config semeada ainda — suba o worker uma vez.</p>
      ) : (
        Object.entries(porPerfil).map(([perfil, cfg]) => (
          <Editor key={perfil} perfil={perfil} cfg={cfg} amostra={amostra ?? {}} />
        ))
      )}
    </div>
  );
}
