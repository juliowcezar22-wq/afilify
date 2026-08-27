/**
 * MENSAGERIA — a conta de WhatsApp do usuário, do lado do painel.
 *
 * Único arquivo do painel que sabe qual fornecedor de infraestrutura existe.
 * Todo o resto trabalha com "uma conexão de WhatsApp" e estados de produto.
 * Espelha nucleo/conexoes/whatsapp.py (decisão D36: o ciclo de conexão roda
 * aqui para não depender do motor estar de pé).
 *
 * Contrato: specs/001-afilify-saas-core/contracts/whatsapp-provider-openapi.yaml
 */
import "server-only";

import { DO_PROVEDOR, type EstadoConexao } from "@/lib/estados";

export type { EstadoConexao };

export const VALIDADE_QR_SEG = 120;
export const VALIDADE_PARCODE_SEG = 300;
const TEMPO_LIMITE_MS = 15_000;

export type Conta = {
  identificador: string;
  credencial: string; // NUNCA sai do servidor
  nome: string;
  estado: EstadoConexao;
  perfil: string;
  numero: string;
  foto: string;
  motivoQueda: string;
};

export type Codigo = {
  tipo: "qr" | "pareamento" | "";
  valor: string;
  validadeSeg: number;
  estado: EstadoConexao;
};

export type GrupoRemoto = {
  identificador: string;
  nome: string;
  participantes: number;
};

/**
 * Todas as vagas de conexão simultânea estão ocupadas.
 *
 * Erro separado porque a saída é diferente de qualquer outra falha: não
 * adianta tentar de novo — é preciso desconectar uma conta antes.
 */
export class ErroLimiteDeConexoes extends Error {
  readonly paraUsuario =
    "Todos os seus WhatsApps disponíveis já estão conectados. Desconecte um antes de conectar outro.";
}

/** Erro com uma face para o usuário e outra para o registro técnico. */
export class ErroMensageria extends Error {
  readonly paraUsuario: string;
  constructor(tecnico: string, paraUsuario?: string) {
    super(tecnico);
    this.paraUsuario =
      paraUsuario ?? "Não conseguimos falar com o WhatsApp agora. Tente de novo em instantes.";
  }
}

function base(): string {
  const url = (process.env.UAZAPI_URL ?? "").replace(/\/+$/, ""); // harness-ok (variável de ambiente)
  if (!url)
    throw new ErroMensageria(
      "URL do provedor ausente",
      "A plataforma de mensagens ainda não foi configurada nesta instalação.",
    );
  return url;
}

function credencialAdmin(): string {
  return (process.env.UAZAPI_ADMIN_TOKEN ?? "").trim(); // harness-ok (variável de ambiente)
}

/** Esta instalação consegue criar contas novas, ou só adotar existentes? (D25b) */
export function podeProvisionar(): boolean {
  return Boolean((process.env.UAZAPI_URL ?? "") && credencialAdmin()); // harness-ok
}

async function chamar(
  caminho: string,
  { metodo = "GET", corpo, cabecalhos }: { metodo?: string; corpo?: unknown; cabecalhos?: Record<string, string> } = {},
): Promise<Record<string, unknown>> {
  let resposta: Response;
  try {
    resposta = await fetch(base() + caminho, {
      method: metodo,
      headers: { "Content-Type": "application/json", ...(cabecalhos ?? {}) },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      signal: AbortSignal.timeout(TEMPO_LIMITE_MS),
      cache: "no-store",
    });
  } catch (e) {
    throw new ErroMensageria(`rede em ${caminho}: ${String(e)}`);
  }
  if (resposta.status === 401 || resposta.status === 403)
    throw new ErroMensageria(
      `${resposta.status} em ${caminho}`,
      "Esta conexão de WhatsApp perdeu o acesso. Reconecte a conta.",
    );
  // O limite é de contas CONECTADAS ao mesmo tempo, não de contas criadas.
  // Criar é livre; conectar é que ocupa vaga — e é aqui que a plataforma
  // recusa. Sem esta tradução, o usuário leria "algo deu errado" quando o
  // problema tem solução óbvia: desconectar uma conta que ele não usa.
  if (resposta.status === 429)
    throw new ErroLimiteDeConexoes(`429 em ${caminho}`);
  if (resposta.status === 503)
    throw new ErroMensageria(
      `503 em ${caminho}`,
      "O serviço de mensagens está sem capacidade no momento. Tente de novo em instantes.",
    );
  if (!resposta.ok) throw new ErroMensageria(`${resposta.status} em ${caminho}`);
  const texto = await resposta.text();
  if (!texto.trim()) return {};
  try {
    return JSON.parse(texto) as Record<string, unknown>;
  } catch {
    throw new ErroMensageria(`resposta ilegível de ${caminho}`);
  }
}

