# Afilify Constitution

Princípios inegociáveis desta plataforma. Derivados do Product Brief de 2026-08-26,
seção "O que está definido e não precisa ser reaberto". Nenhuma spec, plano ou task
pode contrariá-los sem emenda explícita registrada aqui.

## Core Principles

### I. O usuário configura intenção, nunca infraestrutura (NÃO NEGOCIÁVEL)

A experiência comum não contém worker, JID, Redis, Postgres, EasyPanel, uazapi, cookie,
polling, scraper, job, retry, deploy, restart, payload, endpoint, token, slug técnico
(`perfumes-ml`) nem hora decimal. Onde o dado técnico for necessário para diagnóstico,
ele vive em área avançada ou administrativa explicitamente marcada.

Para cada controle da interface valem duas perguntas obrigatórias: isso é necessidade
real do usuário ou está aí porque o backend funciona assim? E: essa decisão é do usuário
ou da Afilify? Variável de backend não vira campo de formulário por inércia.

### II. Domínio formalizado

Workspace → Projeto → Automação → (Fontes, Destinos, Mensagens, Ritmo). Conexão pertence
ao Workspace e é distinta de Destino. Fonte é distinta de Destino. Oferta é conceitualmente
distinta de Publicação: uma Oferta pode gerar várias Publicações. Nenhuma entidade do
produto pode continuar existindo apenas como arquivo de código ou variável de ambiente.

### III. Nada de funcionalidade simulada (NÃO NEGOCIÁVEL)

Estado exibido deriva de dado real. É proibido mock tratado como produção, sucesso falso,
progresso decorativo e disponibilidade fingida. Uma feature só está pronta ponta a ponta:
criação, persistência, refresh, queda, reconexão, erro, estado vazio. Redesign visual
sozinho não é entrega.

### IV. Execução verificável

O estado do trabalho vive em arquivos persistentes (TASKS, PROGRESS, DECISIONS, status de
teste e validação), não na memória da conversa. Concluir exige critério verificável:
build, lint, typecheck, testes, QA de browser/console/network, regressão, e nenhuma tarefa
P0/P1 acionável em aberto. Auditoria de vocabulário faz parte dos testes.

### V. Isolamento e respeito à operação viva

A operação de perfumes roda em produção e não pode ser interrompida ou degradada. O
Clonador/monitoramento é dependência congelada nesta rodada — sua lógica e seus arquivos
não são alterados. O trabalho acontece em worktree isolada; sem merge, push, deploy ou
alteração de `main` sem autorização explícita.

## Referências e limites

Afflink é benchmark de simplicidade, organização de menu, onboarding e percepção de
automação. Não é fonte de código, identidade visual, textos, layout ou componentes. A
Afilify tem identidade e arquitetura próprias.

Registros técnicos não são feature principal do cliente: eventos relevantes aparecem
contextualizados na tela onde importam; o log cru mora no ambiente administrativo.

Credenciais de conexão são cifradas em repouso, nunca reexibidas, nunca registradas em log,
e nunca acessíveis entre workspaces.

## Fluxo de trabalho

Auditar → Spec → Clarify → decisões do dono do produto → Spec atualizada → Plan → Tasks →
Harness → Implementação → QA humano final. Implementação não começa antes do Clarify
concluído. Depois do Clarify fechado, a execução avança com mínima intervenção humana até
a Definition of Done — sem pedir autorização tarefa a tarefa e sem declarar conclusão
porque a interface ficou bonita.

## Governance

Esta constitution prevalece sobre qualquer outra prática do repositório. Emendas exigem
registro datado nesta página com motivo. Decisões de produto tomadas durante o Clarify são
registradas em `specs/*/decisions.md` e não são reabertas sem novo fato.

**Version**: 1.0.0 | **Ratified**: 2026-08-26 | **Last Amended**: 2026-08-26
