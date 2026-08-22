import type { Aviso } from "@/lib/config-cliente";

/** Feedback de salvamento dos formulários — um único formato de aviso. */
export function AvisoSalvar({ aviso }: { aviso: Aviso | null }) {
  if (!aviso) return null;
  return (
    <p role="status" className={`text-sm ${aviso.tom === "ok" ? "text-ok" : "text-erro"}`}>
      {aviso.texto}
    </p>
  );
}
