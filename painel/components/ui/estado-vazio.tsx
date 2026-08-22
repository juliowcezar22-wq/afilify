/** Estado vazio útil: o que significa + o que fazer a respeito. */
export function EstadoVazio({
  titulo,
  descricao,
  acao,
  compacto = false,
}: {
  titulo: string;
  descricao?: React.ReactNode;
  acao?: React.ReactNode;
  compacto?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-linha bg-carta/50 text-center ${
        compacto ? "px-4 py-6" : "px-6 py-12"
      }`}
    >
      <p className="text-sm font-medium text-tinta">{titulo}</p>
      {descricao && <p className="mt-1 max-w-md text-sm text-tinta2">{descricao}</p>}
      {acao && <div className="mt-4">{acao}</div>}
    </div>
  );
}
