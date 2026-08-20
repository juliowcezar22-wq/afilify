import { todas } from "@/lib/dados";
import { FormRitmo } from "./form";

export const dynamic = "force-dynamic";

export default async function Config() {
  const linhas = await todas(
    "SELECT perfil, valor FROM config WHERE chave = 'ritmo' ORDER BY perfil");
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-xl font-semibold">Configurações do ritmo</h1>
      <p className="mt-1 text-sm text-tinta2">
        Cota, janela e coletas por projeto. Cota e janela novas valem a partir do
        <strong className="text-tinta"> plano de amanhã</strong>; coletas, validade e
        proporção valem imediatamente.
      </p>
      {linhas.length === 0 ? (
        <p className="mt-8 text-sm text-alerta">Sem ritmo semeado — suba o worker uma vez.</p>
      ) : (
        linhas.map((l) => {
          let cfg = {};
          try { cfg = JSON.parse(String(l.valor)); } catch {}
          return <FormRitmo key={String(l.perfil)} perfil={String(l.perfil)} inicial={cfg} />;
        })
      )}
    </div>
  );
}
