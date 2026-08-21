#!/usr/bin/env python3
"""
AGENTE ML — PROMOÇÕES DE PERFUME
================================

Porte do fluxo n8n "BOT DE Promoções do ML - PERFUMES (v2) Sem I.A" para um
processo único que roda na VPS. Sem n8n e sem Google Sheets — o estado vive
num SQLite ao lado do script.

    BLOCO 1  varre /ofertas?category=MLB6284 e filtra perfume de verdade
    BLOCO 2  transforma a URL do produto no SEU link de afiliado (por sessão)
    BLOCO 3  monta a mensagem conforme o badge e envia no grupo (uazapi)

Comandos:
    python3 agente_ml.py rodar       daemon — faz os 3 blocos no horário certo
    python3 agente_ml.py buscar      só o BLOCO 1 (+2), agora
    python3 agente_ml.py links       só o BLOCO 2, para o que ainda não tem
    python3 agente_ml.py enviar      só o BLOCO 3, uma rodada
    python3 agente_ml.py listar      o que está na fila
    python3 agente_ml.py testar      confere cookie, uazapi e banco

Só biblioteca padrão: nada de pip, nada de venv.
"""

from __future__ import annotations

from __future__ import annotations
import argparse
import fcntl
import gzip
import html as _html
import json
import math
import os
import random
import re
import signal
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from nucleo.comum import *  # noqa: F401,F403
from mercadolivre.config import *  # noqa: F401,F403
from nucleo.comum import AZUL, CINZA, FIM, VERDE, VERMELHO, AMARELO
from mercadolivre.buscador import (
    achar_marca, bloco1_buscar, bloco2_links, baixar_busca, baixar_pagina,
    cookie_ml, filtrar_marca, filtrar_titulo, foto_para_envio, gerar_links,
    normalizar,
    contexto_da_busca, extrair_contexto, extrair_ofertas, extrair_ofertas_json,
    galeria_do_produto, limpar_url, marca_do_card, salvar_oferta,
    total_de_paginas,
)
from mercadolivre.clonador import (
    bloco4_clonar,
)

# BLOCO 3 — MENSAGEM E ENVIO NO GRUPO
# ══════════════════════════════════════════════════════════════════════


def dormir(segundos: float) -> bool:
    """Pausa que acorda no SIGTERM. False = fomos interrompidos."""
    fim = time.monotonic() + segundos
    while not _parar:
        resta = fim - time.monotonic()
        if resta <= 0:
            return True
        time.sleep(min(0.5, resta))
    return False


def dentro_da_janela(momento: datetime, plano: dict) -> bool:
    return (
        hora_do_dia(momento, plano["inicio"])
        <= momento
        < hora_do_dia(momento, plano["fim"])
    )


def fila_de_envio(con: sqlite3.Connection, limite: int) -> list[sqlite3.Row]:
    ordem = {
        "novas": "criado_em DESC",
        "antigas": "criado_em ASC",
        "maior_desconto": "desconto_pct DESC, criado_em DESC",
    }.get(ORDEM_ENVIO, "criado_em DESC")

    condicoes = ["status_envio = 'PENDENTE'", "link_afiliado != ''",
                 "perfil = ?"]
    # tentativa que falhou fica de molho até a hora marcada
    condicoes.append("(proxima_tentativa IS NULL OR proxima_tentativa <= ?)")
    params: list = [PERFIL_ATIVO, agora().isoformat(timespec="seconds")]
    validade = ritmo_cfg(con).get("validade_horas", VALIDADE_HORAS)
    if validade:
        corte = (agora() - timedelta(hours=validade)).isoformat(timespec="seconds")
        condicoes.append("criado_em >= ?")
        params.append(corte)

    sql = f"SELECT * FROM ofertas WHERE {' AND '.join(condicoes)} ORDER BY {ordem}"
    linhas = con.execute(sql, params).fetchall()
    if limite > 0:
        linhas = priorizar(con, linhas)[:limite]
    return linhas


def priorizar(con: sqlite3.Connection, linhas: list) -> list:
    """Reordena a fila para segurar a proporção de importados do dia.

    Não é ordenação fixa: olha o que JÁ saiu hoje. Se importado está abaixo
    da cota, ele fura na frente; se passou, a vez é do nacional. Ao longo do
    dia converge para PROPORCAO_IMPORTADOS sem deixar o grupo só com um tipo.
    """
    alvo = ritmo_cfg(con).get("proporcao_preferidas", PROPORCAO_IMPORTADOS)
    if not alvo or not linhas:
        return list(linhas)

    hoje = agora().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    contagem = {
        r["familia"]: r["n"]
        for r in con.execute(
            "SELECT familia, COUNT(*) n FROM ofertas WHERE status_envio='ENVIADO' "
            "AND enviado_em >= ? AND perfil = ? GROUP BY familia",
            (hoje, PERFIL_ATIVO),
        )
    }
    enviados = sum(contagem.values())
    importados = sum(contagem.get(f, 0) for f in FAMILIAS_IMPORTADAS)
    proporcao = (importados / enviados) if enviados else 0.0

    quer_importado = proporcao < alvo
    def peso(r):
        # o clone é a razão de existir do monitor: o rival achou, sai na frente
        rival = 0 if r["origem"] == "clone" else 1
        e_importado = r["familia"] in FAMILIAS_IMPORTADAS
        return (rival, 0 if e_importado == quer_importado else 1)

    return sorted(linhas, key=peso)


