import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { SemDados } from "@/components/ui/sem-dados";
import { obterBanco } from "@/lib/dados";
import * as servico from "@/lib/projetos-servico";
import { tiposDeNicho } from "@/lib/projetos-repo";
import { GerenciarProjetos } from "./gerenciar";

export const dynamic = "force-dynamic";

/** Onde a operação nasce: projetos, suas automações, e o que falta para ligar. */
export default async function Projetos() {
  if (!obterBanco()) return <SemDados />;

  const [projetos, tipos] = await Promise.all([
    servico.listar().catch(() => []),
    tiposDeNicho().catch(() => []),
  ]);

  return (
    <div className="mx-auto max-w-4xl">
      <CabecalhoPagina
        titulo="Projetos"
        descricao="Cada projeto é uma operação sua. Dentro dele ficam as automações que encontram e publicam ofertas."
      />
      <div className="mt-6">
        <GerenciarProjetos projetos={projetos} tipos={tipos} />
      </div>
    </div>
  );
}
