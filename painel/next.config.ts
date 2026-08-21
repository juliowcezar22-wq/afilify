import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // imagem Docker mínima: o Dockerfile.painel builda com STANDALONE=1.
  // Local (Mac) fica sem standalone — `pnpm start` serve o build normal,
  // imune ao trace órfão que o pnpm cria quando re-resolve o store.
  output: process.env.STANDALONE ? "standalone" : undefined,
};

export default nextConfig;
