"use client";
import { useEffect, useRef, useState } from "react";
import { NavLinks } from "./nav-links";
import { SeletorProjeto } from "./seletor-projeto";
import { Icone } from "@/components/ui/icone";
import type { Projeto } from "@/lib/projetos";

/** Navegação mobile (<md): botão hamburger + drawer acessível
 *  (dialog, Escape fecha, foco gerenciado, focus trap simples). */
export function DrawerMobile({
  projetos,
  projetoAtivo,
}: {
  projetos: Projeto[];
  projetoAtivo: string;
}) {
  const [aberto, setAberto] = useState(false);
  const painelRef = useRef<HTMLDivElement>(null);
  const fecharRef = useRef<HTMLButtonElement>(null);
  const gatilhoRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!aberto) return;
    fecharRef.current?.focus();
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAberto(false);
        gatilhoRef.current?.focus();
        return;
      }
      if (e.key !== "Tab" || !painelRef.current) return;
      const focaveis = painelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), select, input, [tabindex]:not([tabindex="-1"])',
      );
      if (focaveis.length === 0) return;
      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];
      if (e.shiftKey && document.activeElement === primeiro) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primeiro.focus();
      }
    };
    document.addEventListener("keydown", aoTeclar);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", aoTeclar);
      document.body.style.overflow = "";
    };
  }, [aberto]);

  return (
    <>
      <button
        ref={gatilhoRef}
        type="button"
        onClick={() => setAberto(true)}
        aria-label="Abrir menu"
        aria-expanded={aberto}
        className="rounded-lg p-2 text-tinta2 hover:bg-carta2 hover:text-tinta md:hidden"
      >
        <Icone nome="menu" tamanho={20} />
      </button>

      {aberto && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            aria-label="Fechar menu"
            onClick={() => setAberto(false)}
            className="absolute inset-0 bg-fundo/70 backdrop-blur-sm"
          />
          <div
            ref={painelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Menu de navegação"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col overflow-y-auto border-r border-linha bg-carta px-4 py-4"
          >
            <div className="mb-4 flex items-center justify-between">
              <span className="text-lg font-semibold tracking-tight">
                afilify<span className="text-acento">.</span>
              </span>
              <button
                ref={fecharRef}
                type="button"
                onClick={() => {
                  setAberto(false);
                  gatilhoRef.current?.focus();
                }}
                aria-label="Fechar menu"
                className="rounded-lg p-2 text-tinta2 hover:bg-carta2 hover:text-tinta"
              >
                <Icone nome="fechar" tamanho={18} />
              </button>
            </div>
            <div className="mb-5">
              <SeletorProjeto projetos={projetos} ativo={projetoAtivo} />
            </div>
            <NavLinks aoNavegar={() => setAberto(false)} />
            <form action="/api/sair" method="post" className="mt-auto pt-6">
              <button className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-tinta2 hover:bg-carta2 hover:text-tinta">
                <Icone nome="sair" tamanho={16} />
                Sair
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
