"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Botao } from "@/components/ui/botao";

/** Ações sobre a oferta — quem publica é sempre a automação, no ritmo do
 *  projeto; aqui só mudamos o estado da fila. */
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
      {status === "PENDENTE" ? (
        <Botao
          variante="fantasma"
          tamanho="sm"
          disabled={ocupado}
          onClick={() => agir("ignorar")}
          title="Tira esta oferta da fila de publicação"
        >
          Ignorar
        </Botao>
      ) : (
        <Botao
          variante="secundario"
          tamanho="sm"
          disabled={ocupado}
          onClick={() => agir("reenfileirar")}
          title="Coloca a oferta de volta na fila para publicar de novo"
        >
          Voltar para a fila
        </Botao>
      )}
    </div>
  );
}
