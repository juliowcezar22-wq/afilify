# PROGRESS — Afilify SaaS Redesign

> Atualizado continuamente. Permite retomar o trabalho sem depender da
> conversa. Par com TASKS_AFILIFY_REDESIGN.md (checkboxes = verdade).

## Estado atual

- **Milestone atual:** M16/M17 — verificação final, auditoria adversarial e relatório
- **Worktree:** `/Users/juliocesar/Downloads/afilify-saas-redesign` · branch `feat/afilify-saas-redesign` · base `a456fba` (main)
- **Regra:** nenhum arquivo do motor Python modificado (D1); sem push/merge/deploy.

## Feito

- **M0–M1**: worktree, auditoria completa, docs base, harness testado
  (commit `c4a3768`).
- **M2 Design system**: tokens em `globals.css` (superfícies, tinta 1–3 com
  contraste AA, acento, focus-visible global); componentes em
  `painel/components/ui/` (Botao, Cartao, Selo, EstadoVazio,
  CabecalhoPagina, Indicador, Paginacao, DetalhesTecnicos, Icone, SemDados,
  CONTROLE); libs `formatos.ts` (datas pt-BR, moeda, hora decimal↔HH:MM,
  tradução de status/origem), `projetos.ts` (slug→nome), `contexto.ts`
  (projeto ativo por cookie), `whatsapp.ts` (grupos, máscara de id).
- **M3 Shell**: sidebar fixa com scroll próprio (bug do scroll resolvido no
  layout), navegação agrupada com ícones e aria-current, seletor de projeto
  (cookie via `/api/projeto`, testado), drawer mobile acessível (validado
  em screenshot com foco visível), redirects 308 das 6 rotas antigas
  (testados via curl), /logs fora da navegação.
- **M4–M13**: todas as páginas reescritas em linguagem de produto —
  Dashboard, Ofertas (tabela ≥md + cartões <md), Publicações, Fontes,
  Destinos, Mensagens (preview WhatsApp + biblioteca de chamadas + modo
  avançado), Ritmo & Regras (HH:MM na borda, chips de horários, avançado),
  Conexões (estados por conta, plataformas futuras honestas), Desempenho
  (período 7/14/30), Configurações (tracking movido, D7), Ajuda, Logs
  ("Registro técnico" com aviso).
- **M14 Responsividade**: overflow horizontal medido elemento a elemento em
  TODAS as rotas a 390px (OK) + screenshots 768/1280/1440. Causa-raiz
  documentada na D19 (grid sem template ⇒ grid-cols-1 em todo empilhador).
- **M15 Acessibilidade**: focus-visible global, labels (htmlFor/sr-only) em
  todos os controles, Selo sempre com texto (não só cor), headings
  hierárquicos, aria-current/pressed/expanded, focus trap + Escape no
  drawer, contraste ≥4.5:1 (tinta3 ajustada).
- **M16 (parcial)**: 87 testes Python OK; check-linguagem zero ocorrências;
  console limpo nas 10 páginas; QA visual concluído. Falta: rodar
  `verify-redesign.sh` completo ao final.

## QA — como reproduzir

- Fixture: `scratchpad/qa/fixture.py` → SQLite de teste (NUNCA o banco real).
- Mock WhatsApp: `scratchpad/qa/mock-uazapi.py` (porta 3106).
- Painel QA: `SQLITE_PATH=<fixture> UAZAPI_URL=http://127.0.0.1:3106
  UAZAPI_TOKEN=qa pnpm start -p 3105`.
- Overflow/drawer: copiar `scripts/harness/qa-wrap.html` para
  `painel/public/` e abrir `/qa-wrap.html?rota=/ofertas&w=390[&acao=drawer]`.
- Console: Chrome headless `--enable-logging=stderr` (grep CONSOLE).
- Limitação de tooling documentada: Chrome headless tem largura mínima de
  janela de 500px e composita iframes cross-origin sem clip — usar o
  wrapper same-origin para larguras móveis.

## Blockers

- Nenhum.

## Próximo passo

1. Commits atômicos por área (design system → shell → operação → automação
   → conta/analytics).
2. Auditoria adversarial (Parte 28) + correções.
3. `verify-redesign.sh` completo; relatório final (Parte 29); fechar TASKS.
