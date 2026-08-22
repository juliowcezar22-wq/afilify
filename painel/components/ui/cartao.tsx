/** Superfície padrão do painel. `titulo` opcional vira o cabeçalho da seção. */
export function Cartao({
  titulo,
  acao,
  className = "",
  children,
}: {
  titulo?: React.ReactNode;
  acao?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`rounded-xl border border-linha bg-carta p-5 ${className}`}>
      {(titulo || acao) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {titulo && (
            <h2 className="text-xs font-semibold uppercase tracking-wider text-tinta2">
              {titulo}
            </h2>
          )}
          {acao}
        </div>
      )}
      {children}
    </section>
  );
}
