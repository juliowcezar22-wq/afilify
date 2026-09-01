"""
WHATSAPP — a conta de mensagens do usuário

Esta é a ÚNICA parte do sistema que sabe qual provedor de infraestrutura está
por trás. Para todo o resto da Afilify existe "uma conexão de WhatsApp" com
estados de produto. Quem chamar daqui para fora nunca vê token, instância,
JID nem nome de fornecedor.

    from nucleo.conexoes import whatsapp

    conta  = whatsapp.criar_conta("Promoções Principal")   # devolve credencial
    codigo = whatsapp.iniciar_pareamento(conta.credencial)
    estado = whatsapp.consultar(conta.credencial)
    grupos = whatsapp.listar_grupos(conta.credencial)

Contrato do provedor: specs/001-afilify-saas-core/contracts/whatsapp-provider-openapi.yaml
Verificado contra a conta real em 27/08/2026 (criar e apagar instância, listar, status).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

# ── estados de produto (a spec, FR-011) ──────────────────────────────
CRIANDO = "criando"
GERANDO_CODIGO = "gerando_codigo"
CODIGO_DISPONIVEL = "codigo_disponivel"
AGUARDANDO_LEITURA = "aguardando_leitura"
CODIGO_EXPIRADO = "codigo_expirado"
CONECTANDO = "conectando"
CONECTADO = "conectado"
DESCONECTADO = "desconectado"
SESSAO_PERDIDA = "sessao_perdida"
PRECISA_RECONECTAR = "precisa_reconectar"
RECONECTANDO = "reconectando"
ERRO = "erro"

# O provedor tem quatro estados; o produto tem onze. A diferença é o que o
# usuário precisa saber (o código venceu? a sessão caiu sozinha ou fui eu que
# desconectei?) e mora no estado local, não aqui.
DO_PROVEDOR = {
    "connected": CONECTADO,
    "connecting": CONECTANDO,
    "disconnected": DESCONECTADO,
    "hibernated": PRECISA_RECONECTAR,
}

# Validades declaradas pelo provedor; usadas para dizer ao usuário quanto
# tempo ele tem, em vez de deixar o código morrer sem aviso.
VALIDADE_QR_SEG = 120
VALIDADE_PARCODE_SEG = 300

TEMPO_LIMITE = 25


class ErroLimiteDeConexoes(RuntimeError):
    """Todas as vagas de conexão simultânea estão ocupadas.

    Separado porque a saída é diferente de qualquer outra falha: tentar de
    novo não resolve — é preciso desconectar uma conta antes.
    """

    mensagem_usuario = (
        "Todos os seus WhatsApps disponíveis já estão conectados. "
        "Desconecte um antes de conectar outro.")


class ErroWhatsApp(RuntimeError):
    """Falha ao falar com a plataforma de mensagens.

    `mensagem_usuario` é o que pode ser mostrado na tela: sem token, sem
    nome de fornecedor, sem código HTTP.
    """

    def __init__(self, tecnico: str, mensagem_usuario: str = ""):
        super().__init__(tecnico)
        self.mensagem_usuario = (
            mensagem_usuario or "Não conseguimos falar com o WhatsApp agora. Tente de novo em instantes.")


@dataclass
class Conta:
    """Uma conexão de WhatsApp, do ponto de vista do produto."""
    identificador: str = ""          # id da instância — área técnica
    credencial: str = ""             # token — NUNCA sai do servidor
    nome: str = ""
    estado: str = CRIANDO
    perfil: str = ""                 # nome do WhatsApp conectado
    numero: str = ""
    foto: str = ""
    e_comercial: bool = False
    ultima_queda: str = ""
    motivo_queda: str = ""


@dataclass
class Codigo:
    """O que o usuário precisa para parear: QR ou código de pareamento."""
    tipo: str = "qr"                 # 'qr' | 'pareamento'
    valor: str = ""                  # imagem base64 (qr) ou o código digitável
    validade_seg: int = VALIDADE_QR_SEG
    estado: str = GERANDO_CODIGO


@dataclass
class Grupo:
    identificador: str
    nome: str = ""
    participantes: int = 0
    sou_admin: bool = False


@dataclass
class Config:
    url: str = ""
    admin: str = ""

    @classmethod
    def do_ambiente(cls) -> "Config":
        return cls(
            url=(os.environ.get("UAZAPI_URL") or "").rstrip("/"),
            admin=(os.environ.get("UAZAPI_ADMIN_TOKEN") or "").strip(),
        )

    def completa(self) -> bool:
        return bool(self.url)

    def pode_provisionar(self) -> bool:
        """Sem credencial administrativa a plataforma ainda conecta contas —
        só não cria a estrutura sozinha (decisão D25b)."""
        return bool(self.url and self.admin)


def _requisitar(caminho: str, metodo: str = "GET", corpo=None,
                headers=None, cfg: Config = None):
    cfg = cfg or Config.do_ambiente()
    if not cfg.completa():
        raise ErroWhatsApp(
            "UAZAPI_URL ausente",
            "A plataforma de mensagens ainda não foi configurada nesta instalação.")
    req = urllib.request.Request(
        cfg.url + caminho, method=metodo,
        data=json.dumps(corpo).encode("utf-8") if corpo is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as r:
            bruto = r.read().decode("utf-8")
        return json.loads(bruto) if bruto.strip() else {}
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErroWhatsApp(
                f"HTTP {e.code} em {caminho}",
                "Esta conexão de WhatsApp perdeu o acesso. Reconecte a conta.") from e
        # O limite é de contas CONECTADAS ao mesmo tempo, não de contas
        # criadas: criar é livre, conectar é que ocupa vaga.
        if e.code == 429:
            raise ErroLimiteDeConexoes(f"HTTP 429 em {caminho}") from e
        if e.code == 503:
            raise ErroWhatsApp(
                f"HTTP 503 em {caminho}",
                "O serviço de mensagens está sem capacidade no momento. "
                "Tente de novo em instantes.") from e
        raise ErroWhatsApp(f"HTTP {e.code} em {caminho}") from e
    except urllib.error.URLError as e:
        raise ErroWhatsApp(f"rede: {e}") from e
    except json.JSONDecodeError as e:
        raise ErroWhatsApp(f"resposta ilegível de {caminho}") from e


def _conta_do_payload(dados: dict, credencial: str = "") -> Conta:
    """Traduz o objeto do provedor para o vocabulário do produto."""
    inst = dados.get("instance") if isinstance(dados.get("instance"), dict) else dados
    inst = inst or {}
    return Conta(
        identificador=str(inst.get("id") or ""),
        credencial=credencial or str(inst.get("token") or dados.get("token") or ""),
        nome=str(inst.get("name") or dados.get("name") or ""),
        estado=DO_PROVEDOR.get(str(inst.get("status") or ""), ERRO),
        perfil=str(inst.get("profileName") or ""),
        numero=str(inst.get("owner") or ""),
        foto=str(inst.get("profilePicUrl") or ""),
        e_comercial=bool(inst.get("isBusiness")),
        ultima_queda=str(inst.get("lastDisconnect") or ""),
        motivo_queda=str(inst.get("lastDisconnectReason") or ""),
    )


# ── ciclo de vida ────────────────────────────────────────────────────

def criar_conta(nome: str, cfg: Config = None) -> Conta:
    """Cria a estrutura para uma conexão nova. Exige credencial administrativa."""
    cfg = cfg or Config.do_ambiente()
    if not cfg.pode_provisionar():
        raise ErroWhatsApp(
            "sem admintoken",
            "Esta instalação não pode criar conexões novas. Escolha uma conta já existente.")
    dados = _requisitar("/instance/create", "POST", {"name": nome},
                        {"admintoken": cfg.admin}, cfg)
    conta = _conta_do_payload(dados)
    if not conta.credencial:
        raise ErroWhatsApp("criação sem credencial na resposta")
    conta.estado = CRIANDO
    return conta


def contas_existentes(cfg: Config = None) -> list:
    """Contas já criadas nesta instalação — permite adotar uma em vez de criar
    (D25b), e é como a validação usa a conta livre sem tocar na de produção."""
    cfg = cfg or Config.do_ambiente()
    if not cfg.pode_provisionar():
        return []
    dados = _requisitar("/instance/all", "GET", None, {"admintoken": cfg.admin}, cfg)
    itens = dados if isinstance(dados, list) else (dados.get("instances") or [])
    return [_conta_do_payload(i) for i in itens if isinstance(i, dict)]


def apagar_conta(credencial: str, cfg: Config = None) -> None:
    _requisitar("/instance", "DELETE", None, {"token": credencial}, cfg)


def iniciar_pareamento(credencial: str, telefone: str = "", cfg: Config = None) -> Codigo:
    """Pede o código para o usuário parear.

    Sem telefone: QR para escanear (vale ~2 min).
    Com telefone: código digitável no aparelho (vale ~5 min).
    """
    corpo = {"phone": telefone} if telefone else {}
    dados = _requisitar("/instance/connect", "POST", corpo, {"token": credencial}, cfg)
    inst = dados.get("instance") if isinstance(dados.get("instance"), dict) else dados
    inst = inst or {}

    qr = str(inst.get("qrcode") or dados.get("qrcode") or "")
    par = str(inst.get("paircode") or dados.get("paircode") or "")
    estado_provedor = str(inst.get("status") or "")

    # Já conectada (o usuário pareou antes de a tela pedir): não é erro.
    if DO_PROVEDOR.get(estado_provedor) == CONECTADO:
        return Codigo(tipo="", valor="", validade_seg=0, estado=CONECTADO)

    if telefone and par:
        return Codigo("pareamento", par, VALIDADE_PARCODE_SEG, CODIGO_DISPONIVEL)
    if qr:
        return Codigo("qr", qr, VALIDADE_QR_SEG, CODIGO_DISPONIVEL)
    raise ErroWhatsApp(
        f"connect sem código (status={estado_provedor!r})",
        "Não conseguimos gerar o código agora. Tente gerar um novo.")


def consultar(credencial: str, cfg: Config = None) -> Conta:
    """Estado atual da conta, direto da plataforma."""
    dados = _requisitar("/instance/status", "GET", None, {"token": credencial}, cfg)
    return _conta_do_payload(dados, credencial)


def desconectar(credencial: str, cfg: Config = None) -> None:
    _requisitar("/instance/disconnect", "POST", {}, {"token": credencial}, cfg)


# ── grupos ───────────────────────────────────────────────────────────

def listar_grupos(credencial: str, cfg: Config = None) -> list:
    dados = _requisitar("/group/list", "GET", None, {"token": credencial}, cfg)
    brutos = dados.get("groups") if isinstance(dados, dict) else dados
    saida = []
    for g in (brutos or []):
        if not isinstance(g, dict):
            continue
        identificador = str(g.get("JID") or g.get("jid") or "")
        if not identificador:
            continue
        participantes = g.get("Participants") or g.get("participants") or []
        saida.append(Grupo(
            identificador=identificador,
            nome=str(g.get("Name") or g.get("name") or ""),
            participantes=len(participantes) if isinstance(participantes, list)
                          else int(participantes or 0),
            sou_admin=bool(g.get("IsAdmin") or g.get("isAdmin")),
        ))
    return saida


def criar_grupo(credencial: str, nome: str, participantes: list = None,
                cfg: Config = None) -> Grupo:
    """Usado pela validação para ter um grupo de teste sem mexer no grupo real."""
    dados = _requisitar("/group/create", "POST",
                        {"name": nome, "participants": participantes or []},
                        {"token": credencial}, cfg)
    inst = dados.get("group") if isinstance(dados.get("group"), dict) else dados
    inst = inst or {}
    return Grupo(
        identificador=str(inst.get("JID") or inst.get("jid") or ""),
        nome=str(inst.get("Name") or inst.get("name") or nome),
    )


# ── saúde da conta ───────────────────────────────────────────────────

def limites_do_numero(credencial: str, cfg: Config = None) -> dict:
    """O WhatsApp está limitando esta conta? Alimenta o teto de segurança e
    explica ao usuário por que os envios estão segurando (FR-046)."""
    try:
        dados = _requisitar("/instance/wa_messages_limits", "GET", None,
                            {"token": credencial}, cfg)
    except ErroWhatsApp:
        return {"disponivel": False, "pode_enviar": None, "mensagem": ""}
    return {
        "disponivel": bool(dados.get("reachable")),
        "pode_enviar": dados.get("can_send_new_messages"),
        "mensagem": str(dados.get("message") or ""),
    }


def definir_espacamento(credencial: str, minimo_seg: int, maximo_seg: int,
                        cfg: Config = None) -> None:
    """Espaçamento nativo entre mensagens. Parte da proteção da conta —
    decisão da plataforma, nunca configuração do usuário (D30/D32)."""
    if maximo_seg < minimo_seg:
        maximo_seg = minimo_seg
    _requisitar("/instance/updateDelaySettings", "POST",
                {"msg_delay_min": max(0, int(minimo_seg)),
                 "msg_delay_max": max(0, int(maximo_seg))},
                {"token": credencial}, cfg)
