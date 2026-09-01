import type { Tom } from "@/lib/formatos";

const TONS: Record<Tom, { caixa: string; ponto: string }> = {
  ok: { caixa: "bg-ok/10 text-ok", ponto: "bg-ok" },
  erro: { caixa: "bg-erro/10 text-erro", ponto: "bg-erro" },
  alerta: { caixa: "bg-alerta/10 text-alerta", ponto: "bg-alerta" },
  info: { caixa: "bg-info/10 text-info", ponto: "bg-info" },
  neutro: { caixa: "bg-carta2 text-tinta2", ponto: "bg-tinta3" },
};

/** Selo de status. Ponto + texto: o estado nunca depende só da cor. */
export function Selo({
  tom = "neutro",
  ponto = true,
  children,
}: {
  tom?: Tom;
  ponto?: boolean;
  children: React.ReactNode;
}) {
  const t = TONS[tom];
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${t.caixa}`}
    >
      {ponto && <span aria-hidden className={`h-1.5 w-1.5 shrink-0 rounded-full ${t.ponto}`} />}
      {children}
    </span>
  );
}
