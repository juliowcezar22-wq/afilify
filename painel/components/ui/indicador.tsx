import Link from "next/link";
import type { Tom } from "@/lib/formatos";

const VALORES: Record<Tom | "padrao", string> = {
  padrao: "text-tinta",
  ok: "text-acento",
  erro: "text-erro",
  alerta: "text-alerta",
  info: "text-info",
  neutro: "text-tinta2",
};

/** Cartão de indicador (KPI). Com `href` o cartão inteiro é clicável. */
export function Indicador({
  rotulo,
  valor,
  tom,
  detalhe,
  href,
}: {
  rotulo: string;
  valor: string | number;
  tom?: Tom;
  detalhe?: string;
  href?: string;
}) {
  const corpo = (
    <>
      <p className="text-xs font-medium uppercase tracking-wider text-tinta2">{rotulo}</p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${VALORES[tom ?? "padrao"]}`}>
        {valor}
      </p>
      {detalhe && <p className="mt-1 truncate text-xs text-tinta3">{detalhe}</p>}
    </>
  );
  const caixa = "block rounded-xl border border-linha bg-carta p-5";
  if (href) {
    return (
      <Link href={href} className={`${caixa} transition-colors hover:border-linha2 hover:bg-carta2`}>
        {corpo}
      </Link>
    );
  }
  return <div className={caixa}>{corpo}</div>;
}
