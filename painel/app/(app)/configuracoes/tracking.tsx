"use client";
import { useId, useState } from "react";
import { Botao } from "@/components/ui/botao";
import { CONTROLE } from "@/components/ui/campos";
import { AvisoSalvar } from "@/components/ui/aviso";
import { salvarConfig, type Aviso } from "@/lib/config-cliente";

type Item = { perfil: string; ativo: boolean; base: string };

/**
 * Contagem de cliques nos links publicados. Grava a chave `tracking` por
 * projeto (contrato do motor) com a mesma base pública — decisão D7.
 */
export function FormTracking({ inicial }: { inicial: Item[] }) {
  const idAtivo = useId();
  const idBase = useId();
  const [ativo, setAtivo] = useState(inicial.some((i) => i.ativo));
  const [base, setBase] = useState(inicial.find((i) => i.base)?.base ?? "");
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function salvar() {
    setSalvando(true);
    setAviso(null);
    try {
      // aplica em todos os projetos de uma vez; se algum falhar, o aviso
      // diz exatamente o que ficou de fora (nada de sucesso falso)
      const resultados = await Promise.all(
        inicial.map(async (item) => ({
          perfil: item.perfil,
          ...(await salvarConfig(item.perfil, "tracking", { ativo, base })),
        })),
      );
      const falhas = resultados.filter((r) => !r.ok);
      if (falhas.length === 0) {
        setAviso({ tom: "ok", texto: "Salvo — vale para as próximas publicações." });
      } else if (falhas.length === resultados.length) {
        setAviso({ tom: "erro", texto: falhas[0].erro ?? "falha ao salvar" });
      } else {
        setAviso({
          tom: "erro",
          texto: `Aplicado em parte dos projetos — tente salvar de novo (${falhas[0].erro ?? "falha"}).`,
        });
      }
    } finally {
      setSalvando(false);
    }
  }

  if (inicial.length === 0) {
    return (
      <p className="text-sm text-tinta2">
        Disponível assim que o primeiro projeto estiver ativo.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      <p className="text-sm text-tinta2">
        Com os links inteligentes ligados, a Afilify conta cada clique nas
        suas publicações antes de levar a pessoa à loja. Requer que o painel
        tenha um endereço público — sem isso, os links das mensagens não
        abrem para quem clica.
      </p>
      <label htmlFor={idAtivo} className="flex items-center gap-2 text-sm">
        <input
          id={idAtivo}
          type="checkbox"
          checked={ativo}
          onChange={(e) => setAtivo(e.target.checked)}
          className="h-4 w-4 accent-[var(--color-acento)]"
        />
        Contar cliques nas publicações
      </label>
      <div>
        <label htmlFor={idBase} className="mb-1 block text-xs font-medium text-tinta2">
          Endereço público do painel
        </label>
        <input
          id={idBase}
          value={base}
          onChange={(e) => setBase(e.target.value)}
          placeholder="https://painel.afilify.com.br"
          className={`${CONTROLE} w-full max-w-md`}
        />
      </div>
      <div className="flex items-center gap-3">
        <Botao onClick={salvar} disabled={salvando}>
          {salvando ? "Salvando…" : "Salvar"}
        </Botao>
        <AvisoSalvar aviso={aviso} />
      </div>
    </div>
  );
}
