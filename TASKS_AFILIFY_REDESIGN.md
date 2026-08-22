# TASKS — Afilify SaaS Redesign

Fonte da verdade do progresso. O harness (`scripts/harness/verify-redesign.sh`)
conta `- [ ]` abertas; o Stop hook bloqueia conclusão com tarefas abertas.
Marcar `[x]` somente com o critério de aceitação verificado.

## M0 — Discovery
- [x] Worktree isolado criado (`../afilify-saas-redesign`, branch `feat/afilify-saas-redesign`) e sessão trabalhando nele
- [x] Auditoria completa do painel (10 páginas, APIs, lib, schema) e contratos do motor (config/estado/entregas) registrada nos docs
- [x] Baseline de qualidade registrado (build OK; 5 erros de lint pré-existentes; typecheck via `next typegen`)

## M1 — Harness
- [x] `scripts/harness/verify-redesign.sh` executa lint + typegen/tsc + build + contagem de tasks abertas e retorna exit code correto nas falhas
- [x] `scripts/harness/fast-check.sh` (lint + typecheck) para uso durante tarefas
- [x] Hook Stop configurado em `.claude/settings.json` bloqueando parada com tasks abertas/verificação falhando
- [x] Hook TaskCompleted (fast check) configurado
- [x] Harness testado: falha simulada retorna bloqueio; sucesso permite prosseguir

## M2 — Design System (tokens + componentes)
- [ ] Tokens consolidados em `globals.css` (surfaces, focus ring, success/warn/danger suaves) mantendo identidade dark + acento verde
- [ ] Componentes `components/ui/`: Botao, Cartao, Selo, CampoTexto, CampoSelecao, EstadoVazio, CabecalhoPagina, Indicador, Paginacao, DetalhesTecnicos — usados por ≥2 páginas cada (sem abstração morta)
- [ ] Foco visível (focus-visible ring) em todo controle interativo; nenhum `outline-none` sem substituto

## M3 — App Shell & Navegação
- [ ] Sidebar fixa: conteúdo rola em `<main>` com scroll próprio; sidebar permanece acessível em qualquer altura de página (sem hacks por página)
- [ ] Navegação agrupada (GERAL/OPERAÇÃO/AUTOMAÇÃO/CONEXÕES/CONTA) com ícones e estado ativo (`aria-current="page"`)
- [ ] Seletor de projeto no shell ("Projeto: Nome ▾"), persistido em cookie, funciona com 1..N projetos
- [ ] Navegação mobile: drawer acessível (Escape fecha, foco gerenciado) em <768px; sem sidebar inacessível
- [ ] Redirects 308 das rotas antigas (`/fila`, `/canais`, `/copiador`, `/templates`, `/analytics`, `/config`) para as novas
- [ ] `/logs` removida da navegação comum (rota continua acessível)

## M4 — Dashboard
- [ ] KPIs: "Ofertas encontradas hoje", "Publicações hoje", "Aguardando publicação", "Precisam de atenção" — cartão de atenção clicável levando a /ofertas filtrado
- [ ] Sem "Postgres", "SQLite", "worker", slugs ou "clone" na página
- [ ] Saúde percebida ("Funcionando normalmente" / "Sem sinal da automação" / itens de atenção) por projeto com nome amigável
- [ ] Publicações recentes em layout estável: hora, produto (truncado), desconto — sem overflow em 390px+

## M5 — Ofertas
- [ ] Busca "Buscar produto ou marca" (placeholder e comportamento; MLB continua funcionando como termo, sem ser anunciado)
- [ ] Filtros Status (Todas/Aguardando/Publicadas/Com problema) separados de Origem (Busca/Monitoramento)
- [ ] Paginação "1–40 de N" com anterior/próxima
- [ ] Tabela: nome até 2 linhas (line-clamp), id técnico e erro em linha secundária discreta, datas "22/08 às 13:32", header sticky, sem overflow horizontal do layout (scroll interno do contêiner quando necessário)
- [ ] Ações Ignorar/Reenfileirar preservadas ("Voltar para a fila" como rótulo)
- [ ] Filtro respeita projeto ativo do shell

## M6 — Publicações (ex-Fila)
- [ ] Rota `/publicacoes` com visões "Próximas" e "Recentes"
- [ ] Cota do dia legível por projeto: "N/M hoje · janela 09:00–22:30 · próxima ~HH:MM" (hora decimal nunca exposta)
- [ ] Sem "worker", "clone fura a fila", "plano"; prioridade do monitoramento apresentada como selo "Prioridade" discreto
- [ ] Retries: aparecem só quando existem, como "nova tentativa às HH:MM", com motivo legível
- [ ] Histórico (entregas) com datas "Hoje, 13:32" / "22/08 às 13:32" e status Publicada/Falhou/Enviando

## M7 — Fontes (ex-Copiador)
- [ ] Rota `/fontes` com seções "Busca automática" (horários legíveis do ritmo, por projeto) e "Monitoramento de grupos"
- [ ] Grupos monitorados por NOME (JID só em detalhes técnicos); adicionar/remover preservando contrato `clonador`
- [ ] Frequência como presets legíveis (D12) — sem "varre a cada 180 seg"
- [ ] Últimas oportunidades do monitoramento (clones) com linguagem de produto
- [ ] Empty state honesto sem conexão WhatsApp (D16)

