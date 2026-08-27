"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Botao } from "@/components/ui/botao";
import { Selo } from "@/components/ui/selo";
import { DetalhesTecnicos } from "@/components/ui/detalhes-tecnicos";
import { ConectarWhatsApp } from "./conectar-whatsapp";
import type { Tom } from "@/lib/formatos";

type Estado = Parameters<typeof ConectarWhatsApp>[0]["conexao"]["estado"];

export type ContaWhatsApp = {
  id: string;
  nome: string;
  estado: Estado;
  perfil: string;
  numeroMascarado: string;
  grupos: number;
  gruposSincronizadosEm: string | null;
  ultimaAtividadeEm: string | null;
  precisaAtencao: boolean;
  tecnico: { identificador: string; motivoUltimaQueda: string };
};

type Adotavel = { identificador: string; nome: string; conectada: boolean };

const RESUMO: Partial<Record<Estado, string>> = {
  conectado: "Pronta para publicar nos seus grupos.",
  sessao_perdida: "A conexão caiu. Reconecte para voltar a publicar.",
  precisa_reconectar: "Esta conta precisa ser reconectada para continuar publicando.",
  desconectado: "Conecte esta conta para publicar nos seus grupos.",
  codigo_expirado: "O código expirou antes da leitura. Gere um novo.",
  criando: "Falta conectar seu WhatsApp a esta conexão.",
  erro: "Algo impediu a conexão. Tente gerar um novo código.",
};

const APRESENTACAO: Record<Estado, { rotulo: string; tom: Tom }> = {
  criando: { rotulo: "Falta conectar", tom: "alerta" },
  gerando_codigo: { rotulo: "Gerando código", tom: "info" },
  codigo_disponivel: { rotulo: "Código pronto", tom: "info" },
  aguardando_leitura: { rotulo: "Aguardando leitura", tom: "info" },
  codigo_expirado: { rotulo: "Código expirado", tom: "alerta" },
  conectando: { rotulo: "Conectando", tom: "info" },
  conectado: { rotulo: "Conectado", tom: "ok" },
  desconectado: { rotulo: "Desconectado", tom: "erro" },
  sessao_perdida: { rotulo: "Sessão perdida", tom: "erro" },
  precisa_reconectar: { rotulo: "Precisa reconectar", tom: "alerta" },
  reconectando: { rotulo: "Reconectando", tom: "info" },
  erro: { rotulo: "Precisa de atenção", tom: "erro" },
};

