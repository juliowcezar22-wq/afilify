/**
 * Tradução de erro → resposta HTTP, num lugar só.
 *
 * Mora fora de route.ts de propósito: arquivos de rota só podem exportar
 * handlers e configurações reservadas — qualquer outro export faz o Next
 * descartar a rota silenciosamente.
 */
import "server-only";
import { NextResponse } from "next/server";
import { ErroDeAcao } from "@/lib/conexoes-servico";

export function respostaDeErro(e: unknown) {
  if (e instanceof ErroDeAcao)
    return NextResponse.json(
      { erro: { codigo: e.codigo, mensagem: e.paraUsuario, ...e.extra } },
      { status: e.status },
    );
  return NextResponse.json(
    {
      erro: {
        codigo: "falha_inesperada",
        mensagem: "Algo deu errado por aqui. Tente de novo em instantes.",
      },
    },
    { status: 500 },
  );
}
