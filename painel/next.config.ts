import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // imagem Docker mínima: só .next/standalone vai para o contêiner
  output: "standalone",
};

export default nextConfig;
