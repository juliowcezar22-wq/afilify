#!/usr/bin/env python3
"""
RUNNER — supervisor multi-projeto do Afilify.

Um processo-filho por perfil ativo, rodando o MESMO daemon de sempre
(`agente.py ml rodar` com PERFIL=<nome>). O isolamento vem do que já existe:
trava por perfil, estado prefixado, coluna perfil no banco.

Por que supervisor e não um laço único trocando contexto: os módulos do motor
resolvem o perfil no import (variáveis derivadas em nucleo.comum). Trocar isso
em runtime exigiria reescrever assinaturas de dezenas de funções — risco alto
para ganho nenhum, já que N filhos custam ~10 MB cada. A refatoração de
assinaturas acontece naturalmente quando a config migrar para o banco (Fase 4).

    python3 agente.py runner          sobe todos os perfis rodáveis
    PERFIS=perfumes_ml,casa_ml_shopee python3 agente.py runner   (subconjunto)
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


class Filho:
    def __init__(self, p):
        self.perfil = p
        self.proc: subprocess.Popen | None = None
        self.falhas = 0
        self.proximo_inicio = 0.0

    @property
    def modulo(self) -> str:
        # nome do arquivo em perfis/ (casa-ml-shopee → casa_ml_shopee)
        return self.perfil.nome.replace("-", "_")

    def iniciar(self):
        env = {**os.environ,
               "PERFIL": self.modulo,
               "LOG_PREFIXO": f"[{self.perfil.nome}] "}
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(RAIZ, "agente.py"), "ml", "rodar"],
            env=env, cwd=RAIZ,
        )
        log(f"{self.perfil.nome}: filho iniciado (pid {self.proc.pid})")

    def cuidar(self, agora_ts: float):
        """Reinicia com backoff se o filho morreu com erro."""
        if self.proc is None or self.proc.poll() is None:
            return
        codigo = self.proc.returncode
        self.proc = None
        if codigo == 0:
            log(f"{self.perfil.nome}: saiu limpo (código 0) — não reinicio")
            return
        self.falhas += 1
        espera = min(REINICIO_BASE * (2 ** (self.falhas - 1)), REINICIO_TETO)
        self.proximo_inicio = agora_ts + espera
        log(f"{self.perfil.nome}: morreu (código {codigo}), "
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

    todos = mod_perfil.listar()
    somente = [s.strip() for s in os.environ.get("PERFIS", "").split(",") if s.strip()]
    if somente:
        todos = [p for p in todos if p.nome.replace("-", "_") in somente]

    rodar, pulados = mod_perfil.escolher_para_rodar(todos)
    for nome, motivo in pulados:
        log(f"{nome}: pulado — {motivo}")

    filhos: list[Filho] = []
    for p in rodar:
        dono = lock_ocupado(p.nome)
        if dono:
            log(f"{p.nome}: pulado — já operado pelo pid {dono}")
            continue
        filhos.append(Filho(p))

    if not filhos:
        log("nenhum perfil para rodar — encerrando")
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