def bloco3_enviar(
    con: sqlite3.Connection,
    limite: int = ENVIO_POR_EXECUCAO,
    seco: bool = False,
    forcar: bool = False,
) -> int:
    momento = agora()
    plano = plano_do_dia(con, momento)
    if not forcar and not dentro_da_janela(momento, plano):
        info(
            f"BLOCO 3 — fora da janela "
            f"{hora_do_dia(momento, plano['inicio']):%H:%M}–"
            f"{hora_do_dia(momento, plano['fim']):%H:%M}, nada enviado"
        )
        return 0

    if not forcar:
        ja = enviadas_hoje(con, momento)
        if ja >= plano["cota"]:
            info(f"BLOCO 3 — cota do dia atingida ({ja}/{plano['cota']})")
            return 0
        limite = min(limite, plano["cota"] - ja) if limite else plano["cota"] - ja

    reconciliar_entregas(con)
    destino = canal_cfg(con)["grupo"]
    fila = fila_de_envio(con, limite)
    if not fila:
        info("BLOCO 3 — nenhuma oferta pendente com link pronto")
        return 0

    if not seco and not uazapi_configurado():
        aviso("uazapi incompleto no .env — modo simulação")
        seco = True

    enviadas = 0
    for i, linha in enumerate(fila, 1):
        texto = montar_mensagem(linha, con)
        print(f"\n{AZUL}{'─' * 70}{FIM}")
        print(f"{AZUL}{i}/{len(fila)} · {linha['badge']} · {linha['mlb_id']}{FIM}")
        print(f"{AZUL}{'─' * 70}{FIM}\n{texto}\n")

        if seco:
            aviso("simulação — nada enviado")
            continue

        # idempotência: sem reserva, sem POST. Se outra execução já enviou
        # (ou está enviando), esta oferta é pulada — nunca duplica no grupo.
        if not reservar_entrega(con, linha["mlb_id"], destino):
            info(f"pulada {linha['mlb_id']}: entrega já reservada/concluída")
            continue

        pausa = random.randint(*PAUSA_HUMANIZADA)
        info(f"pausa humanizada de {pausa}s")
        if not dormir(pausa):
            # chegou SIGTERM durante a pausa: sair sem disparar a mensagem,
            # senão o systemd mata no meio do POST e a oferta fica sem status
            aviso("encerrando antes de enviar — oferta segue pendente")
            break

        ts = agora().isoformat(timespec="seconds")
        try:
            msg_id = uazapi_enviar(texto, foto_para_envio(linha), destino)
        except (HttpErro, RuntimeError) as e:
            falhar_entrega(con, linha["mlb_id"], str(e), destino)
            tentativas = (linha["tentativas"] or 0) + 1
            if tentativas >= ENVIO_TENTATIVAS:
                erro(f"envio falhou {tentativas}x, desistindo ({linha['mlb_id']}): {e}")
                con.execute(
                    "UPDATE ofertas SET status_envio='ERRO', erro=?, tentativas=?, "
                    "atualizado_em=? WHERE mlb_id=?",
                    (str(e)[:300], tentativas, ts, linha["mlb_id"]),
                )
            else:
                espera = ENVIO_ESPERA_TENTATIVA * tentativas
                proxima = (momento + timedelta(minutes=espera)).isoformat(
                    timespec="seconds"
                )
                aviso(
                    f"envio falhou ({linha['mlb_id']}): {e} — tentativa "
                    f"{tentativas}/{ENVIO_TENTATIVAS}, volta em {espera}min"
                )
                con.execute(
                    "UPDATE ofertas SET erro=?, tentativas=?, proxima_tentativa=?, "
                    "atualizado_em=? WHERE mlb_id=?",
                    (str(e)[:300], tentativas, proxima, ts, linha["mlb_id"]),
                )
            con.commit()
            continue

        con.execute(
            "UPDATE ofertas SET status_envio='ENVIADO', erro='', "
            "proxima_tentativa=NULL, enviado_em=?, atualizado_em=?, "
            "preco_enviado=preco_promocional WHERE mlb_id=?",
            (ts, ts, linha["mlb_id"]),
        )
        con.commit()
        concluir_entrega(con, linha["mlb_id"], msg_id, destino)
        enviadas += 1
        ok(f"enviada no grupo (id {msg_id})")

    return enviadas


# ══════════════════════════════════════════════════════════════════════
# DAEMON — substitui os três Schedule Triggers do n8n
# ══════════════════════════════════════════════════════════════════════
_parar = False


def _sinal(_num, _frame):
    global _parar
    _parar = True
    print()
    info("sinal recebido, encerrando após o ciclo atual…")


def hora_de_buscar(con: sqlite3.Connection, momento: datetime) -> bool:
    if momento.hour not in ritmo_cfg(con)["busca_horas"]:
        return False
    ultima = ler_estado(con, "ultima_busca")
    if not ultima:
        return True
    try:
        anterior = datetime.fromisoformat(ultima)
    except ValueError:
        return True
    return (anterior.date(), anterior.hour) != (momento.date(), momento.hour)


# ── o plano do dia ───────────────────────────────────────────────────
def hora_do_dia(momento: datetime, hora: float) -> datetime:
    """8.5 → hoje às 08:30."""
    minutos = max(0, min(int(round(hora * 60)), 23 * 60 + 59))
    return momento.replace(
        hour=minutos // 60, minute=minutos % 60, second=0, microsecond=0
    )


def plano_do_dia(con: sqlite3.Connection, momento: datetime) -> dict:
    """Sorteia cota e janela UMA vez por dia, e guarda.

    É o que faz o dia parecer conduzido por gente: hoje 62 ofertas das 08h14
    às 22h03, amanhã 79 das 08h51 às 21h44.
    """
    hoje = momento.date().isoformat()
    bruto = ler_estado(con, "plano_do_dia")
    if bruto:
        try:
            plano = json.loads(bruto)
            if plano.get("data") == hoje:
                return plano
        except (json.JSONDecodeError, ValueError):
            pass

    cfg = ritmo_cfg(con)
    plano = {
        "data": hoje,
        "cota": random.randint(*cfg["envios_por_dia"]),
        "inicio": random.uniform(*cfg["inicio_janela"]),
        "fim": random.uniform(*cfg["fim_janela"]),
        "coletas": list(cfg["busca_horas"]),   # congela as coletas do dia
    }
    gravar_estado(con, "plano_do_dia", json.dumps(plano))
    info(
        f"plano de hoje: {plano['cota']} ofertas entre "
        f"{hora_do_dia(momento, plano['inicio']):%H:%M} e "
        f"{hora_do_dia(momento, plano['fim']):%H:%M}"
    )
    return plano


