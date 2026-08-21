import { NextRequest, NextResponse } from "next/server";
import { uma, executar } from "@/lib/dados";

// Rota PÚBLICA (middleware libera /r/): registra o clique e manda o
// comprador direto para o link de afiliado. Nunca devolve erro feio ao
// clicante — código desconhecido cai no ML genérico.
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ codigo: string }> },
) {
  const { codigo } = await params;
  if (/^[a-z0-9]{4,12}$/.test(codigo)) {
    const alvo = await uma(
      "SELECT link_afiliado, url FROM ofertas WHERE codigo = ?", [codigo]);
    if (alvo) {
      const quando = new Date().toLocaleString("sv-SE",
        { timeZone: "America/Sao_Paulo" }).replace(" ", "T") + "-03:00";
      await executar(
        "INSERT INTO cliques (codigo, quando, agente) VALUES (?, ?, ?)",
        [codigo, quando, (req.headers.get("user-agent") ?? "").slice(0, 200)]);
      return NextResponse.redirect(
        String(alvo.link_afiliado || alvo.url), 302);
    }
  }
  return NextResponse.redirect("https://www.mercadolivre.com.br/ofertas", 302);
}
