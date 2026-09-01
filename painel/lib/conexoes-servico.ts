/**
 * As ações de conexão, num lugar só — as rotas apenas traduzem HTTP.
 *
 * Regra que atravessa o arquivo: o retorno é sempre seguro para exibir.
 * Credencial nunca sai daqui; erro técnico vira frase de produto.
 */
import "server-only";
import * as repo from "@/lib/conexoes";
import * as msg from "@/lib/mensageria";
import { cifraConfigurada } from "@/lib/cripto";
import { traduzirEstado, PRECISAM_ATENCAO } from "@/lib/estados";

export type ConexaoExibivel = {
  id: string;
  plataforma: repo.Plataforma;
  nome: string;
  estado: msg.EstadoConexao;
  perfil: string;
  numeroMascarado: string;
  grupos: number;
  gruposSincronizadosEm: string | null;
  ultimaAtividadeEm: string | null;
  precisaAtencao: boolean;
  /** Só para a área avançada — nunca no fluxo comum. */
  tecnico: { identificador: string; motivoUltimaQueda: string };
};

export class ErroDeAcao extends Error {
  constructor(
    readonly codigo: string,
    readonly paraUsuario: string,
    readonly status = 400,
    readonly extra: Record<string, unknown> = {},
  ) {
    super(`${codigo}: ${paraUsuario}`);
  }
}

/** Mascara o número mantendo o país: "5575999991234" → "+55 75 ••••• 1234". */
export function mascararNumero(bruto: string): string {
  const so = (bruto || "").replace(/\D/g, "");
  if (so.length < 6) return "";
  return `+${so.slice(0, 2)} ${so.slice(2, 4)} ••••• ${so.slice(-4)}`;
}

export async function exibivel(c: repo.Conexao): Promise<ConexaoExibivel> {
  const grupos = await repo.gruposDe(c.id);
  return {
    id: c.id,
    plataforma: c.plataforma,
    nome: c.nome,
    estado: c.estado,
    perfil: c.metadados.perfil ?? "",
    numeroMascarado: c.metadados.numeroMascarado ?? "",
    grupos: grupos.length,
    gruposSincronizadosEm: c.metadados.gruposSincronizadosEm ?? null,
    ultimaAtividadeEm: c.ultimaAtividadeEm,
    precisaAtencao: PRECISAM_ATENCAO.includes(c.estado),
    tecnico: { identificador: c.identificadorExterno, motivoUltimaQueda: c.motivoUltimaQueda },
  };
}

export async function listar(plataforma?: repo.Plataforma): Promise<ConexaoExibivel[]> {
  const conexoes = await repo.listar(plataforma);
  return Promise.all(conexoes.map(exibivel));
}

/** Contas já existentes na instalação que ainda não viraram conexão aqui. */
export async function contasAdotaveis(): Promise<Array<{ identificador: string; nome: string; conectada: boolean }>> {
  if (!msg.podeProvisionar()) return [];
  const [remotas, locais] = await Promise.all([
    msg.contasExistentes().catch(() => []),
    repo.listar("whatsapp"),
  ]);
  const jaUsadas = new Set(locais.map((c) => c.identificadorExterno).filter(Boolean));
  return remotas
    .filter((r) => !jaUsadas.has(r.identificador))
    .map((r) => ({
      identificador: r.identificador,
      nome: r.nome || r.perfil || "Conta sem nome",
      conectada: r.estado === "conectado",
    }));
}

/**
 * Adiciona uma conexão de WhatsApp: cria a conta na plataforma, ou adota uma
 * que já existe (D25b). Nasce em "criando" — o pareamento é o passo seguinte.
 */
export async function adicionarWhatsApp(nome: string, adotarIdentificador = ""): Promise<ConexaoExibivel> {
  if (!nome.trim()) throw new ErroDeAcao("nome_obrigatorio", "Dê um nome para esta conexão.");
  if (!cifraConfigurada())
    throw new ErroDeAcao(
      "cifra_ausente",
      "Esta instalação ainda não está pronta para guardar contas com segurança.",
      503,
    );

  const limite = await repo.podeAdicionarConexao();
  if (!limite.pode)
    throw new ErroDeAcao(
      "limite_do_plano",
      `Seu plano permite ${limite.limite} WhatsApp${limite.limite === 1 ? "" : "s"} conectado${limite.limite === 1 ? "" : "s"} ao mesmo tempo. Desconecte um antes de conectar outro.`,
      429,
    );

  let conta: msg.Conta;
  const adotada = Boolean(adotarIdentificador);
  if (adotarIdentificador) {
    const existentes = await msg.contasExistentes();
    const achada = existentes.find((c) => c.identificador === adotarIdentificador);
    if (!achada)
      throw new ErroDeAcao("conta_nao_encontrada", "Essa conta não está mais disponível.", 404);
    conta = achada;
  } else {
    try {
      conta = await msg.criarConta(nome.trim());
    } catch (e) {
      throw comoErroDeAcao(e);
    }
  }

  const criada = await repo.criar({
    plataforma: "whatsapp",
    nome: nome.trim(),
    credencial: conta.credencial,
    identificadorExterno: conta.identificador,
    estado: conta.estado === "conectado" ? "conectado" : "criando",
    metadados: {
      perfil: conta.perfil,
      numeroMascarado: mascararNumero(conta.numero),
      foto: conta.foto,
      provisionadaPelaAfilify: !adotada,
    },
  });
  return exibivel(criada);
}

