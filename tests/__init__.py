"""Suíte do Afilify — stdlib puro (unittest), zero dependências.

Roda ANTES de qualquer import do núcleo: aponta o banco para um arquivo
temporário para nenhum teste encostar em dados/ofertas.db (produção).
"""
import os, tempfile

os.environ["ML_BANCO"] = os.path.join(tempfile.mkdtemp(prefix="afilify-test-"), "teste.db")
os.environ.setdefault("PERFIL", "perfumes_ml")
