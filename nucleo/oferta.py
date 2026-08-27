"""
OFERTA — a oportunidade encontrada, e o que acontece com ela

O estado que dá nome a este módulo é `retida`.

Antes, uma oferta que não pudesse ser publicada — sessão do Mercado Livre
expirada, conexão caída, link não gerado — virava ERRO e sumia da fila. Na
prática isso é jogar fora oportunidade por um problema temporário nosso.

`retida` guarda a oferta e o motivo. Quando a causa é resolvida, ela volta
sozinha. Nada se perde por falha de infraestrutura (FR-042, SC-006).

    nova ──→ pronta ──→ publicada
      │        │
      └────────┴──→ retida ──→ (causa resolvida) ──→ pronta
                     │
                     └──→ expirada  (passou da validade esperando)
"""

from __future__ import annotations

from datetime import timedelta

from nucleo.comum import agora

NOVA = "nova"
PRONTA = "pronta"
RETIDA = "retida"
PUBLICADA = "publicada"
IGNORADA = "ignorada"
EXPIRADA = "expirada"

# Motivos de retenção que a Afilify sabe resolver sozinha. Cada um vira uma
# frase na tela e uma condição de liberação.
SEM_LINK = "sem_link"
CONEXAO_ML = "conexao_mercadolivre"
CONEXAO_DESTINO = "conexao_destino"

FRASES = {
    SEM_LINK: "Aguardando o link de afiliado ser gerado.",
    CONEXAO_ML: "Sua conexão com o Mercado Livre expirou. "
                "Reconecte sua conta para continuar gerando ofertas.",
    CONEXAO_DESTINO: "A conta de WhatsApp desta automação está desconectada.",
}


def reter(con, oferta_id: str, motivo: str) -> None:
    """Segura a oferta em vez de descartá-la."""
    con.execute(
        "UPDATE ofertas_projeto SET estado = 'retida', motivo_retencao = ?, atualizado_em = ? "
        "WHERE id = ? AND estado IN ('nova','pronta','retida')",
        (motivo, agora().isoformat(timespec="seconds"), oferta_id))
    con.commit()


def reter_todas(con, projeto_id: str, motivo: str) -> int:
    """Segura o que ainda não saiu. Usado quando a causa é geral — a sessão
    do Mercado Livre expirou, por exemplo, e nenhuma oferta consegue link."""
    cur = con.execute(
        "UPDATE ofertas_projeto SET estado = 'retida', motivo_retencao = ?, atualizado_em = ? "
        "WHERE projeto_id = ? AND estado IN ('nova','pronta')",
        (motivo, agora().isoformat(timespec="seconds"), projeto_id))
    con.commit()
    return cur.rowcount or 0


def liberar(con, projeto_id: str, motivo: str) -> int:
    """A causa foi resolvida: o que estava esperando por ELA volta à fila.

    Libera só o que foi retido por aquele motivo — uma reconexão do
    WhatsApp não deve soltar ofertas que esperam link do Mercado Livre.
    """
    cur = con.execute(
        "UPDATE ofertas_projeto SET estado = 'pronta', motivo_retencao = '', atualizado_em = ? "
        "WHERE projeto_id = ? AND estado = 'retida' AND motivo_retencao = ?",
        (agora().isoformat(timespec="seconds"), projeto_id, motivo))
    con.commit()
    return cur.rowcount or 0


def expirar_vencidas(con, projeto_id: str, validade_horas: int) -> int:
    """Oferta velha demais sai da fila — promoção de três dias atrás no grupo
    é pior que silêncio. Sai como `expirada`, não como erro: não foi falha."""
    if not validade_horas:
        return 0
    corte = (agora() - timedelta(hours=validade_horas)).isoformat(timespec="seconds")
    cur = con.execute(
        "UPDATE ofertas_projeto SET estado = 'expirada', atualizado_em = ? "
        "WHERE projeto_id = ? AND estado IN ('nova','pronta','retida') AND criado_em < ?",
        (agora().isoformat(timespec="seconds"), projeto_id, corte))
    con.commit()
    return cur.rowcount or 0


def frase_da_retencao(motivo: str) -> str:
    """O que o usuário lê. Motivo desconhecido não vira código na tela."""
    return FRASES.get(motivo, "Esta oferta está aguardando para ser publicada.")


def contar_por_estado(con, projeto_id: str) -> dict:
    return {
        r["estado"]: r["n"] for r in con.execute(
            "SELECT estado, COUNT(*) AS n FROM ofertas_projeto WHERE projeto_id = ? "
            "GROUP BY estado", (projeto_id,))
    }
