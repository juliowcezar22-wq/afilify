/**
 * ESTADOS DA CONEXÃO — o vocabulário que o usuário lê.
 *
 * Módulo puro de propósito: sem "server-only", sem rede, sem banco. É o que
 * permite testá-lo diretamente, e a lógica aqui já custou dois bugs para
 * ficar de pé.
 */

export type EstadoConexao =
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

/* O provedor tem quatro estados; o produto tem doze. A diferença — o código
   venceu? a sessão caiu sozinha ou fui eu que desconectei? — é o que o
   usuário precisa saber, e não existe do outro lado. */
export const DO_PROVEDOR: Record<string, EstadoConexao> = {
  connected: "conectado",
  connecting: "conectando",
  disconnected: "desconectado",
  hibernated: "precisa_reconectar",
};

/** Estados que descrevem uma situação real e não devem ser apagados por um
 *  "conectando" genérico do provedor. */
export const ESTADOS_QUE_PERMANECEM: EstadoConexao[] = [
  "codigo_expirado",
  "sessao_perdida",
  "desconectado",
  "erro",
];

export const PRECISAM_ATENCAO: EstadoConexao[] = [
  "sessao_perdida",
  "precisa_reconectar",
  "desconectado",
  "codigo_expirado",
  "erro",
];

/**
 * Junta o que o provedor diz com o que já sabíamos, e dá nome ao que o
 * usuário vê.
 *
 * Dois enganos que esta função existe para evitar, ambos vistos em teste
 * contra o serviço real:
 *  · "conectando" dura TODO o pareamento pendente. Traduzido direto, a tela
 *    diria "Conectando" enquanto, na verdade, espera o usuário pegar o
 *    celular — e o código venceria sem que nada na tela mudasse.
 *  · depois de vencido, "conectando" voltaria a apagar o aviso de expiração,
 *    deixando a conexão presa num estado que não descreve nada.
 */
export function traduzirEstado({
  doProvedor,
  guardado,
  codigoExpiraEm,
  agora,
}: {
  doProvedor: EstadoConexao;
  guardado: EstadoConexao;
  codigoExpiraEm: string;
  agora: number;
}): EstadoConexao {
  if (doProvedor === "conectado") return "conectado";

  // Existe código pendente? Então estamos num ciclo de pareamento, e o que
  // importa é se ele ainda vale — não o que o provedor acha.
  if (codigoExpiraEm)
    return Date.parse(codigoExpiraEm) < agora ? "codigo_expirado" : "aguardando_leitura";

  if (doProvedor === "conectando")
    return ESTADOS_QUE_PERMANECEM.includes(guardado) ? guardado : "desconectado";

  // Estava conectada e o provedor diz que não está mais: caiu sozinha.
  // Diferente de "eu desconectei", que grava o estado na hora da ação.
  if (doProvedor === "desconectado" && guardado === "conectado") return "sessao_perdida";

  return doProvedor;
}
