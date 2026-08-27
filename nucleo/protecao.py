"""
PROTEÇÃO DA CONTA — o teto que o usuário não precisa conhecer

Duas automações no mesmo número somam um volume que nenhuma delas tem
sozinha. Quem paga essa conta é o número, não a automação — então o teto
vive na CONEXÃO.

Isto é infraestrutura, não preferência: não aparece como campo de
formulário. Aparece só quando segura uma publicação, e aí como motivo em
linguagem comum (FR-046, D32).
"""

from __future__ import annotations

from datetime import timedelta

from nucleo.comum import agora

# Teto padrão por hora, por número conectado. Conservador de propósito: o
# custo de segurar uma publicação é ela sair alguns minutos depois; o custo
# de perder o número é a operação inteira.
TETO_HORA_PADRAO = 40

# Espaçamento mínimo entre destinos da mesma oferta. Três grupos recebendo a
# mesma mensagem no mesmo segundo é o padrão que derruba conta.
INTERVALO_ENTRE_DESTINOS_SEG = 45


def teto_da_conexao(con, workspace_id: str) -> int:
    linha = con.execute(
        "SELECT teto_envios_conexao_hora FROM limites_plano WHERE workspace_id = ?",
        (workspace_id,)).fetchone()
    return int(linha["teto_envios_conexao_hora"]) if linha and linha["teto_envios_conexao_hora"] \
        else TETO_HORA_PADRAO


def enviadas_na_ultima_hora(con, conexao_id: str) -> int:
    corte = (agora() - timedelta(hours=1)).isoformat(timespec="seconds")
    linha = con.execute(
        "SELECT COUNT(*) AS n FROM publicacoes p JOIN destinos d ON d.id = p.destino_id "
        "WHERE d.conexao_id = ? AND p.estado = 'enviada' AND p.enviada_em >= ?",
        (conexao_id, corte)).fetchone()
    return int(linha["n"] or 0) if linha else 0


def pode_enviar(con, conexao_id: str, workspace_id: str) -> tuple:
    """(pode, motivo). O motivo é exibível.

    Quando o teto segura, o usuário precisa entender que não é defeito — é
    a plataforma protegendo o número dele.
    """
    teto = teto_da_conexao(con, workspace_id)
    usadas = enviadas_na_ultima_hora(con, conexao_id)
    if usadas < teto:
        return True, ""
    return False, ("Segurando os envios por enquanto para proteger a saúde da sua conta. "
                   "As publicações continuam na fila e saem em seguida.")


def espacamento_seguro(intervalo_medio_seg: float) -> tuple:
    """Faixa de espaçamento nativo a pedir à plataforma de mensagens.

    Derivada do ritmo real: um grupo que publica a cada 5 minutos não
    precisa do mesmo cuidado de um que publica a cada 30 segundos.
    """
    if intervalo_medio_seg >= 300:
        return 0, 3
    if intervalo_medio_seg >= 120:
        return 1, 5
    return 3, 10
