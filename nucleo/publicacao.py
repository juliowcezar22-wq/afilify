"""
PUBLICAÇÃO — uma oferta saindo em um destino

Antes, publicar era "marcar a oferta como enviada". Isso amarrava três
coisas que são diferentes: a oportunidade encontrada, a decisão de publicar,
e cada envio de fato. Com dois destinos, ou com uma segunda chance depois de
queda de preço, aquele modelo não tinha onde guardar a segunda linha.

Aqui a Publicação tem identidade própria: (oferta, destino, ciclo).

    ciclo 1  primeira vez que a oferta sai naquele destino
    ciclo 2  o preço caiu abaixo do publicado, e ela volta como novidade

A proteção contra envio duplicado, que a chave antiga dava de graça, é
preservada pela chave de idempotência — que inclui o ciclo.
"""

from __future__ import annotations

import uuid

from nucleo.comum import agora

AGENDADA = "agendada"
ENVIANDO = "enviando"
ENVIADA = "enviada"
FALHOU = "falhou"
CANCELADA = "cancelada"


def chave(oferta_id: str, destino_id: str, ciclo: int) -> str:
    return f"{oferta_id}:{destino_id}:{ciclo}"


def ciclo_atual(con, oferta_id: str, destino_id: str) -> int:
    """Em que rodada esta oferta está, naquele destino."""
    linha = con.execute(
        "SELECT MAX(ciclo) AS c FROM publicacoes WHERE oferta_id = ? AND destino_id = ?",
        (oferta_id, destino_id)).fetchone()
    return int(linha["c"] or 0) if linha else 0


def ja_publicada(con, oferta_id: str, destino_id: str, ciclo: int) -> bool:
    return bool(con.execute(
        "SELECT 1 FROM publicacoes WHERE chave_idempotencia = ?",
        (chave(oferta_id, destino_id, ciclo),)).fetchone())


def agendar(con, ctx, oferta_id: str, destino_id: str, quando,
            preco: float = None, ciclo: int = None) -> str | None:
    """Cria a publicação. Devolve None quando ela já existe.

    Devolver None em vez de estourar é de propósito: uma coleta que roda de
    novo, ou um processo reiniciado, não pode virar mensagem repetida no
    grupo — mas também não pode virar erro.
    """
    if ciclo is None:
        ciclo = max(1, ciclo_atual(con, oferta_id, destino_id))
    if ja_publicada(con, oferta_id, destino_id, ciclo):
        return None
    pid = str(uuid.uuid4())
    ts = agora().isoformat(timespec="seconds")
    con.execute(
        "INSERT INTO publicacoes (id, workspace_id, projeto_id, automacao_id, oferta_id, "
        "destino_id, estado, tentativa, ciclo, chave_idempotencia, preco_publicado, "
        "agendada_para, criado_em, atualizado_em) "
        "VALUES (?, ?, ?, ?, ?, ?, 'agendada', 1, ?, ?, ?, ?, ?, ?)",
        (pid, ctx.workspace_id, ctx.projeto_id, ctx.automacao_id, oferta_id, destino_id,
         ciclo, chave(oferta_id, destino_id, ciclo), preco,
         quando.isoformat(timespec="seconds") if quando else None, ts, ts))
    con.commit()
    return pid


def agendar_em_todos(con, ctx, oferta_id: str, momento, preco: float = None,
                     intervalo_seg: int = 0) -> list:
    """Uma oferta, todos os destinos da automação — espaçados.

    O intervalo entre destinos existe para proteger a conta: disparar a
    mesma mensagem em três grupos no mesmo segundo é o padrão que derruba
    número. É decisão da plataforma, não configuração do usuário (D30).
    """
    from datetime import timedelta
    criadas = []
    for i, destino in enumerate(sorted(ctx.destinos, key=lambda d: d.ordem)):
        if not destino.id:
            continue
        quando = momento + timedelta(seconds=intervalo_seg * i) if momento else None
        pid = agendar(con, ctx, oferta_id, destino.id, quando, preco)
        if pid:
            criadas.append(pid)
    return criadas


def marcar_enviando(con, publicacao_id: str) -> bool:
    """Reserva a publicação para este processo. False = outro já pegou."""
    ts = agora().isoformat(timespec="seconds")
    cur = con.execute(
        "UPDATE publicacoes SET estado = 'enviando', atualizado_em = ? "
        "WHERE id = ? AND estado = 'agendada'", (ts, publicacao_id))
    con.commit()
    return bool(cur.rowcount)


def concluir(con, publicacao_id: str, id_externo: str, mensagem: str = "") -> None:
    ts = agora().isoformat(timespec="seconds")
    con.execute(
        "UPDATE publicacoes SET estado = 'enviada', id_externo = ?, mensagem_enviada = ?, "
        "enviada_em = ?, atualizado_em = ? WHERE id = ?",
        (id_externo, mensagem, ts, ts, publicacao_id))
    con.commit()


def falhar(con, publicacao_id: str, motivo: str) -> None:
    """`motivo` é lido pelo usuário — frase, não traço de pilha."""
    ts = agora().isoformat(timespec="seconds")
    con.execute(
        "UPDATE publicacoes SET estado = 'falhou', motivo_falha = ?, "
        "tentativa = tentativa + 1, atualizado_em = ? WHERE id = ?",
        (motivo, ts, publicacao_id))
    con.commit()


def repetir(con, publicacao_id: str) -> bool:
    """Devolve uma publicação falha para a fila."""
    ts = agora().isoformat(timespec="seconds")
    cur = con.execute(
        "UPDATE publicacoes SET estado = 'agendada', motivo_falha = '', atualizado_em = ? "
        "WHERE id = ? AND estado = 'falhou'", (ts, publicacao_id))
    con.commit()
    return bool(cur.rowcount)


def deve_republicar(con, oferta_id: str, destino_id: str, preco_atual: float,
                    queda_minima_pct: int = 15) -> bool:
    """A oferta volta ao mesmo destino? Só se o preço caiu de verdade.

    Compara com o preço DA PUBLICAÇÃO anterior, não com a última coleta:
    olhar a coleta faria a oferta ir e voltar a cada oscilação de centavos.
    """
    if preco_atual is None:
        return False
    linha = con.execute(
        "SELECT preco_publicado FROM publicacoes WHERE oferta_id = ? AND destino_id = ? "
        "AND estado = 'enviada' ORDER BY ciclo DESC LIMIT 1",
        (oferta_id, destino_id)).fetchone()
    if not linha or linha["preco_publicado"] is None:
        return False
    anterior = float(linha["preco_publicado"])
    if anterior <= 0:
        return False
    queda = (anterior - preco_atual) / anterior * 100
    return queda >= queda_minima_pct


def abrir_ciclo(con, oferta_id: str, destino_id: str) -> int:
    """A próxima rodada daquela oferta naquele destino."""
    return ciclo_atual(con, oferta_id, destino_id) + 1


def fila(con, automacao_id: str, momento, limite: int = 20) -> list:
    """Publicações prontas para sair agora, na ordem."""
    return list(con.execute(
        "SELECT p.id, p.oferta_id, p.destino_id, p.ciclo, d.alvo, d.nome AS destino_nome "
        "  FROM publicacoes p JOIN destinos d ON d.id = p.destino_id "
        " WHERE p.automacao_id = ? AND p.estado = 'agendada' "
        "   AND (p.agendada_para IS NULL OR p.agendada_para <= ?) "
        " ORDER BY p.agendada_para, p.criado_em LIMIT ?",
        (automacao_id, momento.isoformat(timespec="seconds"), limite)))