const txt = (v: unknown): string => (v == null ? "" : String(v));

function comoConta(dados: Record<string, unknown>, credencial = ""): Conta {
  const bruto = dados.instance;
  const i = (bruto && typeof bruto === "object" ? bruto : dados) as Record<string, unknown>;
  return {
    identificador: txt(i.id),
    credencial: credencial || txt(i.token) || txt(dados.token),
    nome: txt(i.name) || txt(dados.name),
    estado: DO_PROVEDOR[txt(i.status)] ?? "erro",
    perfil: txt(i.profileName),
    numero: txt(i.owner),
    foto: txt(i.profilePicUrl),
    motivoQueda: txt(i.lastDisconnectReason),
  };
}

/** Cria a estrutura de uma conexão nova. Exige credencial administrativa. */
export async function criarConta(nome: string): Promise<Conta> {
  if (!podeProvisionar())
    throw new ErroMensageria(
      "sem credencial administrativa",
      "Esta instalação não pode criar conexões novas. Escolha uma conta já existente.",
    );
  const conta = comoConta(
    await chamar("/instance/create", {
      metodo: "POST",
      corpo: { name: nome },
      cabecalhos: { admintoken: credencialAdmin() },
    }),
  );
  if (!conta.credencial) throw new ErroMensageria("criação sem credencial na resposta");
  return { ...conta, estado: "criando" };
}

/** Contas já existentes nesta instalação — permite adotar em vez de criar. */
export async function contasExistentes(): Promise<Conta[]> {
  if (!podeProvisionar()) return [];
  const dados = await chamar("/instance/all", { cabecalhos: { admintoken: credencialAdmin() } });
  const itens = Array.isArray(dados) ? dados : ((dados.instances as unknown[]) ?? []);
  return (itens as Record<string, unknown>[])
    .filter((i) => i && typeof i === "object")
    .map((i) => comoConta(i));
}

/**
 * Pede o código para o usuário parear.
 * Sem telefone: QR (vale ~2 min). Com telefone: código digitável (~5 min).
 */
export async function iniciarPareamento(credencial: string, telefone = ""): Promise<Codigo> {
  const dados = await chamar("/instance/connect", {
    metodo: "POST",
    corpo: telefone ? { phone: telefone } : {},
    cabecalhos: { token: credencial },
  });
  const bruto = dados.instance;
  const i = (bruto && typeof bruto === "object" ? bruto : dados) as Record<string, unknown>;

  // Já conectado (pareou antes de a tela pedir): não é erro.
  if (DO_PROVEDOR[txt(i.status)] === "conectado")
    return { tipo: "", valor: "", validadeSeg: 0, estado: "conectado" };

  const pareamento = txt(i.paircode) || txt(dados.paircode);
  const qr = txt(i.qrcode) || txt(dados.qrcode);
  if (telefone && pareamento)
    return { tipo: "pareamento", valor: pareamento, validadeSeg: VALIDADE_PARCODE_SEG, estado: "codigo_disponivel" };
  if (qr) return { tipo: "qr", valor: qr, validadeSeg: VALIDADE_QR_SEG, estado: "codigo_disponivel" };

  throw new ErroMensageria(
    `connect sem código (status=${txt(i.status)})`,
    "Não conseguimos gerar o código agora. Tente gerar um novo.",
  );
}

export async function consultar(credencial: string): Promise<Conta> {
  return comoConta(await chamar("/instance/status", { cabecalhos: { token: credencial } }), credencial);
}

export async function desconectar(credencial: string): Promise<void> {
  await chamar("/instance/disconnect", { metodo: "POST", corpo: {}, cabecalhos: { token: credencial } });
}

export async function apagarConta(credencial: string): Promise<void> {
  await chamar("/instance", { metodo: "DELETE", cabecalhos: { token: credencial } });
}

export async function listarGrupos(credencial: string): Promise<GrupoRemoto[]> {
  const dados = await chamar("/group/list", { cabecalhos: { token: credencial } });
  const brutos = (Array.isArray(dados) ? dados : ((dados.groups as unknown[]) ?? [])) as Record<
    string,
    unknown
  >[];
  const saida: GrupoRemoto[] = [];
  for (const g of brutos) {
    if (!g || typeof g !== "object") continue;
    const identificador = txt(g.JID) || txt(g.jid); // harness-ok (campo da API, nunca exibido)
    if (!identificador) continue;
    const p = g.Participants ?? g.participants;
    saida.push({
      identificador,
      nome: txt(g.Name) || txt(g.name),
      participantes: Array.isArray(p) ? p.length : Number(p ?? 0),
    });
  }
  return saida;
}