/** Gera o código de pareamento. `telefone` vazio = QR. */
export async function gerarCodigo(id: string, telefone = ""): Promise<{
  estado: msg.EstadoConexao;
  tipo: msg.Codigo["tipo"];
  codigo: string;
  expiraEm: string | null;
}> {
  const conexao = await repo.obter(id);
  if (!conexao) throw new ErroDeAcao("nao_encontrada", "Conexão não encontrada.", 404);

  await repo.definirEstado(id, "gerando_codigo");
  const credencial = await repo.credencialDe(id);

  let codigo: msg.Codigo;
  try {
    codigo = await msg.iniciarPareamento(credencial, telefone);
  } catch (e) {
    await repo.definirEstado(id, "erro");
    throw comoErroDeAcao(e);
  }

  if (codigo.estado === "conectado") {
    await sincronizarEstado(id);
    return { estado: "conectado", tipo: "", codigo: "", expiraEm: null };
  }

  const expiraEm = new Date(Date.now() + codigo.validadeSeg * 1000).toISOString();
  await repo.definirEstado(id, "aguardando_leitura", {
    metadados: { codigoExpiraEm: expiraEm, tipoCodigo: codigo.tipo || undefined },
  });
  return { estado: "aguardando_leitura", tipo: codigo.tipo, codigo: codigo.valor, expiraEm };
}

/**
 * Sincroniza o estado guardado com o da plataforma.
 *
 * É aqui que os quatro estados do provedor viram os doze do produto: o que o
 * provedor chama de "desconectado" pode ser "o código venceu", "a sessão caiu
 * sozinha" ou "eu mesmo desconectei" — e a diferença importa para o usuário.
 */
export async function sincronizarEstado(id: string): Promise<ConexaoExibivel> {
  const conexao = await repo.obter(id);
  if (!conexao) throw new ErroDeAcao("nao_encontrada", "Conexão não encontrada.", 404);

  const credencial = await repo.credencialDe(id);
  if (!credencial) return exibivel(conexao);

  let conta: msg.Conta;
  try {
    conta = await msg.consultar(credencial);
  } catch {
    // Falar com a plataforma falhou: não inventamos estado. O guardado
    // continua valendo e o usuário vê o que era verdade da última vez.
    return exibivel(conexao);
  }

  const estado = traduzirEstado({
    doProvedor: conta.estado,
    guardado: conexao.estado,
    codigoExpiraEm: conexao.metadados.codigoExpiraEm ?? "",
    agora: Date.now(),
  });

  const conectouAgora = estado === "conectado" && conexao.estado !== "conectado";
  await repo.definirEstado(id, estado, {
    motivoQueda: conta.motivoQueda,
    atividade: estado === "conectado",
    metadados: {
      perfil: conta.perfil || conexao.metadados.perfil,
      numeroMascarado: mascararNumero(conta.numero) || conexao.metadados.numeroMascarado,
      foto: conta.foto || conexao.metadados.foto,
      // Conectado ou vencido, o código deixa de ser pendente — senão a
      // próxima consulta reavaliaria um código que já não existe.
      ...(estado === "conectado" || estado === "codigo_expirado"
        ? { codigoExpiraEm: undefined, tipoCodigo: undefined }
        : {}),
    },
  });

  // Conectou agora: os grupos são o que o usuário quer ver em seguida, e é
  // o momento certo de pedir que a plataforma avise sobre quedas futuras.
  if (conectouAgora) {
    await sincronizarGrupos(id).catch(() => undefined);
    await ligarAvisos(id).catch(() => undefined);
  }

  const atualizada = await repo.obter(id);
  return exibivel(atualizada!);
}

export async function sincronizarGrupos(id: string): Promise<{ total: number; quando: string }> {
  const conexao = await repo.obter(id);
  if (!conexao) throw new ErroDeAcao("nao_encontrada", "Conexão não encontrada.", 404);
  if (conexao.estado !== "conectado")
    throw new ErroDeAcao(
      "nao_conectada",
      "Conecte esta conta antes de sincronizar os grupos.",
      409,
    );
  const credencial = await repo.credencialDe(id);
  try {
    const grupos = await msg.listarGrupos(credencial);
    const total = await repo.guardarGrupos(
      id,
      grupos.map((g) => ({
        identificador: g.identificador,
        nome: g.nome,
        participantes: g.participantes,
      })),
    );
    return { total, quando: new Date().toISOString() };
  } catch (e) {
    throw comoErroDeAcao(e);
  }
}

