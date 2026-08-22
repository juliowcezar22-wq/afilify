import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Cartao } from "@/components/ui/cartao";

export const dynamic = "force-static";

const CONCEITOS: Array<[string, string]> = [
  [
    "Projeto",
    "Uma operação completa: o nicho que você atende, de onde vêm as ofertas e para onde elas são publicadas. Ex.: Perfumes.",
  ],
  [
    "Oferta",
    "Um produto em promoção que a Afilify encontrou para você — com preço, desconto e o seu link de afiliado prontos.",
  ],
  [
    "Publicação",
    "O envio de uma oferta para um destino. Uma oferta encontrada hoje pode ser publicada mais tarde, no ritmo configurado.",
  ],
  [
    "Fonte",
    "De onde as ofertas surgem: a busca automática nas lojas e o monitoramento de grupos concorrentes.",
  ],
  [
    "Destino",
    "Para onde a Afilify publica — hoje, grupos de WhatsApp escolhidos por você.",
  ],
  [
    "Conexão",
    "Uma conta que você conectou à Afilify: seu WhatsApp, sua conta do Mercado Livre, da Shopee.",
  ],
  [
    "Ritmo",
    "Quantas publicações por dia e em qual janela de horário. A Afilify varia os horários naturalmente, como uma pessoa faria.",
  ],
];

export default function Ajuda() {
  return (
    <div className="mx-auto max-w-3xl">
      <CabecalhoPagina
        titulo="Ajuda"
        descricao="Como a Afilify funciona, em uma página."
      />

      <Cartao className="mt-6" titulo="O fluxo">
        <ol className="grid grid-cols-1 gap-2 text-sm text-tinta2">
          <li>
            <strong className="text-tinta">1. Encontrar.</strong> As fontes do
            seu projeto localizam promoções de verdade e geram o seu link.
          </li>
          <li>
            <strong className="text-tinta">2. Aguardar a vez.</strong> Cada
            oferta entra na fila e respeita o ritmo do projeto.
          </li>
          <li>
            <strong className="text-tinta">3. Publicar.</strong> A mensagem sai
            no formato que você definiu, no destino que você escolheu.
          </li>
          <li>
            <strong className="text-tinta">4. Acompanhar.</strong> Dashboard
            mostra o agora; Desempenho, os padrões ao longo do tempo.
          </li>
        </ol>
      </Cartao>

      <Cartao className="mt-4" titulo="Conceitos">
        <dl className="grid grid-cols-1 gap-3">
          {CONCEITOS.map(([termo, definicao]) => (
            <div key={termo}>
              <dt className="text-sm font-semibold">{termo}</dt>
              <dd className="mt-0.5 text-sm text-tinta2">{definicao}</dd>
            </div>
          ))}
        </dl>
      </Cartao>

      <Cartao className="mt-4" titulo="Precisa de mais?">
        <p className="text-sm text-tinta2">
          Fale com o suporte da Afilify — b2cgestao@gmail.com.
        </p>
      </Cartao>
    </div>
  );
}
