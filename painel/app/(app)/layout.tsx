import { contextoProjeto } from "@/lib/contexto";
import { NavLinks } from "@/components/shell/nav-links";
import { SeletorProjeto } from "@/components/shell/seletor-projeto";
import { DrawerMobile } from "@/components/shell/drawer-mobile";
import { Icone } from "@/components/ui/icone";

/**
 * App Shell: sidebar fixa com scroll próprio + conteúdo rolando em <main>.
 * A navegação permanece acessível em qualquer altura de página — correção
 * estrutural do bug "sidebar desaparece no scroll" (blueprint Parte 5).
 */
export default async function LayoutApp({ children }: { children: React.ReactNode }) {
  const { projetos, ativo } = await contextoProjeto();

  return (
    <div className="flex h-dvh overflow-hidden">
      {/* Sidebar desktop */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-linha bg-carta md:flex">
        <div className="px-4 pb-2 pt-6">
          <span className="px-2 text-lg font-semibold tracking-tight">
            afilify<span className="text-acento">.</span>
          </span>
        </div>
        <div className="px-4 pb-4 pt-3">
          <SeletorProjeto projetos={projetos} ativo={ativo?.slug ?? ""} />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
          <NavLinks />
        </div>
        <form action="/api/sair" method="post" className="border-t border-linha px-4 py-3">
          <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-tinta2 hover:bg-carta2 hover:text-tinta">
            <Icone nome="sair" tamanho={16} />
            Sair
          </button>
        </form>
      </aside>

      {/* Coluna de conteúdo */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Barra superior mobile */}
        <header className="flex items-center gap-2 border-b border-linha bg-carta px-3 py-2 md:hidden">
          <DrawerMobile projetos={projetos} projetoAtivo={ativo?.slug ?? ""} />
          <span className="text-base font-semibold tracking-tight">
            afilify<span className="text-acento">.</span>
          </span>
          {ativo && (
            <span className="ml-auto truncate rounded-full bg-carta2 px-2.5 py-1 text-xs text-tinta2">
              {ativo.nome}
            </span>
          )}
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-10 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
