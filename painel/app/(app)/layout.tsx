import Link from "next/link";

/* Menu do blueprint (§31). Itens sem página ainda ficam visíveis e
   desabilitados — o mapa do produto aparece desde o dia 1. */
const MENU: Array<[string, string, boolean]> = [
  ["Dashboard", "/", true],
  ["Ofertas", "/ofertas", true],
  ["Fila de publicação", "/fila", true],
  ["Grupos & canais", "/canais", false],
  ["Copiador", "/copiador", true],
  ["Templates", "/templates", true],
  ["Conexões", "/conexoes", true],
  ["Analytics", "/analytics", false],
  ["Logs", "/logs", true],
  ["Configurações", "/config", true],
];

export default function LayoutApp({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <aside className="w-60 shrink-0 border-r border-linha bg-carta px-4 py-6 hidden md:flex md:flex-col">
        <div className="mb-8 px-2">
          <span className="text-lg font-semibold tracking-tight">
            afilify<span className="text-acento">.</span>
          </span>
          <p className="mt-1 text-[11px] leading-tight text-tinta2">
            operações de ofertas
          </p>
        </div>
        <nav className="flex flex-col gap-1 text-sm">
          {MENU.map(([rotulo, href, ativo]) =>
            ativo ? (
              <Link key={href} href={href}
                className="rounded-md px-3 py-2 text-tinta hover:bg-carta2">
                {rotulo}
              </Link>
            ) : (
              <span key={href}
                className="cursor-not-allowed rounded-md px-3 py-2 text-tinta2/60"
                title="em breve">
                {rotulo}
              </span>
            ),
          )}
        </nav>
        <form action="/api/sair" method="post" className="mt-auto px-2 pt-6">
          <button className="text-xs text-tinta2 hover:text-tinta">sair</button>
        </form>
      </aside>
      <main className="min-w-0 flex-1 px-6 py-8 md:px-10">{children}</main>
    </div>
  );
}
