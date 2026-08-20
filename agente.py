#!/usr/bin/env python3
"""
Ponto de entrada do projeto.

    python3 agente.py ml rodar        agente do Mercado Livre
    python3 agente.py shopee buscar   agente da Shopee
    python3 agente.py runner          supervisor: um daemon por perfil ativo

Também dá para chamar cada agente direto:
    python3 -m mercadolivre.agente rodar
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("ml", "shopee", "runner"):
        print(__doc__)
        return 2
    alvo = sys.argv.pop(1)
    if alvo == "ml":
        from mercadolivre.agente import main as m
    elif alvo == "shopee":
        from shopee.agente import main as m
    else:
        from runner import main as m
    return m()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
