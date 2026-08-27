# Quickstart — desenvolver e validar

## Ambiente de validação (D33, D35)

**Regra que não se quebra**: a worktree nunca aponta para o `afilify-db` da VPS (produção
roda em EasyPanel desde 22/08/2026: serviços `worker`, `painel` e `db`).

```bash
cd ~/Downloads/afilify-saas-redesign

# banco de validação — separado, nunca o de produção
export DATABASE_URL='postgres://…/afilify_validacao'
psql "$DATABASE_URL" -f db/0001_init.sql   # … até a última migração, em ordem

# painel
cd painel && pnpm install && pnpm build && pnpm start -p 3105

# motor, apontando para o mesmo banco de validação
STORAGE=postgres DATABASE_URL="$DATABASE_URL" python3 runner.py
```

## Divisão da validação com WhatsApp

| O que validar | Onde | Por quê |
|---|---|---|
| QR, conectado, queda, reconexão, sincronização de grupos | instância `Pessoal` (desconectada) | está livre; exercitar sessão não afeta ninguém |
| Publicação, ritmo, múltiplos destinos, teto de segurança, buscador | instância `bot de promoções` publicando em **grupo de teste** | fidelidade com a operação real, sem tocar no grupo de produção |

A instância de produção **nunca** é reconectada nem tem sua sessão exercitada. O grupo de teste
pode ser criado pela própria plataforma (`POST /group/create`).

## Verificações antes de considerar qualquer tarefa pronta

```bash
scripts/harness/verify-redesign.sh      # herdado do redesign anterior
cd painel && pnpm lint && pnpm exec next typegen && pnpm exec tsc --noEmit && pnpm build
python3 -m unittest discover -s tests -t .
```

A suíte Python roda em banco temporário e **recusa** rodar apontada para banco real — proteção
que já existe no projeto e permanece obrigatória.

## O que nunca fazer nesta rodada

- Alterar `mercadolivre/clonador.py` ou a lógica de monitoramento (Clonador congelado).
- Apontar qualquer processo da worktree para o `afilify-db` de produção.
- Reimplantar qualquer serviço no EasyPanel a partir desta branch.
- Publicar no grupo real a partir da worktree.
- Merge, push ou deploy sem autorização explícita.
