# Afilify — Plano de Redesign da UI

Estado de origem (auditoria, 2026-08-22): painel Next.js 16.3.1 (App Router,
RSC), Tailwind 4 (tokens em `@theme` no globals.css), zero componentes
compartilhados, 10 páginas sob `app/(app)/`, dados via SQL direto
(`lib/dados.ts`), sem testes de frontend.

## Problemas encontrados na auditoria

**App shell**
- Sidebar não é sticky: em páginas longas ela rola junto e desaparece.
- Sem estado ativo na navegação; sem navegação mobile (sidebar some em <md
  e não há substituto).
- Sem contexto de projeto: slugs (`perfumes-ml`) repetidos em cada card.

**Linguagem técnica exposta** (viola regra de abstração)
- Dashboard: "banco SQLite (local)/Postgres", "Worker · perfumes-ml",
  "nenhum worker deu sinal ainda", badge "clone".
- Fila: "O worker publica no ritmo do plano", "clone fura a fila",
  "tentativa N", datas `MM-DD HH:mm`.
- Canais: JID como texto primário, "Salvar destino", "(fora da conta?)".
- Copiador: "varre a cada N seg", JIDs visíveis.
- Templates: sintaxe `{nome}`/`{link}` obrigatória, headlines em textarea
  gigante, "sem deploy, sem restart".
- Config: hora decimal (8.75), "Coletas (horas…)", "Proporção de importados
  (0–1)", tracking misturado com ritmo.
- Conexões: "WhatsApp (uazapi)", "Linkbuilder → F12 → Cookie → .mlcookie",
  "UAZAPI_* não configuradas".
- Logs: "Logs do motor" na navegação principal.
- Ofertas: placeholder "nome, marca ou MLB…", MLB id na linha principal.

**UI/UX**
- Overflow: linha de "Últimas publicadas" no Dashboard estoura porcentagem
  fora do container em telas estreitas (flex sem min-w-0 em todos os pontos).
- Paginação de ofertas sem total legível ("página 1/10" sem intervalo).
- Estados vazios crus ("nenhum worker deu sinal ainda", tabela vazia).
- Foco/acessibilidade: outline-none sem focus-visible substituto em inputs;
  selects/inputs sem label programático em vários pontos.

## Direção

1. **App Shell primeiro**: layout `h-dvh` com sidebar fixa (scroll próprio),
   header com seletor de projeto, `<main>` com scroll independente. Drawer
   de navegação no mobile. Estados ativos via `usePathname`.
2. **Design system enxuto**: manter identidade dark + verde-neon como acento
   raro. Tokens novos (focus, surfaces, danger/success/warning suaves) no
   `@theme`. Componentes em `painel/components/ui/`: Button, Card, Badge,
   Input, Select, Field, EmptyState, PageHeader, Stat, Tabela (wrapper),
   Paginacao, DetalhesTecnicos (collapsible). Sem biblioteca externa.
3. **Contexto de projeto**: `lib/projetos.ts` (slug → nome amigável +
   fallback humanizado), cookie `afilify_projeto`, seletor no shell.
   Páginas de operação filtram pelo projeto ativo; "Todos os projetos"
   disponível onde agregação faz sentido.
4. **Rotas novas com redirect das antigas** (ver MIGRATION_MAP).
5. **Tradução de linguagem** em todas as páginas (ver PRODUCT_ARCHITECTURE §3),
   com "Detalhes técnicos" colapsável onde o dado interno tem valor real.
6. **Datas**: helper `lib/formatos.ts` — "Hoje, 13:32" / "22/08 às 13:32",
   moeda pt-BR, hora decimal ↔ HH:MM (conversão só na borda da UI; o banco
   continua decimal — contrato do motor intocado).

## Página a página

- **Dashboard**: KPIs "Ofertas encontradas hoje", "Publicações hoje",
  "Aguardando publicação", "Precisam de atenção" (clicável → /ofertas
  filtrado). Saúde percebida: "Funcionando normalmente" / "N itens precisam
  de atenção" (heartbeat + erros, sem a palavra worker). Recentes em grid
  estável (hora · produto · desconto) sem overflow.
- **Ofertas**: busca "Buscar produto ou marca", filtros separados
  Status (Todas/Aguardando/Publicadas/Com problema) × Origem
  (Busca/Monitoramento), paginação "1–40 de N", nome em 2 linhas com
  line-clamp, id técnico fora da linha principal.
- **Publicações** (ex-Fila): visões "Próximas" e "Recentes"; cota do dia por
  projeto ("34/80 hoje · janela 09:00–22:30 · próxima ~13:40"); retries só
  aparecem quando existem, como "nova tentativa às HH:MM"; sem linguagem de
  implementação.
- **Fontes** (ex-Copiador): "Busca automática" (horários legíveis, do ritmo)
  e "Monitoramento de grupos" (grupos por nome, frequência traduzida,
  últimas oportunidades). JIDs ocultos.
- **Destinos** (ex-Grupos & canais): destino atual por projeto (nome do
  grupo), trocar destino = "Usar este grupo", lista de grupos da conexão
  com busca; JID em detalhes técnicos.
- **Mensagens** (ex-Templates): preview em destaque; edição comum sem
  sintaxe: rodapé, linha da loja, biblioteca de chamadas (headlines como
  itens individuais adicionar/remover por categoria com nomes humanos);
  template base só em "Modo avançado" (colapsado, com validação já
  existente da API).
- **Ritmo & Regras** (ex-Configurações): por projeto — publicações por dia
  (faixa), janela em HH:MM, horários de busca como chips, validade;
  "Proporção de importados" vai para "Avançado" com explicação (específico
  do nicho perfumes); jitter/dispersão permanecem internos (não expostos).
- **Conexões**: cartões WhatsApp / Mercado Livre / Shopee com estados
  Conectado/Conectando/Precisa de atenção/Desconectado, nome amigável,
  estrutura de lista preparada para múltiplas contas; instruções técnicas de
  renovação só em detalhes; sem nomes de env/provider. Plataformas futuras
  aparecem como "Em breve" não clicáveis.
- **Desempenho** (ex-Analytics): filtro de período (7/14/30 dias) e projeto;
  KPIs + publicações por dia + horários + marcas; sem duplicar o Dashboard
  (foco em período/padrões).
- **Configurações** (conta): tracking de cliques (movido do antigo /config),
  sessão/sair; estrutura visual preparada para perfil/workspace/assinatura
  ("Em breve", honesto).
- **Ajuda**: página simples com conceitos do produto (o que é projeto,
  fonte, destino) — barata e útil.
- **Logs**: sai da navegação; rota continua acessível (operação/admin),
  com aviso de página técnica.

## O que NÃO muda

- Nenhum comportamento do motor; nenhuma escrita nova no banco além dos
  contratos existentes (`config`, ações de oferta).
- Validações da API `/api/config` (continuam a proteger o motor).
- Auth/middleware/tracking/rota `/r/[codigo]`.
- Página de login (ajustes cosméticos só se necessário).

## Classificação (Parte 25)

- NECESSÁRIO: shell, navegação, tradução de linguagem, páginas acima.
- RECOMENDADO: busca de grupos em Destinos, biblioteca de headlines, filtro
  de período em Desempenho, página Ajuda.
- FUTURO (não implementar): QR code de conexão WhatsApp no painel (endpoint
  não confirmado), multiusuário, assinatura, novas plataformas, editor
  drag-and-drop de mensagem, dashboards customizáveis.
