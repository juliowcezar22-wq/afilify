/**
 * Identificadores internos ficam fora da experiência comum (regra de
 * abstração) — quando têm valor real, moram aqui, colapsados.
 */
export function DetalhesTecnicos({
  itens,
  rotulo = "Detalhes técnicos",
}: {
  itens: Array<[string, string]>;
  rotulo?: string;
}) {
  const visiveis = itens.filter(([, v]) => v !== "");
  if (visiveis.length === 0) return null;
  return (
    <details className="group mt-3">
      <summary className="cursor-pointer select-none text-xs text-tinta3 hover:text-tinta2">
        <span aria-hidden className="mr-1 inline-block transition-transform group-open:rotate-90">
          ▸
        </span>
        {rotulo}
      </summary>
      <dl className="mt-2 grid grid-cols-1 gap-1 rounded-lg bg-fundo/60 p-3 text-xs">
        {visiveis.map(([k, v]) => (
          <div key={k} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
            <dt className="text-tinta3">{k}</dt>
            <dd className="break-all font-mono text-tinta2">{v}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