export async function desconectar(id: string): Promise<ConexaoExibivel> {
  const conexao = await repo.obter(id);
  if (!conexao) throw new ErroDeAcao("nao_encontrada", "Conexão não encontrada.", 404);
  const credencial = await repo.credencialDe(id);
  try {
    await msg.desconectar(credencial);
  } catch (e) {
    throw comoErroDeAcao(e);
  }
  await repo.definirEstado(id, "desconectado");
  return exibivel((await repo.obter(id))!);
}

export async function renomear(id: string, nome: string): Promise<void> {
  if (!nome.trim()) throw new ErroDeAcao("nome_obrigatorio", "Dê um nome para esta conexão.");
  await repo.renomear(id, nome.trim());
}

/**
 * Remover uma conexão em uso pararia automações. O usuário precisa saber
 * quais antes de confirmar (FR-022) — por isso a primeira chamada recusa e
 * devolve a lista; só a confirmada prossegue.
 */
export async function remover(id: string, confirmado: boolean): Promise<{ pausadas: string[] }> {
  const conexao = await repo.obter(id);
  if (!conexao) throw new ErroDeAcao("nao_encontrada", "Conexão não encontrada.", 404);

  const dependentes = await repo.automacoesQueDependem(id);
  if (dependentes.length > 0 && !confirmado) {
    throw new ErroDeAcao(
      "conexao_em_uso",
      dependentes.length === 1
        ? "Uma automação usa esta conexão e vai parar de publicar."
        : `${dependentes.length} automações usam esta conexão e vão parar de publicar.`,
      409,
      { automacoes: dependentes.map((d) => `${d.projeto} · ${d.nome}`) },
    );
  }

  // Destruir lá fora SÓ o que nós criamos. Uma conta adotada já existia
  // antes da Afilify e continua sendo do usuário: remover a conexão aqui
  // desfaz o vínculo, não a conta dele.
  if (conexao.metadados.provisionadaPelaAfilify) {
    const credencial = await repo.credencialDe(id);
    if (credencial) await msg.apagarConta(credencial).catch(() => undefined);
  }
  await repo.remover(id);
  return { pausadas: dependentes.map((d) => `${d.projeto} · ${d.nome}`) };
}

function comoErroDeAcao(e: unknown): ErroDeAcao {
  if (e instanceof ErroDeAcao) return e;
  if (e instanceof msg.ErroLimiteDeConexoes)
    return new ErroDeAcao("limite_de_conexoes", e.paraUsuario, 429);
  if (e instanceof msg.ErroMensageria)
    return new ErroDeAcao("plataforma_indisponivel", e.paraUsuario, 502);
  return new ErroDeAcao(
    "falha_inesperada",
    "Algo deu errado por aqui. Tente de novo em instantes.",
    500,
  );
}

/**
 * Um aviso da plataforma sobre uma conta mudou de estado.
 *
 * O envelope varia conforme o evento, então procuramos o identificador da
 * conta em mais de um lugar em vez de exigir um formato exato — um aviso
 * que não sabemos ler é preferível a um aviso descartado.
 *
 * A consulta de estado continua existindo como rede de segurança: se o
 * aviso não chegar (painel reiniciando, rede instável), a próxima consulta
 * corrige. Aviso é o caminho rápido, não o único.
 */
export async function registrarAvisoDeConexao(evento: Record<string, unknown>): Promise<void> {
  const instancia = evento.instance ?? evento.instance_id ?? evento.instanceId;
  const bruto = evento.instance && typeof evento.instance === "object"
    ? (evento.instance as Record<string, unknown>)
    : evento;
  const identificador = String(
    (typeof instancia === "string" ? instancia : "") || bruto.id || bruto.instanceId || "",
  );
  if (!identificador) return;

  const conexao = (await repo.listar("whatsapp")).find(
    (c) => c.identificadorExterno === identificador,
  );
  if (!conexao) return;

  // Reconsultamos em vez de confiar no corpo do aviso: o aviso diz "olhe de
  // novo", e a fonte da verdade continua sendo a consulta — que também
  // resolve a diferença entre "caiu sozinha" e "eu desconectei".
  await sincronizarEstado(conexao.id);
}

/**
 * Liga os avisos para uma conexão. Precisa de um endereço público
 * (`APP_URL`) e do segredo — sem eles, a plataforma continua funcionando
 * pela consulta de estado, só que sabendo das quedas mais tarde.
 */
export async function ligarAvisos(id: string): Promise<{ ligado: boolean; motivo?: string }> {
  const base = (process.env.APP_URL ?? "").replace(/\/+$/, "");
  const segredo = process.env.WEBHOOK_SEGREDO ?? "";
  if (!base || !segredo)
    return { ligado: false, motivo: "sem endereço público configurado nesta instalação" };
  const credencial = await repo.credencialDe(id);
  if (!credencial) return { ligado: false, motivo: "conexão sem credencial" };
  try {
    await msg.assinarAvisos(credencial, `${base}/api/avisos/whatsapp/${segredo}`);
    return { ligado: true };
  } catch (e) {
    return { ligado: false, motivo: e instanceof msg.ErroMensageria ? e.paraUsuario : "falha ao ligar" };
  }
}
