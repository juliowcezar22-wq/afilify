"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Botao } from "@/components/ui/botao";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";

type Criterios = {
  palavras_chave: string[];
  onde: { busca: boolean; pagina_ofertas: boolean };
  desconto_minimo: number;
  preco: { min: number | null; max: number | null };
  excluir: { palavras: string[]; marcas: string[] };
};

type Amostra = {
  nome: string;
  preco: number;
  preco_original: number | null;
  desconto: number;
  marca: string;
};

const reais = (v: number | null) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/**
 * A configuração da busca, em quatro campos: o que procurar, onde, desconto
 * mínimo e faixa de preço. Exclusões ficam em Avançado.
 *
 * "Testar busca" mostra o que essa configuração traria de verdade — mesma
 * consulta que a coleta faria, só que menor.
 */
export function EditorBusca({
  fonteId,
  inicial,
  ativa,
}: {
  fonteId: string;
  inicial: Criterios;
  ativa: boolean;
}) {
  const router = useRouter();
  const [c, setC] = useState<Criterios>(inicial);
  const [nova, setNova] = useState("");
  const [avancado, setAvancado] = useState(false);
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [resultado, setResultado] = useState<{ compativeis: number; amostra: Amostra[] } | null>(null);

  function palavra(acao: "add" | "del", valor: string) {
    setC((atual) => ({
      ...atual,
      palavras_chave:
        acao === "add"
          ? atual.palavras_chave.includes(valor)
            ? atual.palavras_chave
            : [...atual.palavras_chave, valor]
          : atual.palavras_chave.filter((p) => p !== valor),
    }));
  }

  async function enviar(acao: "salvar" | "testar") {
    setOcupado(acao);
    setErro("");
    setAviso("");
    if (acao === "testar") setResultado(null);
    try {
      const r = await fetch(`/api/fontes/${fonteId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ acao, criterios: c }),
      });
      const d = await r.json();
      if (!r.ok) {
        setErro(d?.erro?.mensagem ?? "Não conseguimos concluir agora.");
        return;
      }
      if (acao === "salvar") {
        setAviso("Configuração salva.");
        router.refresh();
        return;
      }
      await acompanhar(d.comando.id);
    } catch {
      setErro("Não conseguimos falar com a Afilify agora. Verifique sua internet.");
    } finally {
      setOcupado("");
    }
  }

  /** Acompanha o pedido até o motor responder — ou até ele expirar. */
  async function acompanhar(id: string) {
    setOcupado("testar");
    for (let tentativa = 0; tentativa < 40; tentativa++) {
      await new Promise((r) => setTimeout(r, 1500));
      const r = await fetch(`/api/comandos/${id}`, { cache: "no-store" });
      if (!r.ok) continue;
      const d = await r.json();
      if (d.estado === "concluido") {
        setResultado({
          compativeis: Number(d.resultado?.compativeis ?? 0),
          amostra: (d.resultado?.amostra ?? []) as Amostra[],
        });
        if (d.resultado?.aviso) setAviso(String(d.resultado.aviso));
        return;
      }
      if (d.estado === "falhou") {
        setErro(d.erro || "O teste não pôde ser concluído.");
        return;
      }
      if (d.estado === "expirado") {
        setErro("A automação não está rodando agora, então não deu para testar.");
        return;
      }
    }
    setErro("O teste está demorando mais que o normal. Tente de novo em instantes.");
  }

  return (
    <Cartao
      titulo="Busca automática"
      acao={<Selo tom={ativa ? "ok" : "neutro"}>{ativa ? "Ligada" : "Desligada"}</Selo>}
    >
      <div className="grid grid-cols-1 gap-5">
        <div className="grid grid-cols-1 gap-2">
          <p className="text-sm font-medium">O que você quer encontrar?</p>
          <div className="flex flex-wrap gap-2">
            {c.palavras_chave.map((p) => (
              <span
                key={p}
                className="inline-flex items-center gap-1.5 rounded-full bg-carta2 px-3 py-1 text-sm"
              >
                {p}
                <button
                  type="button"
                  onClick={() => palavra("del", p)}
                  aria-label={`Remover ${p}`}
                  className="text-tinta3 hover:text-erro"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              value={nova}
              onChange={(e) => setNova(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && nova.trim()) {
                  e.preventDefault();
                  palavra("add", nova.trim());
                  setNova("");
                }
              }}
              placeholder="perfume masculino"
              className="min-w-48 flex-1 rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm"
            />
            <Botao
              variante="secundario"
              tamanho="sm"
              disabled={!nova.trim()}
              onClick={() => {
                palavra("add", nova.trim());
                setNova("");
              }}
            >
              Adicionar
            </Botao>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2">
          <p className="text-sm font-medium">Onde buscar?</p>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={c.onde.busca}
              onChange={(e) => setC({ ...c, onde: { ...c.onde, busca: e.target.checked } })}
            />
            Nos resultados de busca do Mercado Livre
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={c.onde.pagina_ofertas}
              onChange={(e) =>
                setC({ ...c, onde: { ...c.onde, pagina_ofertas: e.target.checked } })
              }
            />
            Na página de ofertas do dia
          </label>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="grid grid-cols-1 gap-1 text-sm">
            <span className="font-medium">Desconto mínimo</span>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={99}
                value={c.desconto_minimo}
                onChange={(e) => setC({ ...c, desconto_minimo: Number(e.target.value) })}
                className="w-24 rounded-lg border border-linha bg-carta2 px-3 py-2"
              />
              <span className="text-tinta2">%</span>
            </div>
          </label>
          <div className="grid grid-cols-1 gap-1 text-sm">
            <span className="font-medium">Faixa de preço</span>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                placeholder="de"
                value={c.preco.min ?? ""}
                onChange={(e) =>
                  setC({ ...c, preco: { ...c.preco, min: e.target.value ? Number(e.target.value) : null } })
                }
                className="w-24 rounded-lg border border-linha bg-carta2 px-3 py-2"
              />
              <span className="text-tinta2">até</span>
              <input
                type="number"
                min={0}
                placeholder="sem limite"
                value={c.preco.max ?? ""}
                onChange={(e) =>
                  setC({ ...c, preco: { ...c.preco, max: e.target.value ? Number(e.target.value) : null } })
                }
                className="w-28 rounded-lg border border-linha bg-carta2 px-3 py-2"
              />
            </div>
          </div>
        </div>

        <div>
          <button
            type="button"
            onClick={() => setAvancado(!avancado)}
            className="text-sm text-tinta2 hover:text-tinta"
          >
            {avancado ? "Ocultar" : "Mostrar"} opções avançadas
          </button>
          {avancado && (
            <div className="mt-3 grid grid-cols-1 gap-3 rounded-lg border border-linha bg-carta2 p-4 md:grid-cols-2">
              <label className="grid grid-cols-1 gap-1 text-sm">
                <span>Palavras que você não quer ver</span>
                <input
                  value={c.excluir.palavras.join(", ")}
                  onChange={(e) =>
                    setC({
                      ...c,
                      excluir: { ...c.excluir, palavras: e.target.value.split(",").map((x) => x.trim()) },
                    })
                  }
                  placeholder="kit, recarga"
                  className="rounded-lg border border-linha bg-carta px-3 py-2"
                />
              </label>
              <label className="grid grid-cols-1 gap-1 text-sm">
                <span>Marcas que você não quer ver</span>
                <input
                  value={c.excluir.marcas.join(", ")}
                  onChange={(e) =>
                    setC({
                      ...c,
                      excluir: { ...c.excluir, marcas: e.target.value.split(",").map((x) => x.trim()) },
                    })
                  }
                  className="rounded-lg border border-linha bg-carta px-3 py-2"
                />
              </label>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <Botao onClick={() => enviar("salvar")} disabled={ocupado !== ""}>
            {ocupado === "salvar" ? "Salvando…" : "Salvar"}
          </Botao>
          <Botao variante="secundario" onClick={() => enviar("testar")} disabled={ocupado !== ""}>
            {ocupado === "testar" ? "Procurando ofertas…" : "Testar busca"}
          </Botao>
        </div>

        {erro && (
          <p role="status" className="text-sm text-erro">
            {erro}
          </p>
        )}
        {aviso && !erro && (
          <p role="status" className="text-sm text-alerta">
            {aviso}
          </p>
        )}

        {resultado && (
          <div className="rounded-lg border border-linha bg-carta2 p-4">
            <p className="text-sm font-medium">
              {resultado.compativeis === 0
                ? "Nenhum produto compatível com esses critérios."
                : `Encontramos ${resultado.compativeis} produto${resultado.compativeis === 1 ? "" : "s"} compatível${resultado.compativeis === 1 ? "" : "eis"} com seus critérios.`}
            </p>
            {resultado.amostra.length > 0 && (
              <ul className="mt-3 grid grid-cols-1 gap-2">
                {resultado.amostra.map((a, i) => (
                  <li key={i} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                    <span className="min-w-0 flex-1 truncate">{a.nome}</span>
                    <span className="tabular-nums">{reais(a.preco)}</span>
                    <span className="tabular-nums text-ok">−{a.desconto}%</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </Cartao>
  );
}
