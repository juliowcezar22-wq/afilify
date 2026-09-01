"""
CIFRA DE CREDENCIAIS

Token de instância do WhatsApp e sessão do Mercado Livre são credenciais de
CONTA — de terceiros, quando a plataforma abrir. Nunca ficam em claro no
banco, nunca voltam para o cliente, nunca aparecem em log.

    from nucleo import cripto
    guardado = cripto.cifrar("token-secreto")
    original = cripto.decifrar(guardado)

AES-256-GCM: além de esconder, DETECTA adulteração — decifrar um valor
mexido levanta erro em vez de devolver lixo silenciosamente.

A chave mestra vem de AFILIFY_CHAVE_MESTRA (32 bytes em base64url).
Gerar uma:

    python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

O formato guardado é `v1.<nonce>.<texto+tag>`, os dois em base64url. O prefixo
de versão existe para trocar de algoritmo um dia sem precisar adivinhar o que
está gravado.
"""

from __future__ import annotations

import base64
import os

VERSAO = "v1"
_VAR_CHAVE = "AFILIFY_CHAVE_MESTRA"


class ErroCripto(RuntimeError):
    """Chave ausente/inválida, ou valor adulterado."""


def _b64e(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).decode("ascii").rstrip("=")


def _b64d(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def chave_mestra() -> bytes:
    bruta = os.environ.get(_VAR_CHAVE, "").strip()
    if not bruta:
        raise ErroCripto(
            f"{_VAR_CHAVE} não configurada — sem ela a plataforma não pode "
            "guardar credenciais. Gere com: python3 -c "
            "\"import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
        )
    try:
        chave = _b64d(bruta)
    except Exception as e:
        raise ErroCripto(f"{_VAR_CHAVE} não é base64url válido") from e
    if len(chave) != 32:
        raise ErroCripto(f"{_VAR_CHAVE} precisa ter 32 bytes (tem {len(chave)})")
    return chave


def _aesgcm():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:      # pragma: no cover — ambiente sem a dependência
        raise ErroCripto(
            "biblioteca de criptografia ausente — instale com: "
            "pip install 'cryptography>=42'"
        ) from e
    return AESGCM


def configurada() -> bool:
    """Dá para cifrar neste ambiente? Usado para degradar com aviso claro."""
    try:
        chave_mestra()
        _aesgcm()
        return True
    except ErroCripto:
        return False


def cifrar(valor: str, contexto: str = "") -> str:
    """Texto claro → `v1.<nonce>.<cifrado>`.

    `contexto` entra como dado autenticado: uma credencial cifrada para uma
    conexão não decifra no lugar de outra, mesmo que alguém troque as linhas
    de lugar no banco.
    """
    if valor is None:
        raise ErroCripto("nada a cifrar")
    AESGCM = _aesgcm()
    nonce = os.urandom(12)
    selado = AESGCM(chave_mestra()).encrypt(
        nonce, valor.encode("utf-8"), contexto.encode("utf-8") or None)
    return f"{VERSAO}.{_b64e(nonce)}.{_b64e(selado)}"


def decifrar(guardado: str, contexto: str = "") -> str:
    """Inverso de cifrar(). Levanta ErroCripto se o valor foi adulterado."""
    if not guardado:
        return ""
    partes = guardado.split(".")
    if len(partes) != 3 or partes[0] != VERSAO:
        raise ErroCripto("formato de credencial desconhecido")
    _, nonce_b64, selado_b64 = partes
    AESGCM = _aesgcm()
    try:
        aberto = AESGCM(chave_mestra()).decrypt(
            _b64d(nonce_b64), _b64d(selado_b64), contexto.encode("utf-8") or None)
    except ErroCripto:
        raise
    except Exception as e:
        raise ErroCripto(
            "credencial não pôde ser lida — chave mestra trocada ou valor adulterado"
        ) from e
    return aberto.decode("utf-8")


def mascarar(valor: str, visiveis: int = 4) -> str:
    """Para EXIBIR (nunca a credencial em si): '••••1234'."""
    if not valor:
        return ""
    fim = valor[-visiveis:] if len(valor) > visiveis else ""
    return "••••" + fim
