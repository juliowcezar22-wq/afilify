"""
COMANDOS — o que o painel pede e o motor faz

Em produção, painel e motor são serviços separados que só compartilham o
banco. Quando o usuário clica em "Testar busca", quem sabe fazer isso é o
motor — e não existe outro caminho entre os dois.

Esta tabela é esse caminho: o painel deixa um pedido, o motor pega, executa
e devolve o resultado no mesmo registro.

    # no motor, dentro do ciclo do daemon
    comandos.atender(con, {"testar_busca": minha_funcao})

Duas garantias que o desenho precisa dar:

  · pedido velho não é executado. Se o motor estava parado quando o usuário
    clicou, executar dez minutos depois seria pior que não executar — a tela
    já desistiu, e o usuário não está mais olhando.
  · um pedido não é atendido duas vezes, mesmo com dois processos rodando.
"""

from __future__ import annotations

import json
import uuid

from nucleo.comum import agora

# Quanto tempo um pedido continua valendo. Curto de propósito: é a espera de
# alguém olhando para a tela.
VALIDADE_SEG = 180

PENDENTE = "pendente"
EXECUTANDO = "executando"
CONCLUIDO = "concluido"
FALHOU = "falhou"
EXPIRADO = "expirado"


def criar(con, tipo: str, parametros: dict, workspace_id: str = "",
          validade_seg: int = VALIDADE_SEG) -> str:
    """Registra um pedido. Devolve o id para acompanhar."""
    from nucleo.comum import WORKSPACE_PADRAO
    from datetime import timedelta

    cid = str(uuid.uuid4())
    ts = agora()
    con.execute(
        "INSERT INTO comandos (id, workspace_id, tipo, parametros, estado, resultado, "
        "erro, expira_em, criado_em, atualizado_em) "
        "VALUES (?, ?, ?, ?, 'pendente', '{}', '', ?, ?, ?)",
        (cid, workspace_id or WORKSPACE_PADRAO, tipo,
         json.dumps(parametros, ensure_ascii=False),
         (ts + timedelta(seconds=validade_seg)).isoformat(timespec="seconds"),
         ts.isoformat(timespec="seconds"), ts.isoformat(timespec="seconds")))
    con.commit()
    return cid


def _expirar_velhos(con) -> int:
    """Pedido cuja janela passou não é executado — é marcado como expirado.

    A tela traduz isso para "a automação não estava rodando", que é a
    verdade, em vez de girar para sempre esperando algo que não vem.
    """
    ts = agora().isoformat(timespec="seconds")
    cur = con.execute(
        "UPDATE comandos SET estado = 'expirado', atualizado_em = ? "
        "WHERE estado IN ('pendente','executando') AND expira_em < ?", (ts, ts))
    con.commit()
    return cur.rowcount or 0


def _tomar(con, tipos: list) -> dict | None:
    """Pega UM pedido pendente e o marca como em execução.

    O UPDATE condicionado ao estado é o que impede dois processos atenderem
    o mesmo pedido: só um consegue mudar a linha de 'pendente'.
    """
    marcadores = ",".join("?" for _ in tipos)
    linha = con.execute(
        f"SELECT id, tipo, parametros FROM comandos "
        f"WHERE estado = 'pendente' AND tipo IN ({marcadores}) "
        f"ORDER BY criado_em LIMIT 1", tuple(tipos)).fetchone()
    if not linha:
        return None
    ts = agora().isoformat(timespec="seconds")
    cur = con.execute(
        "UPDATE comandos SET estado = 'executando', atualizado_em = ? "
        "WHERE id = ? AND estado = 'pendente'", (ts, linha["id"]))
    con.commit()
    if not cur.rowcount:
        return None          # outro processo chegou primeiro
    try:
        parametros = json.loads(linha["parametros"] or "{}")
    except (ValueError, TypeError):
        parametros = {}
    return {"id": linha["id"], "tipo": linha["tipo"], "parametros": parametros}


def concluir(con, cid: str, resultado: dict) -> None:
    con.execute(
        "UPDATE comandos SET estado = 'concluido', resultado = ?, atualizado_em = ? WHERE id = ?",
        (json.dumps(resultado, ensure_ascii=False), agora().isoformat(timespec="seconds"), cid))
    con.commit()


def falhar(con, cid: str, motivo: str) -> None:
    """`motivo` vai para a tela — precisa ser frase, não traço de pilha."""
    con.execute(
        "UPDATE comandos SET estado = 'falhou', erro = ?, atualizado_em = ? WHERE id = ?",
        (motivo, agora().isoformat(timespec="seconds"), cid))
    con.commit()


def atender(con, executores: dict, limite: int = 3) -> int:
    """Atende até `limite` pedidos. Devolve quantos foram atendidos.

    Um executor que estoura não derruba o ciclo do motor: o pedido é marcado
    como falho, com uma frase para o usuário, e a vida segue.
    """
    _expirar_velhos(con)
    atendidos = 0
    for _ in range(limite):
        pedido = _tomar(con, list(executores))
        if not pedido:
            break
        try:
            resultado = executores[pedido["tipo"]](con, pedido["parametros"])
            concluir(con, pedido["id"], resultado or {})
        except Exception as e:
            falhar(con, pedido["id"], _frase(e))
        atendidos += 1
    return atendidos


def _frase(e: Exception) -> str:
    """Erro técnico vira frase de produto. O detalhe fica no registro
    técnico, não na tela de quem só quer saber se deu certo."""
    texto = str(e).strip()
    if not texto or len(texto) > 200 or "Traceback" in texto:
        return "Não conseguimos concluir agora. Tente de novo em instantes."
    return texto


def consultar(con, cid: str) -> dict:
    """Estado e resultado, para o painel acompanhar."""
    _expirar_velhos(con)
    linha = con.execute(
        "SELECT estado, resultado, erro FROM comandos WHERE id = ?", (cid,)).fetchone()
    if not linha:
        return {"estado": "desconhecido", "resultado": {}, "erro": ""}
    try:
        resultado = json.loads(linha["resultado"] or "{}")
    except (ValueError, TypeError):
        resultado = {}
    return {"estado": linha["estado"], "resultado": resultado, "erro": linha["erro"] or ""}