function desde(iso: string | null): string {
  if (!iso) return "";
  const min = Math.round((Date.now() - Date.parse(iso)) / 60_000);
  if (!Number.isFinite(min) || min < 0) return "";
  if (min < 1) return "agora mesmo";
  if (min < 60) return `há ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `há ${h} h`;
  return `há ${Math.round(h / 24)} dia(s)`;
}

export function WhatsAppContas({
  contas,
  adotaveis,
  podeCriar,
}: {
  contas: ContaWhatsApp[];
  adotaveis: Adotavel[];
  podeCriar: boolean;
}) {
  const router = useRouter();
  const [adicionando, setAdicionando] = useState(false);
  const [nome, setNome] = useState("");
  const [adotar, setAdotar] = useState("");
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");
  const [confirmacao, setConfirmacao] = useState<{ id: string; automacoes: string[] } | null>(null);

  const recarregar = useCallback(() => router.refresh(), [router]);

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

  async function adicionar() {
    setOcupado("adicionar");
    try {
      await chamar("/api/conexoes", { plataforma: "whatsapp", nome, adotar });
      setAdicionando(false);
      setNome("");
      setAdotar("");
      recarregar();
    } catch (e) {
      setErro((e as { mensagem?: string }).mensagem ?? "Não conseguimos adicionar a conexão.");
    } finally {
      setOcupado("");
    }
  }

  async function acao(id: string, caminho: string, corpo?: unknown, metodo = "POST") {
    setOcupado(id + caminho);
    try {
      await chamar(`/api/conexoes/${id}${caminho}`, corpo, metodo);
      setConfirmacao(null);
      recarregar();
    } catch (e) {
      const err = e as { codigo?: string; mensagem?: string; automacoes?: string[] };
      if (err.codigo === "conexao_em_uso") {
        setConfirmacao({ id, automacoes: err.automacoes ?? [] });
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
      {contas.length === 0 && !adicionando && (
        <p className="text-sm text-tinta2">
          Nenhum WhatsApp conectado ainda. Conecte um para começar a publicar.
        </p>
      )}

      <ul className="grid grid-cols-1 gap-5">
        {contas.map((c) => {
          const ap = APRESENTACAO[c.estado];
          const precisaParear = c.estado !== "conectado";
          return (
            <li key={c.id} className="grid grid-cols-1 gap-3 border-t border-linha pt-4 first:border-0 first:pt-0">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{c.perfil || c.nome}</p>
                  {c.numeroMascarado && (
                    <p className="mt-0.5 text-sm text-tinta2">{c.numeroMascarado}</p>
                  )}
                </div>
                <Selo tom={ap.tom}>{ap.rotulo}</Selo>
              </div>

              <p className="text-sm text-tinta2">{RESUMO[c.estado] ?? ""}</p>

              {c.estado === "conectado" && (
                <p className="text-sm text-tinta2">
                  {c.grupos} grupo{c.grupos === 1 ? "" : "s"} sincronizado
                  {c.grupos === 1 ? "" : "s"}
                  {c.gruposSincronizadosEm ? ` · ${desde(c.gruposSincronizadosEm)}` : ""}
                  {c.ultimaAtividadeEm ? ` · última atividade ${desde(c.ultimaAtividadeEm)}` : ""}
                </p>
              )}

              {precisaParear && <ConectarWhatsApp conexao={c} aoConectar={recarregar} />}

              <div className="flex flex-wrap gap-2">
                {c.estado === "conectado" && (
                  <>
                    <Botao
                      variante="secundario"
                      tamanho="sm"
                      disabled={ocupado !== ""}
                      onClick={() => acao(c.id, "/sincronizar-grupos")}
                    >
                      {ocupado === c.id + "/sincronizar-grupos" ? "Sincronizando…" : "Sincronizar grupos"}
                    </Botao>
                    <Botao
                      variante="secundario"
                      tamanho="sm"
                      disabled={ocupado !== ""}
                      onClick={() => acao(c.id, "/desconectar")}
                    >
                      Desconectar
                    </Botao>
                  </>
                )}
                <Botao
                  variante="perigo"
                  tamanho="sm"
                  disabled={ocupado !== ""}
                  onClick={() => acao(c.id, "", { confirmar: false }, "DELETE")}
                >
                  Remover
                </Botao>
              </div>

              {confirmacao?.id === c.id && (
                <div className="rounded-lg border border-alerta/30 bg-alerta/5 p-4">
                  <p className="text-sm font-medium text-alerta">
                    Remover esta conexão vai parar de publicar em:
                  </p>
                  <ul className="mt-2 list-disc pl-5 text-sm text-tinta2">
                    {confirmacao.automacoes.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Botao
                      variante="perigo"
                      tamanho="sm"
                      onClick={() => acao(c.id, "", { confirmar: true }, "DELETE")}
                    >
                      Remover mesmo assim
                    </Botao>
                    <Botao variante="fantasma" tamanho="sm" onClick={() => setConfirmacao(null)}>
                      Cancelar
                    </Botao>
                  </div>
                </div>
              )}

              <DetalhesTecnicos
                itens={[
                  ["identificador da conta", c.tecnico.identificador || "—"],
                  ["motivo da última queda", c.tecnico.motivoUltimaQueda || "—"],
                  ["estado interno", c.estado],
                ]}
              />
            </li>
          );
        })}
      </ul>

      {erro && !confirmacao && (
        <p role="status" className="text-sm text-erro">
          {erro}
        </p>
      )}

      {adicionando ? (
        <div className="grid grid-cols-1 gap-3 rounded-lg border border-linha bg-carta2 p-4">
          <label className="grid grid-cols-1 gap-1 text-sm">
            <span className="text-tinta2">Como você quer chamar esta conexão?</span>
            <input
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Promoções Principal"
              className="rounded-lg border border-linha bg-carta px-3 py-2 text-tinta"
            />
          </label>

          {adotaveis.length > 0 && (
            <label className="grid grid-cols-1 gap-1 text-sm">
              <span className="text-tinta2">
                Já existe uma conta preparada nesta instalação. Quer usar uma delas?
              </span>
              <select
                value={adotar}
                onChange={(e) => setAdotar(e.target.value)}
                className="rounded-lg border border-linha bg-carta px-3 py-2 text-tinta"
              >
                <option value="">Criar uma conta nova</option>
                {adotaveis.map((a) => (
                  <option key={a.identificador} value={a.identificador}>
                    {a.nome}
                    {a.conectada ? " (já conectada)" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}

          {!podeCriar && !adotar && (
            <p className="text-sm text-alerta">
              Esta instalação não pode criar contas novas. Escolha uma conta já preparada acima.
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <Botao onClick={adicionar} disabled={ocupado !== "" || !nome.trim()}>
              {ocupado === "adicionar" ? "Adicionando…" : "Adicionar conexão"}
            </Botao>
            <Botao variante="fantasma" onClick={() => setAdicionando(false)}>
              Cancelar
            </Botao>
          </div>
        </div>
      ) : (
        <div>
          <Botao onClick={() => setAdicionando(true)}>Adicionar conexão</Botao>
        </div>
      )}
    </div>
  );
}
