type Variante = "primario" | "secundario" | "fantasma" | "perigo";
type Tamanho = "sm" | "md";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold " +
  "transition-colors disabled:pointer-events-none disabled:opacity-50";

const VARIANTES: Record<Variante, string> = {
  primario: "bg-acento text-fundo hover:bg-acento2",
  secundario: "border border-linha bg-carta2 text-tinta hover:bg-carta3 hover:border-linha2",
  fantasma: "text-tinta2 hover:text-tinta hover:bg-carta2",
  perigo: "border border-erro/30 bg-erro/10 text-erro hover:bg-erro/20",
};

const TAMANHOS: Record<Tamanho, string> = {
  sm: "px-2.5 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

export function classesBotao(variante: Variante = "primario", tamanho: Tamanho = "md") {
  return `${BASE} ${VARIANTES[variante]} ${TAMANHOS[tamanho]}`;
}

export function Botao({
  variante = "primario",
  tamanho = "md",
  className = "",
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: Variante;
  tamanho?: Tamanho;
}) {
  return (
    <button
      type={type}
      className={`${classesBotao(variante, tamanho)} ${className}`}
      {...props}
    />
  );
}

