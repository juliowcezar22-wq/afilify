/** Disclosure padrão (▸ que gira) — base de "Detalhes técnicos",
 *  "Modo avançado" e afins. */
export function Detalhes({
  rotulo,
  children,
  className = "",
}: {
  rotulo: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <details className={`group ${className}`}>
      <summary className="cursor-pointer select-none text-xs font-medium text-tinta3 hover:text-tinta2">
        <span aria-hidden className="mr-1 inline-block transition-transform group-open:rotate-90">
          ▸
        </span>
        {rotulo}
      </summary>
      {children}
    </details>
  );
}
