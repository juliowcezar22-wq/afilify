"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function Acoes({ id, status }: { id: string; status: string }) {
  const r = useRouter();
  const [ocupado, setOcupado] = useState(false);

  async function agir(acao: string) {
    setOcupado(true);
    await fetch(`/api/ofertas/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acao }),
    });
    r.refresh();
    setOcupado(false);
  }

  return (
    <div className="flex justify-end gap-2">
      {status === "PENDENTE" && (
        <button disabled={ocupado} onClick={() => agir("ignorar")}
          className="rounded-md border border-linha px-2 py-1 text-xs text-tinta2 hover:text-erro disabled:opacity-50">
          Ignorar
        </button>
      )}
      {status !== "PENDENTE" && (
        <button disabled={ocupado} onClick={() => agir("reenfileirar")}
          className="rounded-md border border-linha px-2 py-1 text-xs text-tinta2 hover:text-acento disabled:opacity-50">
          Reenfileirar
        </button>
      )}
    </div>
  );
}
