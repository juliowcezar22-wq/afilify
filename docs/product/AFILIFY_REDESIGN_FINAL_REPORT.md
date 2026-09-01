# Afilify — Relatório Final do Redesign SaaS

Branch: `feat/afilify-saas-redesign` · base `a456fba` (main) · 2026-08-22
Worktree: `../afilify-saas-redesign` (isolado; main intocada; sem push/merge/deploy)

## 1. Arquitetura anterior

Painel Next.js 16 com 10 páginas planas (Dashboard, Ofertas, Fila,
Grupos & canais, Copiador, Templates, Conexões, Analytics, Logs,
Configurações), sem componentes compartilhados, sidebar que rolava junto
com o conteúdo e sumia, sem navegação mobile, sem contexto de projeto —
slugs (`perfumes-ml`), JIDs, "worker", "Postgres", hora decimal e
instruções de infraestrutura expostos ao usuário.

## 2. Arquitetura implementada

Modelo mental Conta → Projetos → (Fontes/Destinos/Mensagens/Ritmo) →
Ofertas → Publicações (docs/product/AFILIFY_PRODUCT_ARCHITECTURE.md).
Navegação agrupada: GERAL (Dashboard) · OPERAÇÃO (Ofertas, Publicações,
Desempenho) · AUTOMAÇÃO (Fontes, Destinos, Mensagens, Ritmo & Regras) ·
CONEXÕES · CONTA (Configurações, Ajuda). Contexto de projeto no shell
(cookie, 1..N projetos). App shell com sidebar fixa (scroll só no
conteúdo), drawer mobile acessível, rotas antigas com redirect 308.
Logs fora da navegação comum (rota técnica preservada).

## 3. Mudanças por feature

