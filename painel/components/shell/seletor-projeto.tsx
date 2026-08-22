"use client";
import { useId, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { Projeto } from "@/lib/projetos";
import { Icone } from "@/components/ui/icone";

/**
 * Contexto de projeto do shell: "Projeto: Nome ▾". Persistido em cookie
 * via /api/projeto; as páginas de operação filtram por ele no servidor.
 * Com 1 projeto o contexto é fixo (exibição estática); com N, seletor.
 */
export function SeletorProjeto({
  projetos,
  ativo,
}: {
  projetos: Projeto[];
  ativo: string; // slug ou "" (todos)
}) {
  const r = useRouter();
  const id = useId();
  const [pendente, comecar] = useTransition();
  const [valor, setValor] = useState(ativo);
  // re-sincroniza quando o servidor confirma outro valor (ex.: trocado na
  // outra instância — sidebar × drawer)
  const [ativoAnterior, setAtivoAnterior] = useState(ativo);
  if (ativoAnterior !== ativo) {
    setAtivoAnterior(ativo);
    setValor(ativo);
  }

  function trocar(slug: string) {
    setValor(slug);
    comecar(async () => {
      try {
        await fetch("/api/projeto", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ projeto: slug }),
        });
      } catch {
        /* sem rede: o refresh abaixo devolve o valor confirmado */
      }
      r.refresh();
    });
  }

  if (projetos.length === 0) return null;

  // 1 projeto: contexto claro, nada para escolher
  if (projetos.length === 1) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-linha bg-carta2 px-3 py-2">
        <Icone nome="projeto" tamanho={16} className="text-tinta3" />
        <span className="truncate text-sm font-medium text-tinta">{projetos[0].nome}</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <label htmlFor={id} className="sr-only">
        Projeto ativo
      </label>
      <div
        className={`flex items-center gap-2 rounded-lg border border-linha bg-carta2 px-3 py-2 transition-opacity ${
          pendente ? "opacity-60" : ""
        }`}
      >
        <Icone nome="projeto" tamanho={16} className="text-tinta3" />
        <select
          id={id}
          value={valor}
          onChange={(e) => trocar(e.target.value)}
          className="w-full appearance-none bg-transparent pr-5 text-sm font-medium text-tinta"
        >
          <option value="">Todos os projetos</option>
          {projetos.map((p) => (
            <option key={p.slug} value={p.slug}>
              {p.nome}
            </option>
          ))}
        </select>
        <Icone
          nome="seta-baixo"
          tamanho={14}
          className="pointer-events-none absolute right-3 text-tinta3"
        />
      </div>
    </div>
  );
}
