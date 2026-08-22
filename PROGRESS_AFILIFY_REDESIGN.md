# PROGRESS — Afilify SaaS Redesign

> Atualizado continuamente. Permite retomar o trabalho sem depender da
> conversa. Par com TASKS_AFILIFY_REDESIGN.md (checkboxes = verdade).

## Estado atual

- **Milestone atual:** M2 — Design System (M0 e M1 concluídos)
- **Executando agora:** tokens + componentes UI compartilhados
- **Worktree:** `/Users/juliocesar/Downloads/afilify-saas-redesign` · branch `feat/afilify-saas-redesign` · base `a456fba` (main)
- **Regra:** nenhum arquivo do motor Python é modificado (D1); sem push/merge/deploy.

## Feito

- M0 completo: worktree isolado; auditoria de todas as páginas do painel,
  APIs, lib de dados, schema e contratos do motor (config dinâmica, estado,
  entregas, headlines/mensagem, ritmo em hora decimal, clonador, canal,
  tracking). Docs criados:
  - docs/product/AFILIFY_PRODUCT_ARCHITECTURE.md
  - docs/product/AFILIFY_UI_REDESIGN_PLAN.md
  - docs/product/AFILIFY_DECISIONS.md (D1–D16)
  - docs/product/AFILIFY_MIGRATION_MAP.md
- Baseline: `pnpm build` OK (todas rotas atuais compilam); `pnpm lint` com
  5 erros pré-existentes (analytics Date.now purity, config/form Par em
  render, dashboard purity…) — todos em arquivos que serão reescritos;
  `tsc --noEmit` requer `next typegen` antes (LayoutProps).

## Decisões-chave (detalhe em AFILIFY_DECISIONS.md)

D1 frontend-only · D2 projeto=perfil com nomes amigáveis em lib/projetos.ts
· D5 rotas novas + redirects 308 · D6 hora decimal convertida na borda
· D8 template avançado colapsado · D12 frequência em presets · D13 sem QR
nesta fase · D16 empty states sem conexão.

## Blockers

- Nenhum blocker real no momento. Painel do worktree roda sem env (mostra
  estados vazios); QA com dados usa fixture SQLite própria (nunca o banco
  real da operação no Mac).

## Próximo passo

1. M2: tokens em globals.css + componentes components/ui/.
2. M3: App Shell (sidebar fixa, drawer mobile, seletor de projeto,
   redirects) — testar com fixture SQLite própria.

## Harness (M1 — concluído e testado)

- `scripts/harness/fast-check.sh` lint+typecheck · `verify-redesign.sh`
  full check (build, linguagem, motor intocado, tasks) grava marcador
  `.harness/last-verify-ok` · `check-linguagem.sh` termos proibidos
  (exceção pontual: marcar linha com `harness-ok`) · `stop-guard.sh` Stop
  hook (bloqueia com tasks abertas/verificação velha; anti-loop após 2
  bloqueios sem mudança) · `task-check.sh` TaskCompleted hook.
- Hooks em `.claude/settings.json`. Testes: bloqueio exit 2 ✓, anti-loop ✓,
  sucesso exit 0 ✓, check-linguagem detecta legado ✓. Nota: hooks novos só
  carregam em sessão nova do Claude Code — nesta sessão a disciplina é
  rodar os scripts manualmente a cada tarefa/milestone.

## Testes executados até agora

- pnpm lint / next typegen + tsc / pnpm build (baseline — ver acima).

## Arquivos principais alterados até agora

- Somente docs/ e arquivos de tasks/progress (nenhum código ainda).
