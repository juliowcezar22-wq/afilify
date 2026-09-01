"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAVEGACAO } from "./nav-dados";
import { Icone } from "@/components/ui/icone";

/** Grupos de navegação com estado ativo. Usado na sidebar e no drawer. */
export function NavLinks({ aoNavegar }: { aoNavegar?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Navegação principal" className="flex flex-col gap-5">
      {NAVEGACAO.map((grupo) => (
        <div key={grupo.titulo}>
          <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-tinta3">
            {grupo.titulo}
          </p>
          <ul className="mt-1.5 flex flex-col gap-0.5">
            {grupo.itens.map((item) => {
              const ativo =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={aoNavegar}
                    aria-current={ativo ? "page" : undefined}
                    className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                      ativo
                        ? "bg-carta2 font-medium text-tinta"
                        : "text-tinta2 hover:bg-carta2/60 hover:text-tinta"
                    }`}
                  >
                    <Icone
                      nome={item.icone}
                      className={ativo ? "text-acento" : "text-tinta3"}
                    />
                    {item.rotulo}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