## M8 — Destinos (ex-Grupos & canais)
- [ ] Rota `/destinos`: destino atual de cada projeto com nome do grupo e atividade de hoje
- [ ] Trocar destino = "Usar este grupo" com confirmação clara (efeito: próximas publicações)
- [ ] Lista de grupos da conexão com busca por nome
- [ ] JID oculto por padrão (detalhes técnicos)
- [ ] Empty state honesto sem conexão (D16)

## M9 — Mensagens (ex-Templates)
- [ ] Rota `/mensagens` com preview em destaque (como ficará no WhatsApp)
- [ ] Fluxo comum sem sintaxe `{token}`: rodapé, linha da loja, biblioteca de chamadas
- [ ] Headlines como itens individuais (adicionar/remover/editar) por categoria com nome humano (D9)
- [ ] Template base apenas em "Modo avançado" colapsado; validação de tokens continua na API
- [ ] Sem "deploy", "restart" ou jargão técnico na página

## M10 — Ritmo & Regras (ex-Configurações do ritmo)
- [ ] Rota `/ritmo` por projeto: publicações por dia (faixa), janela em HH:MM (conversão decimal na borda, D6)
- [ ] Horários de busca como seleção de horas legível (chips), não "Coletas 7,15"
- [ ] Validade da oferta em horas com explicação de produto
- [ ] "Proporção de importados" só em Avançado, com explicação (específica do nicho)
- [ ] Nenhuma hora decimal visível; validações da API preservadas

## M11 — Conexões
- [ ] Cartões WhatsApp / Mercado Livre / Shopee com nomes de produto (sem "uazapi", sem env vars, sem ".mlcookie" no fluxo comum)
- [ ] Estados: Conectado / Conectando / Precisa de atenção / Desconectado / Não configurada
- [ ] Estrutura de lista por plataforma preparada para múltiplas contas (render de N itens)
- [ ] Instrução de renovação da sessão ML em "Detalhes técnicos" (não no cartão principal)
- [ ] Plataformas futuras (Amazon, Magalu, Shein, TikTok Shop, Telegram) como "Em breve" não clicáveis — sem simular funcionalidade

## M12 — Desempenho (ex-Analytics)
- [ ] Rota `/desempenho` com filtro de período (7/14/30 dias) e projeto
- [ ] KPIs de período + publicações por dia + horários + marcas (dados reais existentes)
- [ ] Origem "Monitoramento" ao invés de "copiador"/"clones"; sem métricas inventadas
- [ ] Não duplica o Dashboard (sem estado "agora": fila/saúde ficam fora)

## M13 — Configurações da conta + Ajuda + Logs
- [ ] Rota `/configuracoes`: tracking de cliques (D7) com linguagem de produto + sessão (sair) + seções futuras honestas
- [ ] Rota `/ajuda`: conceitos do produto (projeto, fonte, destino, publicação)
- [ ] `/config` redireciona para `/ritmo`; tracking não aparece mais junto do ritmo
- [ ] `/logs` com aviso de página técnica, fora da navegação

## M14 — Responsividade
- [ ] 390px: dashboard, ofertas (tabela → cartões ou scroll controlado), publicações, fontes, destinos, mensagens, ritmo, conexões, desempenho, configurações sem overflow horizontal do body
- [ ] 768px e 1280px: grids adaptam (2→4 colunas KPI etc.); sidebar visível ≥768px… (breakpoint md)
- [ ] Modais/drawers cabem no viewport; botões alcançáveis

## M15 — Acessibilidade
- [ ] Navegação por teclado completa no shell (menu, seletor de projeto, drawer com Escape/focus trap)
- [ ] Labels programáticos em todos inputs/selects; botões são `<button>`
- [ ] Estados não dependem só de cor (texto/ícone acompanham selos de status)
- [ ] Headings hierárquicos (h1 único por página); `aria-current`, `aria-expanded` onde aplicável
- [ ] Contraste: texto secundário e selos ≥ 4.5:1 sobre as superfícies usadas

## M16 — Regression & QA final
- [ ] `verify-redesign.sh` completo passa (lint, typecheck, build, tasks)
- [ ] Testes Python continuam passando (nenhum arquivo do motor alterado — verificado por diff)
- [ ] QA visual das telas nos 4 breakpoints (screenshots via browser automation, ou limitação documentada)
- [ ] Grep de linguagem proibida na UI (worker, Postgres, Uazapi, JID, deploy, restart, LOG_PATH, slug de perfil, hora decimal) — zero ocorrências voltadas ao usuário
- [ ] Console do browser sem erros nas telas validadas (ou limitação documentada)

## M17 — Final
- [ ] Auditoria adversarial (Parte 28) executada e correções aplicadas
- [ ] `docs/product/AFILIFY_REDESIGN_FINAL_REPORT.md` completo (Parte 29)
- [ ] PROGRESS atualizado; commits atômicos; `git status` limpo; sem push/merge
