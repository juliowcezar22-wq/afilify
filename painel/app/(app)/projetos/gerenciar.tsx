"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Botao } from "@/components/ui/botao";
import { Cartao } from "@/components/ui/cartao";
import { Selo } from "@/components/ui/selo";
import { EstadoVazio } from "@/components/ui/estado-vazio";
import type { Tom } from "@/lib/formatos";

type Automacao = {
  id: string;
  nome: string;
  estado: "rascunho" | "ativa" | "pausada" | "impedida";
  destinos: number;
  fontes: number;
  pendencias: string[];
};

type Projeto = {
  id: string;
  nome: string;
  tipoNicho: string;
  estado: string;
  ofertasHoje: number;
  automacoes: Automacao[];
};

const ESTADO_AUTOMACAO: Record<Automacao["estado"], { rotulo: string; tom: Tom }> = {
  ativa: { rotulo: "Ligada", tom: "ok" },
  pausada: { rotulo: "Pausada", tom: "neutro" },
  impedida: { rotulo: "Falta configurar", tom: "alerta" },
  rascunho: { rotulo: "Falta configurar", tom: "alerta" },
};

export function GerenciarProjetos({
  projetos,
  tipos,
}: {
  projetos: Projeto[];
  tipos: Array<{ id: string; nome: string }>;
}) {
  const router = useRouter();
  const [criando, setCriando] = useState(false);
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState(tipos[0]?.id ?? "");
  const [novaAutomacao, setNovaAutomacao] = useState<{ projeto: string; nome: string } | null>(null);
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");
  const [pendencias, setPendencias] = useState<{ id: string; lista: string[] } | null>(null);

  async function chamar(caminho: string, corpo?: unknown, metodo = "POST") {
    setErro("");
    const r = await fetch(caminho, {
      method: metodo,
      headers: { "Content-Type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw d?.erro ?? { mensagem: "Algo deu errado por aqui." };
    return d;
  }

  async function agir(chave: string, caminho: string, corpo?: unknown, metodo = "POST") {
    setOcupado(chave);
    try {
      await chamar(caminho, corpo, metodo);
      setPendencias(null);
      setCriando(false);
      setNovaAutomacao(null);
      setNome("");
      router.refresh();
    } catch (e) {
      const err = e as { codigo?: string; mensagem?: string; pendencias?: string[] };
      if (err.codigo === "automacao_incompleta" && err.pendencias) {
        setPendencias({ id: chave, lista: err.pendencias });
        setErro(err.mensagem ?? "");
      } else {
        setErro(err.mensagem ?? "Não conseguimos concluir a ação.");
      }
    } finally {
      setOcupado("");
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {projetos.length === 0 && !criando && (
        <EstadoVazio
          titulo="Nenhum projeto ainda"
          descricao="Um projeto agrupa tudo de um nicho: o que procurar, para onde publicar e em que ritmo."
        />
      )}

      {projetos.map((p) => (
        <Cartao
          key={p.id}
          titulo={p.nome}
          acao={
            <span className="text-xs text-tinta2">
              {p.ofertasHoje > 0 ? `${p.ofertasHoje} ofertas hoje` : "sem ofertas hoje"}
            </span>
          }
        >
          {p.automacoes.length === 0 ? (
            <p className="text-sm text-tinta2">
              Este projeto ainda não tem automação. Crie uma para começar a encontrar ofertas.
            </p>
          ) : (
            <ul className="grid grid-cols-1 gap-4">
              {p.automacoes.map((a) => {
                const ap = ESTADO_AUTOMACAO[a.estado];
                const chave = `${a.id}:acao`;
                return (
                  <li key={a.id} className="grid grid-cols-1 gap-2 border-t border-linha pt-3 first:border-0 first:pt-0">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium">{a.nome}</span>
                      <Selo tom={ap.tom}>{ap.rotulo}</Selo>
                    </div>
                    <p className="text-sm text-tinta2">
                      {a.fontes} fonte{a.fontes === 1 ? "" : "s"} · {a.destinos} destino
                      {a.destinos === 1 ? "" : "s"}
                    </p>

                    {a.pendencias.length > 0 && a.estado !== "ativa" && (
                      <ul className="list-disc pl-5 text-sm text-alerta">
                        {a.pendencias.map((f) => (
                          <li key={f}>Falta {f}</li>
                        ))}
                      </ul>
                    )}

                    {pendencias?.id === chave && (
                      <div className="rounded-lg border border-alerta/30 bg-alerta/5 p-3">
                        <p className="text-sm font-medium text-alerta">Ainda não dá para ligar:</p>
                        <ul className="mt-1 list-disc pl-5 text-sm text-tinta2">
                          {pendencias.lista.map((f) => (
                            <li key={f}>{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2">
                      {a.estado === "ativa" ? (
                        <Botao
                          variante="secundario"
                          tamanho="sm"
                          disabled={ocupado !== ""}
                          onClick={() => agir(chave, `/api/automacoes/${a.id}`, { acao: "pausar" })}
                        >
                          Pausar
                        </Botao>
                      ) : (
                        <Botao
                          tamanho="sm"
                          disabled={ocupado !== ""}
                          onClick={() => agir(chave, `/api/automacoes/${a.id}`, { acao: "ativar" })}
                        >
                          {ocupado === chave ? "Ligando…" : "Ligar"}
                        </Botao>
                      )}
                      <Botao
                        variante="perigo"
                        tamanho="sm"
                        disabled={ocupado !== ""}
                        onClick={() => agir(`${a.id}:del`, `/api/automacoes/${a.id}`, undefined, "DELETE")}
                      >
                        Excluir
                      </Botao>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          <div className="mt-4 flex flex-wrap gap-2 border-t border-linha pt-3">
            {novaAutomacao?.projeto === p.id ? (
              <div className="grid w-full grid-cols-1 gap-2">
                <input
                  autoFocus
                  value={novaAutomacao.nome}
                  onChange={(e) => setNovaAutomacao({ projeto: p.id, nome: e.target.value })}
                  placeholder="Ofertas Mercado Livre"
                  className="rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm"
                />
                <div className="flex flex-wrap gap-2">
                  <Botao
                    tamanho="sm"
                    disabled={ocupado !== "" || !novaAutomacao.nome.trim()}
                    onClick={() =>
                      agir(`${p.id}:nova`, `/api/projetos/${p.id}`, {
                        acao: "nova-automacao",
                        nome: novaAutomacao.nome,
                      })
                    }
                  >
                    Criar automação
                  </Botao>
                  <Botao variante="fantasma" tamanho="sm" onClick={() => setNovaAutomacao(null)}>
                    Cancelar
                  </Botao>
                </div>
              </div>
            ) : (
              <>
                <Botao
                  variante="secundario"
                  tamanho="sm"
                  onClick={() => setNovaAutomacao({ projeto: p.id, nome: "" })}
                >
                  Nova automação
                </Botao>
                <Botao
                  variante="secundario"
                  tamanho="sm"
                  disabled={ocupado !== ""}
                  onClick={() => agir(`${p.id}:dup`, `/api/projetos/${p.id}`, { acao: "duplicar" })}
                >
                  Duplicar projeto
                </Botao>
                <Botao
                  variante="fantasma"
                  tamanho="sm"
                  disabled={ocupado !== ""}
                  onClick={() => agir(`${p.id}:arq`, `/api/projetos/${p.id}`, undefined, "DELETE")}
                >
                  Arquivar
                </Botao>
              </>
            )}
          </div>
        </Cartao>
      ))}

      {erro && !pendencias && (
        <p role="status" className="text-sm text-erro">
          {erro}
        </p>
      )}

      {criando ? (
        <Cartao titulo="Novo projeto">
          <div className="grid grid-cols-1 gap-3">
            <label className="grid grid-cols-1 gap-1 text-sm">
              <span className="text-tinta2">Como você quer chamar este projeto?</span>
              <input
                autoFocus
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Perfumes"
                className="rounded-lg border border-linha bg-carta2 px-3 py-2"
              />
            </label>
            <label className="grid grid-cols-1 gap-1 text-sm">
              <span className="text-tinta2">Que tipo de produto ele vende?</span>
              <select
                value={tipo}
                onChange={(e) => setTipo(e.target.value)}
                className="rounded-lg border border-linha bg-carta2 px-3 py-2"
              >
                {tipos.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nome}
                  </option>
                ))}
              </select>
              <span className="text-xs text-tinta3">
                Isso define o que a Afilify aceita como oferta boa neste projeto — marcas
                conhecidas, tamanhos que valem a pena, e o que ela nunca vai publicar.
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              <Botao
                disabled={ocupado !== "" || !nome.trim() || !tipo}
                onClick={() => agir("novo", "/api/projetos", { nome, tipoNicho: tipo })}
              >
                {ocupado === "novo" ? "Criando…" : "Criar projeto"}
              </Botao>
              <Botao variante="fantasma" onClick={() => setCriando(false)}>
                Cancelar
              </Botao>
            </div>
          </div>
        </Cartao>
      ) : (
        <div>
          <Botao onClick={() => setCriando(true)}>Novo projeto</Botao>
        </div>
      )}
    </div>
  );
}
