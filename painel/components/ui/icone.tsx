/** Ícones do painel — traço 1.8, herdam currentColor. Decorativos por
 * padrão (aria-hidden); o rótulo textual fica sempre ao lado. */
export type NomeIcone =
  | "dashboard"
  | "ofertas"
  | "publicacoes"
  | "desempenho"
  | "fontes"
  | "destinos"
  | "mensagens"
  | "ritmo"
  | "conexoes"
  | "configuracoes"
  | "ajuda"
  | "sair"
  | "menu"
  | "fechar"
  | "projeto"
  | "busca"
  | "seta-baixo";

const DESENHOS: Record<NomeIcone, React.ReactNode> = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </>
  ),
  ofertas: (
    <>
      <path d="M20.6 13.4 12 22 2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8Z" />
      <circle cx="7.5" cy="7.5" r="1.2" />
    </>
  ),
  publicacoes: (
    <>
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4Z" />
    </>
  ),
  desempenho: (
    <>
      <path d="M3 3v16a2 2 0 0 0 2 2h16" />
      <path d="M7 15v-4" />
      <path d="M12 15V7" />
      <path d="M17 15v-7" />
    </>
  ),
  fontes: (
    <>
      <path d="M4 11a9 9 0 0 1 9 9" />
      <path d="M4 4a16 16 0 0 1 16 16" />
      <circle cx="5" cy="19" r="1.5" />
    </>
  ),
  destinos: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.2" />
    </>
  ),
  mensagens: (
    <>
      <path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />
    </>
  ),
  ritmo: (
    <>
      <path d="M3 8h10" />
      <circle cx="16" cy="8" r="2.5" />
      <path d="M21 8h-2.5" />
      <path d="M21 16H11" />
      <circle cx="8" cy="16" r="2.5" />
      <path d="M3 16h2.5" />
    </>
  ),
  conexoes: (
    <>
      <path d="M9 7V3" />
      <path d="M15 7V3" />
      <path d="M6 7h12v4a6 6 0 0 1-12 0Z" />
      <path d="M12 17v4" />
    </>
  ),
  configuracoes: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" />
    </>
  ),
  ajuda: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9a2.5 2.5 0 0 1 4.9.8c0 1.7-2.4 2.2-2.4 3.7" />
      <path d="M12 17h.01" />
    </>
  ),
  sair: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
    </>
  ),
  menu: (
    <>
      <path d="M4 6h16" />
      <path d="M4 12h16" />
      <path d="M4 18h16" />
    </>
  ),
  fechar: (
    <>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </>
  ),
  projeto: (
    <>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
    </>
  ),
  busca: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4-4" />
    </>
  ),
  "seta-baixo": (
    <>
      <path d="m6 9 6 6 6-6" />
    </>
  ),
};

export function Icone({
  nome,
  tamanho = 18,
  className = "",
}: {
  nome: NomeIcone;
  tamanho?: number;
  className?: string;
}) {
  return (
    <svg
      aria-hidden
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 ${className}`}
    >
      {DESENHOS[nome]}
    </svg>
  );
}