- **Dashboard**: KPIs "Ofertas encontradas hoje / Publicações hoje /
  Aguardando publicação / Precisam de atenção" — os dois últimos são
  cartões clicáveis que levam à lista com o MESMO critério (D22). Saúde
  percebida por projeto ("Funcionando normalmente" / "Sem sinal da
  automação", batida de vida com limiar de 5 min, D21). Recentes sem
  overflow (grid estável).
- **Ofertas**: busca "Buscar produto ou marca", filtros Status
  (Aguardando/Publicadas/Com problema/Ignoradas) separados de Origem
  (Busca automática/Monitoramento), paginação "1–40 de N" com clamp de
  página inválida, tabela ≥md com header fixo + cartões <md, nome em 2
  linhas, motivo de erro legível, ações "Ignorar"/"Voltar para a fila".
- **Publicações** (ex-Fila): ritmo do dia por projeto em HH:MM (plano de
  outro dia nunca aparece como de hoje), próximas com selo "Prioridade"
  para monitoramento, "Aguardando nova tentativa" só quando existe,
  recentes com "Hoje, 13:32".
- **Fontes** (ex-Copiador): busca automática com horários legíveis e
  estado ligado à batida real; monitoramento com grupos por NOME,
  frequência em presets (D12), oportunidades recentes; JIDs só em
  Detalhes técnicos.
- **Destinos** (ex-Grupos & canais): destino atual com nome + atividade,
  troca com busca (nome ou final do id — grupos sem nome alcançáveis),
  confirmação explícita e refresh; id em Detalhes técnicos.
- **Mensagens** (ex-Templates): preview estilo WhatsApp com oferta real
  DO PRÓPRIO projeto; biblioteca de chamadas por categoria (item a item,
  D9); rodapé simples; sintaxe {token} apenas no Modo avançado (D8/D18);
  chamada digitada e não adicionada entra no salvar.
- **Ritmo & Regras** (ex-Configurações): faixa de publicações/dia,
  janelas em HH:MM (decimal só no contrato, D6; campo vazio bloqueia o
  salvar), horários de busca em chips, validade, proporção de importados
  em Avançado.
- **Conexões**: WhatsApp/Mercado Livre/Shopee com estados de produto
  (Conectado/Conectando/Precisa de atenção/Desconectado/Não configurada),
  lista por plataforma pronta para múltiplas contas, renovação da sessão
  ML em Detalhes técnicos, futuras plataformas como "Em breve" honesto.
- **Desempenho** (ex-Analytics): período 7/14/30 dias, KPIs (cliques
  respeitam projeto ativo; 0 ≠ indisponível), publicações por dia com
  legenda Busca × Monitoramento, horários, marcas.
- **Configurações** (conta): links inteligentes (tracking, D7), sessão,
  seções futuras honestas. **Ajuda**: conceitos do produto.
  **Logs** → "Registro técnico", fora da navegação, com aviso.

## 4. Decisões de produto — D1–D23 em docs/product/AFILIFY_DECISIONS.md
(principais: D2 projeto=perfil com nomes amigáveis; D5 redirects; D6 hora
decimal na borda; D8/D18 modo avançado; D11 ignoradas ≠ atenção; D13 sem
QR nesta fase; D21 limiar de batida; D22 KPI=lista.)

## 5. Decisões técnicas

Tailwind 4 tokens em `@theme` (contraste AA; focus-visible global);
componentes próprios sem biblioteca externa; SQL nos Server Components
(padrão do projeto) com `condicaoProjeto` para o contexto; conversões só
na borda (`lib/formatos.ts`); `contextoProjeto` memoizada por request;
consultas independentes em `Promise.all`; grid empilhador sempre
`grid-cols-1` (aprendizado D19).

## 6. Componentes criados

`components/ui/`: Botao (+classesBotao), Cartao, Selo, EstadoVazio,
CabecalhoPagina, Indicador (compacto opcional), Paginacao, Detalhes,
DetalhesTecnicos, AvisoSalvar, Icone, SemDados, CONTROLE.
`components/shell/`: NavLinks, SeletorProjeto, DrawerMobile, nav-dados.
`lib/`: formatos, projetos, grupos, contexto, whatsapp, config-cliente.

## 7. Rotas alteradas

Novas: `/publicacoes`, `/fontes`, `/destinos`, `/mensagens`, `/ritmo`,
`/desempenho`, `/configuracoes`, `/ajuda`. Redirects 308: `/fila`,
`/canais`, `/copiador`, `/templates`, `/analytics`, `/config`.
Mantidas: `/`, `/ofertas`, `/conexoes`, `/logs`, `/login`, `/r/[codigo]`.

## 8. APIs impactadas

Nenhum endpoint removido/alterado em contrato. Novo: `POST /api/projeto`
(cookie do projeto ativo). `/api/config`: apenas mensagens de erro
traduzidas (validações idênticas). `/api/health`: intocado (contrato de
monitoramento). Motor Python: **zero arquivos alterados** (verificado por
allowlist no harness).

## 9. Testes executados

- `pnpm lint` ✓ (zero erros; 5 erros pré-existentes eliminados junto com
  as páginas antigas) · `next typegen && tsc --noEmit` ✓ · `pnpm build` ✓
- Suíte Python do motor: 87 testes ✓ (banco temporário)
- QA visual: fixture SQLite própria + mock do provedor WhatsApp; Chrome
  headless em 1440/1280/768 e 390px reais (wrapper same-origin
  `scripts/harness/qa-wrap.html`); overflow medido elemento a elemento em
  TODAS as rotas (390px sem estouro); drawer mobile testado com clique
  programático (foco visível, focus trap); console limpo nas 10 páginas;
  redirects e APIs de escrita testados por curl.
- Harness testado: bloqueio/anti-loop/sucesso do Stop hook, contagem de
  tasks, falha simulada.

## 10. Limitações conhecidas

- QA interativo completo (teclado real, leitores de tela) não coberto por
  automação — recomendado teste manual curto antes do merge.
- Lista de grupos do WhatsApp busca fresca a cada render (sem cache de
  60s) — correção de dados sobre latência; candidato a melhoria.
- `/api/health` mantém limiar de 90s e vocabulário técnico (contrato).
- Tracking "global" grava por projeto em N chamadas (não atômico); falha
  parcial é reportada com clareza, mas a atomicidade real pede endpoint
  novo (FUTURO).

## 11. Classificado como FUTURO (não implementado)

QR code de conexão WhatsApp no painel (D13); página Projetos com CRUD
(D17); multiusuário/assinatura/permissões; novas plataformas (Amazon,
Magalu, Shein, TikTok Shop, Telegram); métricas de receita/conversão;
cache TTL da lista de grupos; endpoint atômico de tracking.

## 12. Commits (base → topo)

1. `c4a3768` chore: establish afilify redesign harness
2. `2497b2b` feat: design system tokens and shared UI kit
3. `777599c` refactor: rebuild application shell and navigation
4. `ae8d5f4` feat: redesign dashboard, offers and publications experience
5. `acc7960` feat: redesign automation pages (sources, destinations, messages, pace)
6. `819a684` feat: redesign connections, performance, account settings and help
7. `24def95` chore: QA tooling and progress tracking update
8. `33f2c12` fix: adversarial audit round — correctness, consistency and hardening
9. (final) docs: final report and closing checklist

## 13. Instruções para revisão

```bash
cd ../afilify-saas-redesign
(cd painel && pnpm install && pnpm build)
scripts/harness/verify-redesign.sh          # full check
# rodar com dados reais (só leitura de quem revisa):
(cd painel && SQLITE_PATH=../dados/ofertas.db pnpm start -p 3105)
```
Para QA móvel/overflow: copiar `scripts/harness/qa-wrap.html` para
`painel/public/` e abrir `/qa-wrap.html?rota=/ofertas&w=390`.

## 14. Possíveis conflitos com outras worktrees

A workstream dos agentes toca só o motor Python — zero interseção de
arquivos com esta branch (painel/, docs/, scripts/harness/, .claude/,
markdowns da raiz). Único ponto de atenção: se a outra worktree editar o
`README.md` da raiz (esta branch atualizou nomes de páginas na tabela de
config) — conflito trivial de texto.

## 15. Procedimento recomendado de merge

1. Revisar a branch e rodar `scripts/harness/verify-redesign.sh`.
2. Merge normal em main (fast-forward não disponível; merge commit ok).
3. Deploy do painel como sempre (nenhuma env nova; nenhuma migração).
4. Após o merge, decidir se os hooks de `.claude/settings.json` e os
   arquivos TASKS/PROGRESS da raiz permanecem (harness era do redesign;
   os scripts de verificação continuam úteis).
