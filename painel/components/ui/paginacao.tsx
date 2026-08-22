import Link from "next/link";

/** Paginação legível: "1–40 de 367" + anterior/próxima preservando filtros. */
export function Paginacao({
  total,
  pagina,
  porPagina,
  criarHref,
}: {
  total: number;
  pagina: number;
  porPagina: number;
  criarHref: (pagina: number) => string;
}) {
  if (total === 0) return null;
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  const de = (pagina - 1) * porPagina + 1;
  const ate = Math.min(pagina * porPagina, total);
  const alcance = `${de.toLocaleString("pt-BR")}–${ate.toLocaleString("pt-BR")} de ${total.toLocaleString("pt-BR")}`;

  const seta =
    "rounded-lg border border-linha px-3 py-1.5 text-sm text-tinta2 hover:border-linha2 hover:text-tinta";
  return (
    <nav aria-label="Paginação" className="mt-4 flex items-center justify-between gap-3">
      <p className="text-sm tabular-nums text-tinta2">{alcance}</p>
      <div className="flex gap-2">
        {pagina > 1 ? (
          <Link className={seta} href={criarHref(pagina - 1)}>
            ← Anterior
          </Link>
        ) : (
          <span className={`${seta} pointer-events-none opacity-40`}>← Anterior</span>
        )}
        {pagina < paginas ? (
          <Link className={seta} href={criarHref(pagina + 1)}>
            Próxima →
          </Link>
        ) : (
          <span className={`${seta} pointer-events-none opacity-40`}>Próxima →</span>
        )}
      </div>
    </nav>
  );
}
