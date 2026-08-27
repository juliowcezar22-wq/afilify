import type { NomeIcone } from "@/components/ui/icone";

export type ItemNav = { rotulo: string; href: string; icone: NomeIcone };
export type GrupoNav = { titulo: string; itens: ItemNav[] };

/**
 * Navegação do produto (blueprint do redesign, Parte 4).
 * /logs fica FORA da navegação comum — página técnica, acessível por URL.
 */
export const NAVEGACAO: GrupoNav[] = [
  {
    titulo: "Geral",
    itens: [
      { rotulo: "Dashboard", href: "/", icone: "dashboard" },
      { rotulo: "Projetos", href: "/projetos", icone: "projeto" },
    ],
  },
  {
    titulo: "Operação",
    itens: [
      { rotulo: "Ofertas", href: "/ofertas", icone: "ofertas" },
      { rotulo: "Publicações", href: "/publicacoes", icone: "publicacoes" },
      { rotulo: "Desempenho", href: "/desempenho", icone: "desempenho" },
    ],
  },
  {
    titulo: "Automação",
    itens: [
      { rotulo: "Fontes", href: "/fontes", icone: "fontes" },
      { rotulo: "Destinos", href: "/destinos", icone: "destinos" },
      { rotulo: "Mensagens", href: "/mensagens", icone: "mensagens" },
      { rotulo: "Ritmo & Regras", href: "/ritmo", icone: "ritmo" },
    ],
  },
  {
    titulo: "Conexões",
    itens: [{ rotulo: "Conexões", href: "/conexoes", icone: "conexoes" }],
  },
  {
    titulo: "Conta",
    itens: [
      { rotulo: "Configurações", href: "/configuracoes", icone: "configuracoes" },
      { rotulo: "Ajuda", href: "/ajuda", icone: "ajuda" },
    ],
  },
];
