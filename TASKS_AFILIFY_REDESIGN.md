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
- [x] Tokens consolidados em `globals.css` (surfaces, focus ring, success/warn/danger suaves) mantendo identidade dark + acento verde
- [x] Componentes `components/ui/`: Botao, Cartao, Selo, EstadoVazio, CabecalhoPagina, Indicador, Paginacao, DetalhesTecnicos, Icone, SemDados + classe CONTROLE p/ inputs — todos em uso real (CampoTexto/CampoSelecao foram removidos por serem abstração morta)
- [x] Foco visível (focus-visible ring) em todo controle interativo; nenhum `outline-none` sem substituto

## M3 — App Shell & Navegação
- [x] Sidebar fixa: conteúdo rola em `<main>` com scroll próprio; sidebar permanece acessível em qualquer altura de página (sem hacks por página)
- [x] Navegação agrupada (GERAL/OPERAÇÃO/AUTOMAÇÃO/CONEXÕES/CONTA) com ícones e estado ativo (`aria-current="page"`)
- [x] Seletor de projeto no shell ("Projeto: Nome ▾"), persistido em cookie, funciona com 1..N projetos
- [x] Navegação mobile: drawer acessível (Escape fecha, foco gerenciado) em <768px; sem sidebar inacessível
- [x] Redirects 308 das rotas antigas (`/fila`, `/canais`, `/copiador`, `/templates`, `/analytics`, `/config`) para as novas
- [x] `/logs` removida da navegação comum (rota continua acessível)

## M4 — Dashboard
- [x] KPIs: "Ofertas encontradas hoje", "Publicações hoje", "Aguardando publicação", "Precisam de atenção" — cartão de atenção clicável levando a /ofertas filtrado
- [x] Sem "Postgres", "SQLite", "worker", slugs ou "clone" na página
- [x] Saúde percebida ("Funcionando normalmente" / "Sem sinal da automação" / itens de atenção) por projeto com nome amigável
- [x] Publicações recentes em layout estável: hora, produto (truncado), desconto — sem overflow em 390px+

## M5 — Ofertas
- [x] Busca "Buscar produto ou marca" (placeholder e comportamento; MLB continua funcionando como termo, sem ser anunciado)
- [x] Filtros Status (Todas/Aguardando/Publicadas/Com problema) separados de Origem (Busca/Monitoramento)
- [x] Paginação "1–40 de N" com anterior/próxima
- [x] Tabela: nome até 2 linhas (line-clamp), id técnico e erro em linha secundária discreta, datas "22/08 às 13:32", header sticky, sem overflow horizontal do layout (scroll interno do contêiner quando necessário)
- [x] Ações Ignorar/Reenfileirar preservadas ("Voltar para a fila" como rótulo)
- [x] Filtro respeita projeto ativo do shell

## M6 — Publicações (ex-Fila)
- [x] Rota `/publicacoes` com visões "Próximas" e "Recentes"
- [x] Cota do dia legível por projeto: "N/M hoje · janela 09:00–22:30 · próxima ~HH:MM" (hora decimal nunca exposta)
- [x] Sem "worker", "clone fura a fila", "plano"; prioridade do monitoramento apresentada como selo "Prioridade" discreto
- [x] Retries: aparecem só quando existem, como "nova tentativa às HH:MM", com motivo legível
- [x] Histórico (entregas) com datas "Hoje, 13:32" / "22/08 às 13:32" e status Publicada/Falhou/Enviando

## M7 — Fontes (ex-Copiador)
- [x] Rota `/fontes` com seções "Busca automática" (horários legíveis do ritmo, por projeto) e "Monitoramento de grupos"
- [x] Grupos monitorados por NOME (JID só em detalhes técnicos); adicionar/remover preservando contrato `clonador`
- [x] Frequência como presets legíveis (D12) — sem "varre a cada 180 seg"
- [x] Últimas oportunidades do monitoramento (clones) com linguagem de produto
- [x] Empty state honesto sem conexão WhatsApp (D16)

## M8 — Destinos (ex-Grupos & canais)
- [x] Rota `/destinos`: destino atual de cada projeto com nome do grupo e atividade de hoje
- [x] Trocar destino = "Usar este grupo" com confirmação clara (efeito: próximas publicações)
- [x] Lista de grupos da conexão com busca por nome
- [x] JID oculto por padrão (detalhes técnicos)
- [x] Empty state honesto sem conexão (D16)

