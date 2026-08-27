"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Botao } from "@/components/ui/botao";
import { Selo } from "@/components/ui/selo";
import type { Tom } from "@/lib/formatos";

/* Estados de produto. O usuário lê estes; o resto é problema nosso. */
type Estado =
  | "criando"
  | "gerando_codigo"
  | "codigo_disponivel"
  | "aguardando_leitura"
  | "codigo_expirado"
  | "conectando"
  | "conectado"
  | "desconectado"
  | "sessao_perdida"
  | "precisa_reconectar"
  | "reconectando"
  | "erro";

const APRESENTACAO: Record<Estado, { rotulo: string; tom: Tom }> = {
  criando: { rotulo: "Preparando", tom: "info" },
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

const INTERVALO_MS = 2500;

type Conexao = {
  id: string;
  nome: string;
  estado: Estado;
  perfil: string;
  numeroMascarado: string;
  grupos: number;
};

/**
 * O pareamento: pede o código, mostra na tela e acompanha até conectar.
 *
 * A tela só consulta enquanto há código na tela — conectado, ela para. Nada
 * de estado inventado: enquanto a resposta não chega, o que está escrito é o
 * que era verdade da última vez.
 */
export function ConectarWhatsApp({
  conexao,
  aoConectar,
}: {
  conexao: Conexao;
  aoConectar?: () => void;
}) {
  const [estado, setEstado] = useState<Estado>(conexao.estado);
  const [codigo, setCodigo] = useState("");
  const [tipo, setTipo] = useState<"qr" | "pareamento" | "">("");
  const [expiraEm, setExpiraEm] = useState<number | null>(null);
  const [restante, setRestante] = useState(0);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [perfil, setPerfil] = useState({ perfil: conexao.perfil, numero: conexao.numeroMascarado });
  const jaAvisou = useRef(false);

  const esperando = estado === "aguardando_leitura" || estado === "codigo_disponivel";

  const gerar = useCallback(async () => {
    setOcupado(true);
    setErro("");
    setEstado("gerando_codigo");
    try {
      const r = await fetch(`/api/conexoes/${conexao.id}/conectar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const d = await r.json();
      if (!r.ok) {
        setErro(d?.erro?.mensagem ?? "Não conseguimos gerar o código agora.");
        setEstado("erro");
        return;
      }
      setEstado(d.estado as Estado);
      setCodigo(d.codigo ?? "");
      setTipo(d.tipo ?? "");
      setExpiraEm(d.expiraEm ? Date.parse(d.expiraEm) : null);
    } catch {
      setErro("Não conseguimos falar com a Afilify agora. Verifique sua internet.");
      setEstado("erro");
    } finally {
      setOcupado(false);
    }
  }, [conexao.id]);

  /* Contagem do tempo que resta no código — o usuário sabe quanto tem. */
  useEffect(() => {
    if (!expiraEm || !esperando) return;
    const tique = () => {
      const falta = Math.max(0, Math.round((expiraEm - Date.now()) / 1000));
      setRestante(falta);
      if (falta === 0) setEstado("codigo_expirado");
    };
    tique();
    const id = setInterval(tique, 1000);
    return () => clearInterval(id);
  }, [expiraEm, esperando]);

  /* Acompanha o pareamento. Só enquanto o código está na tela. */
  useEffect(() => {
    if (!esperando) return;
    let vivo = true;
    const id = setInterval(async () => {
      try {
        const r = await fetch(`/api/conexoes/${conexao.id}/estado`, { cache: "no-store" });
        if (!vivo || !r.ok) return;
        const d = await r.json();
        const nova = d?.conexao?.estado as Estado | undefined;
        if (!nova) return;
        setEstado(nova);
        if (nova === "conectado") {
          setPerfil({
            perfil: d.conexao.perfil ?? "",
            numero: d.conexao.numeroMascarado ?? "",
          });
          setCodigo("");
        }
      } catch {
        /* falha de rede não muda o que está na tela */
      }
    }, INTERVALO_MS);
    return () => {
      vivo = false;
      clearInterval(id);
    };
  }, [esperando, conexao.id]);

  /* Conectou: avisa a página uma única vez para recarregar os dados. */
  useEffect(() => {
    if (estado === "conectado" && !jaAvisou.current) {
      jaAvisou.current = true;
      aoConectar?.();
    }
  }, [estado, aoConectar]);

  const apresentacao = APRESENTACAO[estado];

  return (
    <div className="grid grid-cols-1 gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Selo tom={apresentacao.tom}>{apresentacao.rotulo}</Selo>
        {esperando && restante > 0 && (
          <span className="text-xs text-tinta2">
            o código vale por mais {Math.floor(restante / 60)}:{String(restante % 60).padStart(2, "0")}
          </span>
        )}
      </div>

      {estado === "conectado" && (
        <div className="rounded-lg border border-ok/30 bg-ok/5 p-4">
          <p className="font-medium">{perfil.perfil || conexao.nome}</p>
          {perfil.numero && <p className="mt-0.5 text-sm text-tinta2">{perfil.numero}</p>}
          <p className="mt-2 text-sm text-tinta2">
            Pronto. Esta conta já pode publicar nos seus grupos.
          </p>
        </div>
      )}

      {esperando && tipo === "qr" && codigo && (
        <div className="grid grid-cols-1 gap-3">
          <div className="mx-auto rounded-xl bg-white p-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={codigo.startsWith("data:") ? codigo : `data:image/png;base64,${codigo}`}
              alt="Código para conectar seu WhatsApp"
              className="h-56 w-56"
            />
          </div>
          <ol className="mx-auto max-w-sm list-decimal space-y-1 pl-5 text-sm text-tinta2">
            <li>Abra o WhatsApp no seu celular</li>
            <li>Toque em Configurações e depois em Aparelhos conectados</li>
            <li>Toque em Conectar aparelho e aponte a câmera para o código</li>
          </ol>
        </div>
      )}

      {esperando && tipo === "pareamento" && codigo && (
        <div className="grid grid-cols-1 gap-3 text-center">
          <p className="font-mono text-3xl font-semibold tracking-widest">{codigo}</p>
          <p className="text-sm text-tinta2">
            Digite este código no seu WhatsApp, em Aparelhos conectados.
          </p>
        </div>
      )}

      {estado === "codigo_expirado" && (
        <p className="text-sm text-alerta">
          O código expirou antes da leitura. Gere um novo — leva um instante.
        </p>
      )}

      {erro && (
        <p role="status" className="text-sm text-erro">
          {erro}
        </p>
      )}

      {estado !== "conectado" && (
        <div>
          <Botao onClick={gerar} disabled={ocupado}>
            {ocupado
              ? "Gerando…"
              : estado === "codigo_expirado"
                ? "Gerar novo código"
                : esperando
                  ? "Gerar outro código"
                  : "Gerar código"}
          </Botao>
        </div>
      )}
    </div>
  );
}