# ── trava de instância única ─────────────────────────────────────────
# Trava POR PERFIL: dois grupos são duas operações independentes — o daemon
# de casa não pode ser barrado pelo de perfumes. O que continua proibido é
# dois processos do MESMO perfil (mesmo grupo de WhatsApp).
ARQUIVO_TRAVA = os.path.join(DADOS, f".lock-{PERFIL_ATIVO}")


class Trava:
    """Impede dois processos publicando no mesmo grupo ao mesmo tempo.

    Sem isto, um `enviar` manual rodando junto do daemon manda a mesma
    oferta duas vezes — ou duas ofertas coladas fora do ritmo.
    """

    def __init__(self, caminho: str = ARQUIVO_TRAVA):
        self.caminho = caminho
        self.arquivo = None

    def __enter__(self):
        self.arquivo = open(self.caminho, "a+")
        try:
            fcntl.flock(self.arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.arquivo.seek(0)
            dono = self.arquivo.read().strip() or "?"
            self.arquivo.close()
            self.arquivo = None
            raise RuntimeError(
                f"já existe um agente rodando (pid {dono}).\n"
                "  Pare o outro antes, senão o grupo recebe mensagem duplicada."
            )
        self.arquivo.seek(0)
        self.arquivo.truncate()
        self.arquivo.write(str(os.getpid()))
        self.arquivo.flush()
        return self

    def __exit__(self, *_):
        if self.arquivo:
            fcntl.flock(self.arquivo.fileno(), fcntl.LOCK_UN)
            self.arquivo.close()
            self.arquivo = None


def dono_da_trava() -> str:
    """PID do processo que está com a trava, ou '' se estiver livre."""
    if not os.path.exists(ARQUIVO_TRAVA):
        return ""
    with open(ARQUIVO_TRAVA, "a+") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return ""
        except OSError:
            f.seek(0)
            return f.read().strip() or "?"


def purgar_vencidas(con: sqlite3.Connection) -> int:
    """Apaga pendentes velhas demais para publicar. A oferta entra ~3x mais
    rápido do que sai, então sem isto a fila cresce para sempre."""
    if not VALIDADE_HORAS:
        return 0
    limite = (agora() - timedelta(hours=VALIDADE_HORAS)).isoformat(timespec="seconds")
    return con.execute(
        "DELETE FROM ofertas WHERE status_envio != 'ENVIADO' AND criado_em < ? "
        "AND perfil = ?", (limite, PERFIL_ATIVO),
    ).rowcount


def enviadas_hoje(con: sqlite3.Connection, momento: datetime) -> int:
    return con.execute(
        "SELECT COUNT(*) n FROM ofertas WHERE status_envio = 'ENVIADO' "
        "AND enviado_em >= ? AND perfil = ?",
        (momento.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
         PERFIL_ATIVO),
    ).fetchone()["n"]


def fim_do_ciclo(momento: datetime, plano: dict) -> datetime:
    """A próxima coleta, ou o fim da janela de envio — o que vier antes.

    É o prazo dentro do qual a fila atual precisa ser distribuída.
    """
    marcos = [
        momento.replace(hour=h, minute=0, second=0, microsecond=0)
        for h in sorted(plano.get("coletas", BUSCA_HORAS))
    ]
    marcos.append(hora_do_dia(momento, plano["fim"]))
    futuros = [m for m in marcos if m > momento]
    # passou de todos os marcos hoje: o ciclo fecha na abertura de amanhã
    return min(futuros) if futuros else (
        hora_do_dia(momento, plano["inicio"]) + timedelta(days=1)
    )


def ritmo(
    con: sqlite3.Connection | None,
    momento: datetime,
    fila: int,
    resta_dia: float,
    resta_ciclo: float,
    cota_total: int,
    ja_enviadas: int | None = None,
) -> float | None:
    """Minutos médios entre envios. None = não enviar mais hoje.

    Duas restrições, as duas são um piso de lentidão — vale a mais lenta:

    1. Espalhar a COTA do dia pelo que resta do dia. Sem isso a fila cheia da
       manhã queima o teto até meio-dia e o grupo fica mudo à tarde.
    2. Espalhar a FILA pelo que resta até a próxima coleta. Sem isso 5 ofertas
       às 7h saem todas às 7h05 e o grupo fica parado até meio-dia.
    """
    if ja_enviadas is None:
        ja_enviadas = enviadas_hoje(con, momento) if con is not None else 0
    restam = cota_total - ja_enviadas
    if restam <= 0:
        return None
    pelo_dia = resta_dia / restam
    pelo_ciclo = resta_ciclo / fila
    return max(pelo_dia, pelo_ciclo)


def sortear_intervalo(base: float) -> float:
    """Sorteia um intervalo cuja MÉDIA é `base`, com a forma do MAENO.

    Lognormal: muitos intervalos curtos, alguns médios, poucos longos — que
    é exatamente o perfil medido no grupo dele. A média fica igual a `base`,
    então a cota do dia continua fechando na hora certa.
    """
    mais_curto, mais_longo = ENVIO_INTERVALO_LIMITES
    sigma = max(ENVIO_DISPERSAO, 0.01)
    # numa lognormal, média = mediana × e^(σ²/2). Invertendo para que a
    # média saia igual a `base`:
    mediana = max(base, 0.1) / math.exp(sigma * sigma / 2)
    minutos = random.lognormvariate(math.log(mediana), sigma)
    return min(max(minutos, mais_curto), mais_longo)


def calcular_intervalo(con: sqlite3.Connection, momento: datetime) -> float:
    """Minutos até o próximo envio, em função da fila e do tempo restante."""
    if not ENVIO_ADAPTATIVO:
        return random.uniform(*ENVIO_INTERVALO_FIXO)

    mais_curto, mais_longo = ENVIO_INTERVALO_LIMITES
    fila = len(fila_de_envio(con, 0))
    if fila <= 0:
        return mais_longo          # nada a mandar: volta a olhar daqui a pouco

    plano = plano_do_dia(con, momento)
    fim_janela = hora_do_dia(momento, plano["fim"])
    resta_dia = max(1.0, (fim_janela - momento).total_seconds() / 60)
    resta_ciclo = max(
        1.0, (fim_do_ciclo(momento, plano) - momento).total_seconds() / 60
    )

    base = ritmo(con, momento, fila, resta_dia, resta_ciclo, plano["cota"])
    return mais_longo if base is None else sortear_intervalo(base)


def agendar_proximo_envio(con: sqlite3.Connection, momento: datetime) -> datetime:
    """Sorteia quando será o próximo envio e persiste."""
    minutos = calcular_intervalo(con, momento)
    proximo = momento + timedelta(minutes=minutos)
    gravar_estado(con, "proximo_envio", proximo.isoformat(timespec="seconds"))
    plano = plano_do_dia(con, momento)
    info(
        f"próximo envio em {minutos:.0f}min ({proximo:%H:%M}) · "
        f"fila {len(fila_de_envio(con, 0))} · "
        f"{enviadas_hoje(con, momento)}/{plano['cota']} hoje · "
        f"ciclo fecha {fim_do_ciclo(momento, plano):%H:%M}"
    )
    return proximo


def hora_de_enviar(con: sqlite3.Connection, momento: datetime) -> bool:
    plano = plano_do_dia(con, momento)
    if not dentro_da_janela(momento, plano):
        return False
    if enviadas_hoje(con, momento) >= plano["cota"]:
        return False
    agendado = ler_estado(con, "proximo_envio")
    if not agendado:
        return True
    try:
        return momento >= datetime.fromisoformat(agendado)
    except ValueError:
        return True


def hora_de_clonar(con: sqlite3.Connection, momento: datetime) -> bool:
    ultimo = ler_estado(con, "ultimo_clone")
    if not ultimo:
        return True
    try:
        return ((momento - datetime.fromisoformat(ultimo)).total_seconds()
                >= clonador_cfg(con)["intervalo_seg"])
    except ValueError:
        return True


def sementear_estado(con: sqlite3.Connection, momento: datetime) -> None:
    """Primeira subida: marca o relógio sem disparar nada.

    Sem isto, `ultimo_envio` vazio faz o daemon publicar no grupo no segundo
    em que sobe — surpresa ruim em restart, deploy ou teste. Quem quer o
    ciclo imediato pede com --agora.
    """
    if not ler_estado(con, "ultima_busca"):
        gravar_estado(con, "ultima_busca", momento.isoformat(timespec="seconds"))
        info(f"primeira subida: busca ancorada em {momento:%d/%m %H:%M}")
    if not ler_estado(con, "proximo_envio"):
        agendar_proximo_envio(con, momento)


def cmd_rodar(args) -> int:
    try:
        trava = Trava().__enter__()
    except RuntimeError as e:
        erro(str(e))
        return 1

    signal.signal(signal.SIGTERM, _sinal)
    signal.signal(signal.SIGINT, _sinal)

    con = abrir_banco()
    reconciliar_entregas(con)      # crash anterior? resolve antes de operar
    semeadas = garantir_config(con)
    if semeadas:
        info(f"config: {semeadas} chave(s) semeada(s) com os valores vigentes")
    ok(
        f"daemon no ar · fuso {TZ} · busca {BUSCA_HORAS}h · "
        f"envio {'adaptativo' if ENVIO_ADAPTATIVO else 'fixo'} · "
        f"{ENVIOS_POR_DIA[0]}-{ENVIOS_POR_DIA[1]} ofertas/dia"
        + (" · MODO SECO (não envia)" if args.seco else "")
    )
    sementear_estado(con, agora())

    if args.agora:
        info("--agora: um ciclo completo antes de entrar no horário")
        try:
            bloco1_buscar(con, args.paginas)
            bloco2_links(con)
            bloco3_enviar(con, seco=args.seco, forcar=True)
        except Exception as e:  # o daemon não pode morrer por um ciclo ruim
            erro(f"ciclo inicial: {type(e).__name__}: {e}")

    while not _parar:
        momento = agora()
        # pulso de vida: o dashboard mostra "Worker ● Online" lendo isto
        gravar_estado(con, "heartbeat", momento.isoformat(timespec="seconds"))
        try:
            if hora_de_buscar(con, momento):
                gravar_estado(con, "ultima_busca", momento.isoformat(timespec="seconds"))
                n = purgar_vencidas(con)
                con.commit()
                if n:
                    info(f"{n} pendente(s) vencida(s) removida(s) da fila")
                bloco1_buscar(con, args.paginas)
                bloco2_links(con)

            if not _parar and clonador_cfg(con)["ativo"] and hora_de_clonar(con, momento):
                gravar_estado(con, "ultimo_clone", momento.isoformat(timespec="seconds"))
                if bloco4_clonar(con):
                    bloco2_links(con)

            if not _parar and hora_de_enviar(con, momento):
                agendar_proximo_envio(con, momento)
                bloco2_links(con)  # rede de segurança: link que faltou
                bloco3_enviar(con, seco=args.seco)
        except Exception as e:
            erro(f"ciclo: {type(e).__name__}: {e}")

        dormir(30)

    con.close()
    trava.__exit__()
    ok("daemon encerrado")
    return 0


# ══════════════════════════════════════════════════════════════════════
# COMANDOS AVULSOS
# ══════════════════════════════════════════════════════════════════════
def cmd_buscar(args) -> int:
    con = abrir_banco()
    bloco1_buscar(con, args.paginas, seco=args.seco)
    if not args.seco and not args.sem_links:
        bloco2_links(con)
    con.close()
    return 0


def cmd_links(args) -> int:
    con = abrir_banco()
    bloco2_links(con)
    con.close()
    return 0


def cmd_enviar(args) -> int:
    if not args.seco:
        try:
            Trava().__enter__()      # solta ao fim do processo
        except RuntimeError as e:
            erro(str(e))
            return 1
    con = abrir_banco()
    bloco2_links(con)
    enviadas = bloco3_enviar(con, limite=args.limite, seco=args.seco, forcar=args.forcar)
    con.close()
    if enviadas:
        ok(f"{enviadas} oferta(s) enviada(s)")
    return 0


def cmd_listar(args) -> int:
    con = abrir_banco()
    sql = "SELECT * FROM ofertas"
    params: list = []
    if args.status:
        sql += " WHERE status_envio = ?"
        params.append(args.status.upper())
    sql += " ORDER BY criado_em DESC LIMIT ?"
    params.append(args.limite)

    linhas = con.execute(sql, params).fetchall()
    if not linhas:
        aviso("nada no banco — rode `buscar` primeiro")
        con.close()
        return 0

    for r in linhas:
        cor = {"ENVIADO": VERDE, "ERRO": VERMELHO}.get(r["status_envio"], AMARELO)
        print(f"{cor}{r['status_envio']:<9}{FIM} {r['nome'][:62]}")
        print(
            f"          {CINZA}{reais(r['preco_original'])} →{FIM} "
            f"{VERDE}{reais(r['preco_promocional'])}"
            f"{(' ' + r['condicao']) if r['condicao'] else ''}{FIM} "
            f"{AMARELO}-{r['desconto_pct']}%{FIM}  {AZUL}{r['marca'] or '?'}{FIM}"
            f"  {CINZA}{r['badge']}{FIM}"
        )
        print(f"          {CINZA}{r['link_afiliado'] or '(sem link de afiliado)'}{FIM}")
        if r["erro"]:
            print(f"          {VERMELHO}{r['erro'][:80]}{FIM}")
        print()

    contagem = con.execute(
        "SELECT status_envio, COUNT(*) n FROM ofertas GROUP BY status_envio"
    ).fetchall()
    print(CINZA + " · ".join(f"{r['n']} {r['status_envio'].lower()}" for r in contagem) + FIM)
    con.close()
    return 0


def cmd_testar(args) -> int:
    print()
    con = abrir_banco()
    total = con.execute("SELECT COUNT(*) n FROM ofertas").fetchone()["n"]
    ok(f"banco {BANCO} — {total} oferta(s)")

    cookie = cookie_ml()
    if not cookie:
        erro(f"cookie do ML ausente ({ARQUIVO_COOKIE})")
    elif not ML_AFFILIATE_TAG:
        erro("ML_AFFILIATE_TAG vazio no .env")
    else:
        alvo = con.execute(
            "SELECT url FROM ofertas ORDER BY criado_em DESC LIMIT 1"
        ).fetchone()
        if not alvo:
            aviso(
                f"cookie presente ({len(cookie)} chars) — rode `buscar` para "
                "testar a geração de link de verdade"
            )
        else:
            try:
                links = gerar_links([limpar_url(alvo["url"])])
                if links:
                    ok(f"afiliado ML ok — {list(links.values())[0]}")
                else:
                    erro("createLink respondeu sem short_url")
            except RuntimeError as e:
                erro(f"afiliado ML: {e}")

    if not uazapi_configurado():
        erro("uazapi incompleto no .env (UAZAPI_URL / UAZAPI_TOKEN / UAZAPI_GRUPO)")
    else:
        ok(f"uazapi {UAZAPI_URL} → grupo {UAZAPI_GRUPO}")
        if args.enviar_teste:
            try:
                msg_id = uazapi_enviar("🤖 teste do agente de promoções — ignore.")
                ok(f"mensagem de teste entregue (id {msg_id})")
            except (HttpErro, RuntimeError) as e:
                erro(f"uazapi: {e}")

    momento = agora()
    plano = plano_do_dia(con, momento)
    print(
        f"\n{CINZA}fuso {TZ} · agora {momento:%d/%m %H:%M} · "
        f"janela {'ABERTA' if dentro_da_janela(momento, plano) else 'FECHADA'}{FIM}"
    )
    print(
        f"{CINZA}plano de hoje: {plano['cota']} ofertas entre "
        f"{hora_do_dia(momento, plano['inicio']):%H:%M} e "
        f"{hora_do_dia(momento, plano['fim']):%H:%M} · "
        f"{enviadas_hoje(con, momento)} já enviada(s){FIM}"
    )
    print(
        f"{CINZA}filtros: {len(KEYWORDS_OBRIGATORIAS)} keywords · "
        f"{len(BLACKLIST)} termos na blacklist · desconto ≥ {DESCONTO_MINIMO}% · "
        f"validade {VALIDADE_HORAS}h{FIM}\n"
    )
    con.close()
    return 0


def cmd_marcas(args) -> int:
    """Varre a categoria e mostra TODAS as marcas que o ML rotulou, separando
    as que passam das que você está barrando. É daqui que sai a curadoria."""
    aceitas: dict[str, list[str]] = {}
    barradas: dict[str, list[str]] = {}
    sem_rotulo: list[str] = []
    paginas = args.paginas

    pagina = 0
    while pagina < paginas:
        pagina += 1
        try:
            contexto = extrair_contexto(baixar_pagina(pagina))
        except (HttpErro, RuntimeError) as e:
            aviso(f"página {pagina}: {e}")
            break
        if not contexto:
            aviso(f"página {pagina}: sem estado embutido")
            break
        if pagina == 1:
            paginas = min(paginas, total_de_paginas(contexto, paginas))

        for item in contexto.get("items") or []:
            card = item.get("card") or {}
            comps = {c.get("type"): c for c in card.get("components") or []}
            titulo = ((comps.get("title") or {}).get("title") or {}).get("text") or ""
            if not titulo or filtrar_titulo(titulo):
                continue  # nem é perfume: não polui a curadoria de marca
            rotulo = marca_do_card(comps)
            marca, motivo, _ = filtrar_marca(rotulo, titulo)
            if not rotulo:
                sem_rotulo.append(titulo)
            alvo = aceitas if not motivo else barradas
            alvo.setdefault(rotulo or "(sem rótulo)", []).append(titulo)
        time.sleep(random.uniform(*PAUSA_ENTRE_PAGINAS))

    print(f"\n{VERDE}{'═' * 74}{FIM}")
    print(f"{VERDE}  PASSAM — {sum(len(v) for v in aceitas.values())} anúncio(s){FIM}")
    print(f"{VERDE}{'═' * 74}{FIM}")
    for rotulo, titulos in sorted(aceitas.items(), key=lambda x: -len(x[1])):
        marca, _ = achar_marca(rotulo, titulos[0])
        print(f"  {VERDE}{len(titulos):>2}x{FIM} {rotulo:<26} {CINZA}→ {marca}{FIM}")

    print(f"\n{VERMELHO}{'═' * 74}{FIM}")
    print(f"{VERMELHO}  BARRADAS — {sum(len(v) for v in barradas.values())} anúncio(s){FIM}")
    print(f"{VERMELHO}{'═' * 74}{FIM}")
    for rotulo, titulos in sorted(barradas.items(), key=lambda x: -len(x[1])):
        print(f"  {VERMELHO}{len(titulos):>2}x{FIM} {rotulo}")
        if args.detalhe:
            for t in titulos:
                print(f"        {CINZA}{t[:66]}{FIM}")

    print(
        f"\n{CINZA}{len(sem_rotulo)} anúncio(s) sem rótulo de marca no card "
        f"(quase sempre paralela).{FIM}"
    )
    print(
        f"{CINZA}Para liberar uma marca, acrescente o nome em MARCAS_IMPORTADAS, "
        f"MARCAS_ARABES,\nMARCAS_NACIONAIS ou MARCAS_CASAS_NACIONAIS no topo do "
        f"agente_ml.py.{FIM}\n"
    )
    return 0


def cmd_clonar(args) -> int:
    con = abrir_banco()
    bloco4_clonar(con, seco=args.seco)
    if not args.seco:
        bloco2_links(con)
    con.close()
    return 0


def cmd_status(args) -> int:
    """Raio-x da operação: vivo? o que já fez hoje? o que vem?"""
    con = abrir_banco()
    momento = agora()
    plano = plano_do_dia(con, momento)

    pid = dono_da_trava()
    if pid:
        print(f"\n  {VERDE}● daemon rodando{FIM} {CINZA}(pid {pid}){FIM}")
    else:
        print(f"\n  {AMARELO}○ daemon parado{FIM}")

    inicio = hora_do_dia(momento, plano["inicio"])
    fim = hora_do_dia(momento, plano["fim"])
    enviadas = enviadas_hoje(con, momento)
    dentro = dentro_da_janela(momento, plano)
    print(
        f"  plano de hoje: {AZUL}{enviadas}/{plano['cota']}{FIM} enviadas · "
        f"janela {inicio:%H:%M}–{fim:%H:%M} "
        f"({VERDE + 'aberta' + FIM if dentro else AMARELO + 'fechada' + FIM})"
    )

    proximo = ler_estado(con, "proximo_envio")
    if proximo:
        try:
            quando = datetime.fromisoformat(proximo)
            faltam = (quando - momento).total_seconds() / 60
            print(
                f"  próximo envio: {quando:%H:%M} "
                f"{CINZA}({'agora' if faltam <= 0 else f'em {faltam:.0f}min'}){FIM}"
            )
        except ValueError:
            pass

    ultima = ler_estado(con, "ultima_busca")
    if ultima:
        print(f"  última coleta: {CINZA}{ultima[:16].replace('T', ' ')}{FIM}")

    print()
    for r in con.execute(
        "SELECT status_envio, COUNT(*) n FROM ofertas GROUP BY status_envio"
    ):
        cor = {"ENVIADO": VERDE, "ERRO": VERMELHO}.get(r["status_envio"], AMARELO)
        print(f"  {cor}{r['n']:>4} {r['status_envio'].lower()}{FIM}")

    prontas = len(fila_de_envio(con, 0))
    espera = con.execute(
        "SELECT COUNT(*) n FROM ofertas WHERE status_envio='PENDENTE' "
        "AND proxima_tentativa > ?",
        (momento.isoformat(timespec="seconds"),),
    ).fetchone()["n"]
    sem_link = con.execute(
        "SELECT COUNT(*) n FROM ofertas WHERE status_envio='PENDENTE' "
        "AND link_afiliado = ''"
    ).fetchone()["n"]
    print(
        f"  {CINZA}{prontas} pronta(s) para enviar · {espera} em espera de retry · "
        f"{sem_link} sem link{FIM}"
    )

    falhas = con.execute(
        "SELECT nome, tentativas, erro FROM ofertas WHERE status_envio='ERRO' "
        "ORDER BY atualizado_em DESC LIMIT 3"
    ).fetchall()
    if falhas:
        print(f"\n  {VERMELHO}falhas recentes:{FIM}")
        for f in falhas:
            print(f"    {f['nome'][:48]} {CINZA}({f['tentativas']}x) "
                  f"{f['erro'][:52]}{FIM}")

    if os.path.exists(ARQUIVO_COOKIE):
        idade = (time.time() - os.path.getmtime(ARQUIVO_COOKIE)) / 86400
        cor = VERMELHO if idade > 28 else (AMARELO if idade > 21 else CINZA)
        print(f"\n  {cor}cookie com {idade:.0f} dia(s) — vence por volta de 30{FIM}")
    print()
    con.close()
    return 0


def cmd_grupo(args) -> int:
    """Confere para onde as mensagens vão, ou lista os grupos disponíveis."""
    if not uazapi_configurado():
        erro("uazapi incompleto no .env")
        return 1

    if args.listar:
        try:
            grupos = uazapi_grupos()
        except (HttpErro, RuntimeError) as e:
            erro(f"uazapi: {e}")
            return 1
        for g in sorted(grupos, key=lambda x: str(x.get("Name") or "")):
            marca = f"{VERDE}◄ destino{FIM}" if g.get("JID") == UAZAPI_GRUPO else ""
            print(f"  {CINZA}{g.get('JID','')}{FIM}  {g.get('Name','')} {marca}")
        print(f"\n{CINZA}{len(grupos)} grupo(s){FIM}\n")
        return 0

    try:
        info_grupo = uazapi_grupo_info()
    except (HttpErro, RuntimeError) as e:
        erro(f"uazapi: {e}")
        return 1

    nome = info_grupo.get("Name") or "(sem nome)"
    print(f"\n  destino: {AZUL}{nome}{FIM}")
    print(f"  {CINZA}{info_grupo.get('JID','')} · "
          f"{len(info_grupo.get('Participants') or [])} participante(s){FIM}\n")
    return 0


def cmd_simular(args) -> int:
    """Roda um dia inteiro de envios em memória, sem tocar em nada.

    Serve para ver o ritmo que ENVIO_ADAPTATIVO / ENVIO_CHANCE_RAJADA produzem
    antes de apontar isso para o grupo.
    """
    con = abrir_banco()
    fila_real = len(fila_de_envio(con, 0))
    con.close()

    fila = args.fila or fila_real
    entrada = args.entrada          # ofertas novas por coleta
    base_dia = agora().replace(minute=0, second=0, microsecond=0)

    # sorteia um plano novo por dia simulado, sem tocar no plano real
    plano = {
        "data": "",
        "cota": args.cota or random.randint(*ENVIOS_POR_DIA),
        "inicio": random.uniform(*ENVIO_INICIO_JANELA),
        "fim": random.uniform(*ENVIO_FIM_JANELA),
    }
    momento = hora_do_dia(base_dia, plano["inicio"])
    fim = hora_do_dia(base_dia, plano["fim"])

    print(
        f"\n{CINZA}fila inicial {fila} · +{entrada} por coleta {BUSCA_HORAS}{FIM}\n"
        f"{CINZA}plano sorteado: {plano['cota']} ofertas entre "
        f"{momento:%H:%M} e {fim:%H:%M}{FIM}\n"
    )

    enviados: list[datetime] = []
    coletas = set(BUSCA_HORAS)
    hora_anterior = momento.hour
    while momento < fim:
        # a coleta repõe a fila ao cruzar cada hora de BUSCA_HORAS
        if momento.hour != hora_anterior:
            for h in range(hora_anterior + 1, momento.hour + 1):
                if h in coletas:
                    fila += entrada
            hora_anterior = momento.hour

        if len(enviados) >= plano["cota"]:
            break
        if fila <= 0:
            momento += timedelta(minutes=5)
            continue

        enviados.append(momento)
        fila -= 1

        if not ENVIO_ADAPTATIVO:
            momento += timedelta(minutes=random.uniform(*ENVIO_INTERVALO_FIXO))
            continue

        # mesma função que o daemon usa, só que sem banco
        base = ritmo(
            None,
            momento,
            max(fila, 1),
            max(1.0, (fim - momento).total_seconds() / 60),
            max(1.0, (fim_do_ciclo(momento, plano) - momento).total_seconds() / 60),
            plano["cota"],
            ja_enviadas=len(enviados),
        )
        if base is None:
            break
        momento += timedelta(minutes=sortear_intervalo(base))

    linha, hora_atual = [], None
    for t in enviados:
        if t.hour != hora_atual:
            if linha:
                print("   " + "  ".join(linha))
            hora_atual, linha = t.hour, []
        linha.append(f"{t:%H:%M}")
    if linha:
        print("   " + "  ".join(linha))

    intervalos = [
        (b - a).total_seconds() / 60 for a, b in zip(enviados, enviados[1:])
    ]
    if intervalos:
        curtos = sum(1 for i in intervalos if i <= 3)
        print(
            f"\n{VERDE}{len(enviados)} envios{FIM} · intervalo "
            f"{min(intervalos):.0f}–{max(intervalos):.0f}min "
            f"(média {sum(intervalos)/len(intervalos):.0f}) · "
            f"{curtos} colado(s) ≤3min · fila no fim: {fila}"
        )
    print()
    return 0


def cmd_termos(args) -> int:
    """Testa termos de busca: quantos cards voltam e quantos viram oferta.

    Serve para validar antes de pôr em TERMOS_BUSCA — em alguns termos o ML
    responde em streaming e o payload não vem, e isso não dá erro, só volta
    vazio.
    """
    alvos = args.termo or TERMOS_BUSCA
    if not cookie_ml():
        erro("a busca exige o cookie de sessão (.mlcookie)")
        return 1

    bons = 0
    for i, termo in enumerate(alvos):
        try:
            contexto = contexto_da_busca(baixar_busca(termo))
        except (HttpErro, RuntimeError) as e:
            print(f"  {VERMELHO}!{FIM} {termo!r:<30} {e}")
            continue

        if not contexto:
            print(
                f"  {VERMELHO}✗{FIM} {termo!r:<30} "
                f"{CINZA}sem payload — troque o termo{FIM}"
            )
        else:
            bons += 1
            ofertas, _ = extrair_ofertas_json(contexto, set())
            total = (contexto.get("paging") or {}).get("total")
            marcas = sorted({o.marca for o in ofertas})
            print(
                f"  {VERDE}✓{FIM} {termo!r:<30} "
                f"{len(contexto['items']):>2} cards de {total:<6} → "
                f"{VERDE}{len(ofertas)} oferta(s){FIM}"
            )
            if marcas:
                print(f"      {CINZA}{', '.join(marcas)[:96]}{FIM}")
        if i < len(alvos) - 1:
            time.sleep(random.uniform(*PAUSA_ENTRE_BUSCAS))

    print(f"\n{bons}/{len(alvos)} termo(s) utilizáveis\n")
    return 0


def cmd_exportar(args) -> int:
    """JSON no shape do actor do Mercado Livre na Apify — para plugar em
    qualquer coisa que já consumisse aquele formato."""
    con = abrir_banco()
    sql = "SELECT * FROM ofertas"
    params: list = []
    if args.status:
        sql += " WHERE status_envio = ?"
        params.append(args.status.upper())
    sql += " ORDER BY criado_em DESC"
    linhas = con.execute(sql, params).fetchall()
    con.close()

    itens = [
        {
            "id": r["mlb_id"],
            "marketplace": "mercadolivre",
            "title": r["nome"],
            "permalink": r["url"],
            "affiliate_link": r["link_afiliado"],
            "thumbnail": r["imagem"],
            "original_price": r["preco_original"],
            "price": r["preco_promocional"],
            "discount_percentage": r["desconto_pct"],
            "price_condition": r["condicao"],
            "brand": r["marca"],
            "badge": r["badge"],
            "seller": r["vendedor"],
            "store": r["loja"],
            "official_store": bool(r["loja_oficial"]),
            "rating": r["avaliacao"],
            "sold_quantity": r["vendidos"],
            "status": r["status_envio"],
            "scraped_at": r["criado_em"],
            "sent_at": r["enviado_em"],
        }
        for r in linhas
    ]

    saida = json.dumps(itens, ensure_ascii=False, indent=2)
    if args.arquivo:
        with open(args.arquivo, "w", encoding="utf-8") as f:
            f.write(saida + "\n")
        ok(f"{len(itens)} item(ns) em {args.arquivo}")
    else:
        print(saida)
    return 0


def cmd_limpar(args) -> int:
    """A oferta chega ~3x mais rápido do que sai, então a fila só cresce e a
    maior parte expira sem nunca ser enviada. Sem esta limpeza o banco vira
    um cemitério de pendentes vencidas."""
    con = abrir_banco()
    momento = agora()

    corte = (momento - timedelta(days=args.dias)).isoformat(timespec="seconds")
    enviadas = con.execute(
        "DELETE FROM ofertas WHERE status_envio = 'ENVIADO' AND enviado_em < ?",
        (corte,),
    ).rowcount

    vencidas = purgar_vencidas(con)
    con.commit()
    con.execute("VACUUM")
    restam = con.execute("SELECT COUNT(*) n FROM ofertas").fetchone()["n"]
    con.close()
    ok(
        f"removidas: {enviadas} enviada(s) há +{args.dias}d · "
        f"{vencidas} pendente(s) vencida(s) (+{VALIDADE_HORAS}h) · restam {restam}"
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Agente de promoções do Mercado Livre (perfumes) — porte do n8n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rodar", help="daemon: os 3 blocos nos horários certos")
    r.add_argument("--paginas", type=int, default=PAGINAS_MAX)
    r.add_argument("--agora", action="store_true", help="um ciclo completo ao subir")
    r.add_argument("--seco", action="store_true", help="nunca envia — só mostra")

    b = sub.add_parser("buscar", help="BLOCO 1 (+2) agora")
    b.add_argument("--paginas", type=int, default=PAGINAS_MAX)
    b.add_argument("--seco", action="store_true", help="só mostra, não grava")
    b.add_argument("--sem-links", action="store_true", help="não roda o BLOCO 2")

    sub.add_parser("links", help="BLOCO 2 para as ofertas sem link")

    e = sub.add_parser("enviar", help="BLOCO 3, uma rodada")
    e.add_argument("--limite", type=int, default=ENVIO_POR_EXECUCAO, help="0 = todas")
    e.add_argument("--seco", action="store_true", help="mostra a mensagem, não envia")
    e.add_argument("--forcar", action="store_true", help="ignora a janela de horário")

    l = sub.add_parser("listar", help="o que está no banco")
    l.add_argument("--status", help="PENDENTE | ENVIADO | ERRO")
    l.add_argument("--limite", type=int, default=20)

    t = sub.add_parser("testar", help="confere cookie, uazapi e banco")
    t.add_argument("--enviar-teste", action="store_true", help="manda 1 msg no grupo")

    mc = sub.add_parser("marcas", help="marcas na categoria: quais passam e quais não")
    mc.add_argument("--paginas", type=int, default=PAGINAS_MAX)
    mc.add_argument("--detalhe", action="store_true", help="lista os títulos barrados")

    cl = sub.add_parser("clonar", help="BLOCO 4: varre os grupos rivais")
    cl.add_argument("--seco", action="store_true", help="só mostra")

    sub.add_parser("status", help="raio-x da operação")

    g = sub.add_parser("grupo", help="mostra o grupo de destino")
    g.add_argument("--listar", action="store_true", help="lista todos os grupos")

    sm = sub.add_parser("simular", help="mostra o ritmo de um dia de envios")
    sm.add_argument("--fila", type=int, default=0, help="padrão: a fila real")
    sm.add_argument("--entrada", type=int, default=15, help="novas por coleta")
    sm.add_argument("--cota", type=int, default=0, help="fixa a cota (padrão: sorteia)")

    tm = sub.add_parser("termos", help="valida termos de busca")
    tm.add_argument("termo", nargs="*", help="padrão: os de TERMOS_BUSCA")

    x = sub.add_parser("exportar", help="JSON dos dados coletados")
    x.add_argument("--arquivo", help="grava em arquivo (padrão: stdout)")
    x.add_argument("--status", help="PENDENTE | ENVIADO | ERRO")

    c = sub.add_parser("limpar", help="apaga ofertas antigas já enviadas")
    c.add_argument("--dias", type=int, default=30)

    args = p.parse_args()
    return {
        "rodar": cmd_rodar,
        "buscar": cmd_buscar,
        "links": cmd_links,
        "enviar": cmd_enviar,
        "listar": cmd_listar,
        "testar": cmd_testar,
        "marcas": cmd_marcas,
        "termos": cmd_termos,
        "simular": cmd_simular,
        "grupo": cmd_grupo,
        "status": cmd_status,
        "clonar": cmd_clonar,
        "exportar": cmd_exportar,
        "limpar": cmd_limpar,
    }[args.cmd](args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