## M9 — Mensagens (ex-Templates)
- [x] Rota `/mensagens` com preview em destaque (como ficará no WhatsApp)
- [x] Fluxo comum sem sintaxe `{token}`: rodapé, linha da loja, biblioteca de chamadas
- [x] Headlines como itens individuais (adicionar/remover/editar) por categoria com nome humano (D9)
- [x] Template base apenas em "Modo avançado" colapsado; validação de tokens continua na API
- [x] Sem "deploy", "restart" ou jargão técnico na página

## M10 — Ritmo & Regras (ex-Configurações do ritmo)
- [x] Rota `/ritmo` por projeto: publicações por dia (faixa), janela em HH:MM (conversão decimal na borda, D6)
- [x] Horários de busca como seleção de horas legível (chips), não "Coletas 7,15"
- [x] Validade da oferta em horas com explicação de produto
- [x] "Proporção de importados" só em Avançado, com explicação (específica do nicho)
- [x] Nenhuma hora decimal visível; validações da API preservadas

## M11 — Conexões
- [x] Cartões WhatsApp / Mercado Livre / Shopee com nomes de produto (sem "uazapi", sem env vars, sem ".mlcookie" no fluxo comum)
- [x] Estados: Conectado / Conectando / Precisa de atenção / Desconectado / Não configurada
- [x] Estrutura de lista por plataforma preparada para múltiplas contas (render de N itens)
- [x] Instrução de renovação da sessão ML em "Detalhes técnicos" (não no cartão principal)
- [x] Plataformas futuras (Amazon, Magalu, Shein, TikTok Shop, Telegram) como "Em breve" não clicáveis — sem simular funcionalidade

## M12 — Desempenho (ex-Analytics)
- [x] Rota `/desempenho` com filtro de período (7/14/30 dias) e projeto
- [x] KPIs de período + publicações por dia + horários + marcas (dados reais existentes)
- [x] Origem "Monitoramento" ao invés de "copiador"/"clones"; sem métricas inventadas
- [x] Não duplica o Dashboard (sem estado "agora": fila/saúde ficam fora)

## M13 — Configurações da conta + Ajuda + Logs
- [x] Rota `/configuracoes`: tracking de cliques (D7) com linguagem de produto + sessão (sair) + seções futuras honestas
- [x] Rota `/ajuda`: conceitos do produto (projeto, fonte, destino, publicação)
- [x] `/config` redireciona para `/ritmo`; tracking não aparece mais junto do ritmo
- [x] `/logs` com aviso de página técnica, fora da navegação

## M14 — Responsividade
- [x] 390px: dashboard, ofertas (tabela → cartões ou scroll controlado), publicações, fontes, destinos, mensagens, ritmo, conexões, desempenho, configurações sem overflow horizontal do body
- [x] 768px e 1280px: grids adaptam (2→4 colunas KPI etc.); sidebar visível ≥768px… (breakpoint md)
- [x] Modais/drawers cabem no viewport; botões alcançáveis

## M15 — Acessibilidade
- [x] Navegação por teclado completa no shell (menu, seletor de projeto, drawer com Escape/focus trap)
- [x] Labels programáticos em todos inputs/selects; botões são `<button>`
- [x] Estados não dependem só de cor (texto/ícone acompanham selos de status)
- [x] Headings hierárquicos (h1 único por página); `aria-current`, `aria-expanded` onde aplicável
- [x] Contraste: texto secundário e selos ≥ 4.5:1 sobre as superfícies usadas

## M16 — Regression & QA final
- [ ] `verify-redesign.sh` completo passa (lint, typecheck, build, tasks)
- [x] Testes Python continuam passando (87 OK; diff do motor vs main vazio)
- [x] QA visual das telas nos 4 breakpoints (Chrome headless + medição de overflow via scripts/harness/qa-wrap.html)
- [x] Grep de linguagem proibida na UI (worker, Postgres, Uazapi, JID, deploy, restart, LOG_PATH, slug de perfil, hora decimal) — zero ocorrências voltadas ao usuário (check-linguagem.sh)
- [x] Console do browser sem erros nas 10 telas validadas (Chrome headless --enable-logging)

## M17 — Final
- [ ] Auditoria adversarial (Parte 28) executada e correções aplicadas
- [ ] `docs/product/AFILIFY_REDESIGN_FINAL_REPORT.md` completo (Parte 29)
- [ ] PROGRESS atualizado; commits atômicos; `git status` limpo; sem push/merge
