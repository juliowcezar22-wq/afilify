import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // imagem Docker mínima: o Dockerfile.painel builda com STANDALONE=1.
  // Local (Mac) fica sem standalone — `pnpm start` serve o build normal,
  // imune ao trace órfão que o pnpm cria quando re-resolve o store.
  output: process.env.STANDALONE ? "standalone" : undefined,

  // Rotas antigas → vocabulário novo do produto (redesign SaaS).
  // 308 (permanent): bookmarks e histórico continuam funcionando.
  async redirects() {
    return [
      { source: "/fila", destination: "/publicacoes", permanent: true },
      { source: "/canais", destination: "/destinos", permanent: true },
      { source: "/copiador", destination: "/fontes", permanent: true },
      { source: "/templates", destination: "/mensagens", permanent: true },
      { source: "/analytics", destination: "/desempenho", permanent: true },
      { source: "/config", destination: "/ritmo", permanent: true },
    ];
  },
};

export default nextConfig;
