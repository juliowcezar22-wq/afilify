#!/usr/bin/env python3
"""
RUNNER — supervisor multi-projeto do Afilify.

Um processo-filho por automação ativa. As automações vêm de duas fontes, e o
supervisor trata as duas do mesmo jeito:

    do BANCO    automações criadas na interface (AUTOMACAO_ID=...)
    de ARQUIVO  perfis/*.py — a operação de sempre (PERFIL=...)

Um processo por automação continua sendo o desenho certo: o isolamento é
real (falha de uma não derruba outra), custa ~10 MB cada, e a trava por
automação impede dois processos disputando a mesma fila.

O que mudou: QUAL automação rodar deixou de ser uma lista de arquivos e
passou a ser uma consulta. Criar um projeto na tela e ligá-lo faz este
supervisor subir o processo dele no próximo ciclo — sem editar código, sem
reiniciar o resto.

    python3 agente.py runner          sobe tudo que está ativo
    PERFIS=perfumes_ml python3 agente.py runner   (só estes arquivos)
"""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from nucleo import perfil as mod_perfil            # noqa: E402

REINICIO_BASE = 30      # backoff: 30s → 60 → 120 → 240 (teto 300)
REINICIO_TETO = 300

_parar = False


def _sinal(_n, _f):
    global _parar
    _parar = True


def lock_ocupado(nome_perfil: str) -> str:
    """PID de quem segura a trava daquele perfil, ou '' se livre."""
    caminho = os.path.join(RAIZ, "dados", f".lock-{nome_perfil}")
    if not os.path.exists(caminho):
        return ""
    with open(caminho, "a+") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return ""
        except OSError:
            f.seek(0)
            return f.read().strip() or "?"


def log(msg: str) -> None:
    print(f"{time.strftime('%d/%m %H:%M:%S')} [runner] {msg}", flush=True)


def automacoes_do_banco() -> list:
    """(id, rótulo) das automações ativas. Lista vazia quando não há banco
    ou o modelo novo ainda não existe — a operação por arquivo segue."""
    try:
        from nucleo import comum, contexto
        con = comum.abrir_banco()
        try:
            saida = []
            for aid in contexto.automacoes_ativas(con):
                ctx = contexto.Contexto.do_banco(con, aid)
                pode, motivo = ctx.pronta_para_publicar()
                if not pode:
                    log(f"{ctx.projeto_nome} · {ctx.automacao_nome}: pulada — {motivo}")
                    continue
                saida.append((aid, f"{ctx.projeto_nome} · {ctx.automacao_nome}"))
            return saida
        finally:
            con.close()
    except Exception as e:
        log(f"automações do banco indisponíveis ({type(e).__name__}) — seguindo pelos arquivos")
        return []


class Filho:
    """Um processo de automação, venha ela do banco ou de um arquivo."""

    def __init__(self, rotulo: str, ambiente: dict, trava: str):
        self.rotulo = rotulo
        self.ambiente = ambiente
        self.trava = trava
        self.proc: subprocess.Popen | None = None
        self.falhas = 0
        self.proximo_inicio = 0.0

    @classmethod
    def de_perfil(cls, p) -> "Filho":
        modulo = p.nome.replace("-", "_")   # casa-ml-shopee → casa_ml_shopee
        return cls(p.nome, {"PERFIL": modulo, "AUTOMACAO_ID": ""}, p.nome)

    @classmethod
    def de_automacao(cls, automacao_id: str, rotulo: str) -> "Filho":
        return cls(rotulo, {"AUTOMACAO_ID": automacao_id}, automacao_id)

    def iniciar(self):
        env = {**os.environ, **self.ambiente, "LOG_PREFIXO": f"[{self.rotulo}] "}
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(RAIZ, "agente.py"), "ml", "rodar"],
            env=env, cwd=RAIZ,
        )
        log(f"{self.rotulo}: filho iniciado (pid {self.proc.pid})")

    def cuidar(self, agora_ts: float):
        """Reinicia com backoff se o filho morreu com erro."""
        if self.proc is None or self.proc.poll() is None:
            return
        codigo = self.proc.returncode
        self.proc = None
        if codigo == 0:
            log(f"{self.rotulo}: saiu limpo (código 0) — não reinicio")
            return
        self.falhas += 1
        espera = min(REINICIO_BASE * (2 ** (self.falhas - 1)), REINICIO_TETO)
        self.proximo_inicio = agora_ts + espera
        log(f"{self.rotulo}: morreu (código {codigo}), "
            f"reinício {self.falhas} em {espera}s")

    def talvez_reiniciar(self, agora_ts: float):
        if self.proc is None and self.proximo_inicio and agora_ts >= self.proximo_inicio:
            self.proximo_inicio = 0.0
            self.iniciar()

    def parar(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


def main() -> int:
    signal.signal(signal.SIGTERM, _sinal)
    signal.signal(signal.SIGINT, _sinal)

    candidatos: list[Filho] = []

    # 1) automações criadas na interface
    for automacao_id, rotulo in automacoes_do_banco():
        candidatos.append(Filho.de_automacao(automacao_id, rotulo))

    # 2) perfis em arquivo — a operação de sempre
    todos = mod_perfil.listar()
    somente = [s.strip() for s in os.environ.get("PERFIS", "").split(",") if s.strip()]
    if somente:
        todos = [p for p in todos if p.nome.replace("-", "_") in somente]
    rodar, pulados = mod_perfil.escolher_para_rodar(todos)
    for nome, motivo in pulados:
        log(f"{nome}: pulado — {motivo}")
    for p in rodar:
        candidatos.append(Filho.de_perfil(p))

    filhos: list[Filho] = []
    for f in candidatos:
        dono = lock_ocupado(f.trava)
        if dono:
            log(f"{f.rotulo}: pulado — já operado pelo pid {dono}")
            continue
        filhos.append(f)

    if not filhos:
        log("nenhuma automação para rodar — encerrando")
        return 1

    for f in filhos:
        f.iniciar()

    while not _parar:
        ts = time.monotonic()
        for f in filhos:
            f.cuidar(ts)
            f.talvez_reiniciar(ts)
        time.sleep(2)

    log("encerrando: repassando SIGTERM aos filhos")
    for f in filhos:
        f.parar()
    limite = time.monotonic() + 15
    for f in filhos:
        while f.proc and f.proc.poll() is None and time.monotonic() < limite:
            time.sleep(0.5)
    log("runner encerrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
