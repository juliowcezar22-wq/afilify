"use client";
import { useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Botao } from "@/components/ui/botao";
import { CONTROLE } from "@/components/ui/campos";
import { Selo } from "@/components/ui/selo";
import { DetalhesTecnicos } from "@/components/ui/detalhes-tecnicos";
import { AvisoSalvar } from "@/components/ui/aviso";
import { salvarConfig, type Aviso } from "@/lib/config-cliente";
import { nomeDoGrupo, type Grupo } from "@/lib/grupos";

/**
 * Destino do projeto: mostra o grupo em uso e permite trocar com busca e
 * confirmação explícita. Grava a chave `canal` (contrato do motor).
 * Todos os grupos ficam alcançáveis (lista rolável); a busca aceita nome
 * ou o final do identificador — grupos sem nome continuam selecionáveis.
 */
export function SeletorDestino({
  perfil,
  nomeProjeto,
  atual,
  grupos,
  enviadasHoje,
}: {
  perfil: string;
  nomeProjeto: string;
  atual: string;
  grupos: Grupo[];
  enviadasHoje: number;
}) {
  const r = useRouter();
  const idBusca = useId();
  const [busca, setBusca] = useState("");
  const [confirmando, setConfirmando] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [emUso, setEmUso] = useState(atual);

  const resultados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    const lista = grupos.filter((g) => g.jid !== emUso);
    if (!q) return lista;
    return lista.filter(
      (g) => g.nome.toLowerCase().includes(q) || g.jid.split("@")[0].endsWith(q),
    );
  }, [busca, grupos, emUso]);

  async function usar(jid: string) {
    setSalvando(true);
    setAviso(null);
    try {
      const res = await salvarConfig(perfil, "canal", { grupo: jid });
      if (res.ok) {
        setEmUso(jid);
        setConfirmando(null);
        setAviso({
          tom: "ok",
          texto: "Destino atualizado — as próximas publicações já vão para o grupo novo.",
        });
        r.refresh(); // atualiza selos "em uso" e contagens da página
      } else {
        setAviso({ tom: "erro", texto: res.erro ?? "não foi possível trocar o destino" });
      }
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm font-medium">{nomeProjeto}</p>
        <span className="text-xs text-tinta3">
          {enviadasHoje} {enviadasHoje === 1 ? "publicação hoje" : "publicações hoje"} neste destino
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-linha bg-carta2 px-3 py-2.5">
        <span className="min-w-0 truncate text-sm font-medium">
          {emUso ? nomeDoGrupo(emUso, grupos) : "Nenhum destino escolhido"}
        </span>
        {emUso && <Selo tom="ok">Em uso</Selo>}
      </div>

      {grupos.length > 0 && (
        <div className="mt-4">
          <label htmlFor={idBusca} className="mb-1 block text-xs font-medium text-tinta2">
            Trocar destino — buscar grupo
          </label>
          <input
            id={idBusca}
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Nome do grupo…"
            className={`${CONTROLE} w-full`}
          />
          {resultados.length > 0 ? (
            <ul className="mt-2 grid max-h-72 grid-cols-1 gap-1.5 overflow-y-auto pr-1">
              {resultados.map((g) => (
                <li
                  key={g.jid}
                  className="flex flex-wrap items-center gap-2 rounded-lg border border-linha px-3 py-2 text-sm"
                >
                  <span className="min-w-0 flex-1 truncate">{nomeDoGrupo(g.jid, grupos)}</span>
                  <span className="flex shrink-0 items-center gap-2">
                    {confirmando === g.jid ? (
                      <>
                        <span className="text-xs text-tinta2">
                          As próximas publicações vão para este grupo.
                        </span>
                        <Botao tamanho="sm" disabled={salvando} onClick={() => usar(g.jid)}>
                          {salvando ? "Trocando…" : "Confirmar"}
                        </Botao>
                        <Botao
                          variante="fantasma"
                          tamanho="sm"
                          onClick={() => setConfirmando(null)}
                        >
                          Cancelar
                        </Botao>
                      </>
                    ) : (
                      <Botao
                        variante="secundario"
                        tamanho="sm"
                        onClick={() => {
                          setConfirmando(g.jid);
                          setAviso(null);
                        }}
                      >
                        Usar este grupo
                      </Botao>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-tinta3">Nenhum grupo com essa busca.</p>
          )}
        </div>
      )}

      <div className="mt-3">
        <AvisoSalvar aviso={aviso} />
      </div>

      <DetalhesTecnicos itens={[["identificador do destino", emUso]]} />
    </div>
  );
}
