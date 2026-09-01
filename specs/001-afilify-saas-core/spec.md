# Feature Specification: Afilify — núcleo SaaS (domínio, conexões e fontes configuráveis)

**Feature Branch**: `feat/afilify-saas-redesign`

**Created**: 2026-08-26

**Status**: Draft — Clarify em andamento (sessão 2026-08-26)

**Input**: Product Brief "Evolução da Afilify para SaaS profissional" (2026-08-26) + auditoria do repositório (`audit.md`)

## Contexto

A Afilify hoje é um motor real em produção: encontra ofertas no Mercado Livre e Shopee,
gera link de afiliado e publica em grupos de WhatsApp com ritmo calibrado. O que funciona
funciona de verdade — e a operação de perfumes depende disso diariamente.

O que não existe é **produto**: um projeto é um arquivo Python, uma automação é um processo,
uma conexão é uma variável de ambiente, e os termos de busca estão dentro do código. Um
segundo usuário não conseguiria operar a plataforma sem um desenvolvedor.

Esta especificação cobre a passagem de ferramenta interna para SaaS: formalizar as entidades,
tornar as conexões autoatendidas, e transformar a busca em uma Fonte configurável por intenção.

## Escopo

**Dentro**: modelo de domínio (Workspace, Projeto, Automação, Conexão, Fonte, Destino, Oferta,
Publicação), conexão WhatsApp ponta a ponta, conexão Mercado Livre, Fonte de busca configurável
com teste prévio, revisão de Ritmo & Regras, Publicações, Mensagens, Dashboard e Desempenho sob
o novo vocabulário.

**Fora**: lógica do Clonador/monitoramento (dependência congelada — a captura, o casamento de
produto e a publicação imediata continuam como estão); billing e cobrança; novas plataformas
(Amazon, Magalu, Shein, TikTok Shop, Telegram); métricas de receita e conversão.

## Clarifications

### Session 2026-08-26

- Q: Qual a cardinalidade entre Projeto, Automação e Destino? → A: Projeto → N automações → N destinos (modelo completo)
- Q: Como cada workspace terá seu WhatsApp conectado? → A: Uma instância dedicada por conexão, provisionada pela Afilify
- Q: Como o usuário conecta a conta de afiliado do Mercado Livre? → A: Extensão de navegador que captura e renova a sessão
- Q: Quem precisa usar a plataforma ao final desta rodada? → A: Apenas a operação do próprio dono, mas com o sistema já arquitetado para clientes externos, sem retrabalho depois
- Q: Enquanto a extensão não existir, como o Mercado Livre fica conectado? → A: Como está hoje — a tela mostra o estado real e avisa, sem fluxo novo de conexão nesta rodada
- Q: Quanto da curadoria de qualidade vira configuração do usuário? → A: O mínimo possível — palavras-chave e onde buscar; o conjunto exato de controles ainda será definido
- Q: Como cada destino se comporta quando há vários? → A: Mesma oferta e mesma mensagem em todos, com intervalo entre os destinos para proteger os números
- Q: Quando a mesma oferta pode ser publicada de novo? → A: Quando o preço cair abaixo do já publicado; publicações vindas de monitoramento não são bloqueadas por essa regra
- Q: Quais controles a Fonte deve ter? → A: Palavras-chave, onde buscar, desconto mínimo e faixa de preço; exclusões em Avançado
- Q: Como evitar falsificação sem o usuário configurar marcas? → A: Tipo de nicho pronto por projeto somado a sinais automáticos do anúncio
- Q: A extensão do Mercado Livre entra nesta rodada? → A: Não, fica para a próxima rodada com spec própria
- Q: Há admin token no provedor de WhatsApp? → A: A ser confirmado; o contrato da API exige `admintoken` para criar instância, então o plano prevê fallback para instância existente
- Q: Deve haver teto de envios por número? → A: Sim, automático e decidido pela Afilify, invisível ao usuário
- Q: Como a operação atual passa para o novo modelo? → A: Não passa nesta rodada — tudo é construído e validado na worktree com grupo de teste, e o corte só acontece após validação manual e merge
- Q: Qual WhatsApp na validação? → A: O mesmo número da operação, publicando em grupo de teste separado


## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conectar o WhatsApp sem sair da Afilify (Priority: P1)

Um usuário abre Conexões, escolhe WhatsApp, dá um nome à conexão e vê um QR Code. Escaneia
pelo celular. A tela sai sozinha de "Aguardando leitura" para "Conectado", mostra o número
mascarado e a lista de grupos daquela conta. No dia seguinte a conexão continua lá; se o
telefone ficar offline, a Afilify avisa e oferece reconectar.

**Why this priority**: sem isso não há autoatendimento — hoje conectar um WhatsApp exige que
alguém com acesso ao servidor crie a instância e cole um token. É o gargalo do primeiro cliente.

**Independent Test**: criar uma conexão nova em conta limpa, escanear, publicar uma mensagem de
teste no grupo escolhido, derrubar a sessão pelo aparelho e reconectar — tudo pela interface.

**Acceptance Scenarios**:

1. **Given** um workspace sem conexões, **When** o usuário adiciona uma conexão de WhatsApp,
   **Then** um QR Code aparece em até 10 segundos e a tela indica que está aguardando a leitura.
2. **Given** um QR exibido, **When** o usuário escaneia, **Then** a tela muda para "Conectado"
   sem recarregar a página e mostra o número mascarado e o nome do perfil.
3. **Given** um QR exibido há mais tempo que sua validade, **When** ninguém escaneou,
   **Then** a tela informa que o código expirou e oferece gerar um novo, sem erro técnico.
4. **Given** uma conexão conectada, **When** o usuário recarrega a página ou volta no dia
   seguinte, **Then** o estado continua "Conectado" e os grupos permanecem disponíveis.
5. **Given** uma conexão conectada, **When** o aparelho perde a sessão,
   **Then** a Afilify mostra "Precisa reconectar", avisa no Dashboard e as automações que
   dependem dela informam por que estão paradas.
6. **Given** uma conexão conectada, **When** o usuário pede para sincronizar grupos,
   **Then** a lista é atualizada e mostra quando foi a última sincronização.

---

### User Story 2 - Conectar a conta de afiliado do Mercado Livre (Priority: P1)

O usuário conecta sua conta de afiliado do Mercado Livre à Afilify, confirma qual tag de
afiliado será usada, e a plataforma passa a gerar links atribuídos a ele. Quando a sessão
envelhece, a Afilify avisa antes de quebrar e explica em uma frase o que fazer.

**Why this priority**: sem atribuição correta, o usuário trabalha e outra pessoa recebe a
comissão. É a diferença entre um SaaS e um script compartilhado.

**Independent Test**: conectar uma conta, gerar um link a partir de um produto e verificar que
o link curto carrega a tag daquele usuário; expirar a sessão e verificar o aviso e a renovação.

**Acceptance Scenarios**:

1. **Given** um workspace sem conexão de Mercado Livre, **When** o usuário conclui a conexão,
   **Then** a Afilify confirma a conta e exibe a tag de afiliado ativa.
2. **Given** uma conexão ativa, **When** uma oferta precisa de link,
   **Then** o link gerado é atribuído à tag daquele workspace, nunca à de outro.
3. **Given** uma sessão perto de expirar, **When** o usuário abre a Afilify,
   **Then** vê um aviso antecipado com o prazo, não um erro depois da falha.
4. **Given** uma sessão expirada, **When** a automação tenta gerar link,
   **Then** as ofertas ficam retidas em estado recuperável (não descartadas) e o usuário lê
   "Sua conexão com o Mercado Livre expirou. Reconecte sua conta para continuar gerando ofertas."
5. **Given** dois workspaces distintos, **When** ambos operam,
   **Then** as credenciais de um nunca são visíveis nem utilizáveis pelo outro.

---

### User Story 3 - Criar um projeto e sua automação sem tocar em código (Priority: P1)

O usuário cria o projeto "Perfumes", dá um nome à automação ("Ofertas Mercado Livre"),
escolhe de onde vêm as ofertas, para onde vão, qual mensagem e em que ritmo. Liga. A automação
começa a trabalhar. Ele pode pausar, duplicar para outro nicho e excluir.

**Why this priority**: é a fundação. Sem a entidade, todo o resto continua amarrado a arquivos
e a um slug técnico; nenhuma outra tela pode ser multiprojeto de verdade.

**Independent Test**: criar um projeto novo pela interface, ligar a automação e ver uma
publicação real sair, sem editar arquivo nem reiniciar processo.

**Acceptance Scenarios**:

1. **Given** um workspace, **When** o usuário cria um projeto e uma automação com fonte,
   destino e mensagem definidos, **Then** a automação fica pronta para ativar sem intervenção técnica.
2. **Given** uma automação sem destino ou sem conexão exigida, **When** o usuário tenta ativar,
   **Then** a Afilify explica exatamente o que falta e não ativa pela metade.
3. **Given** uma automação ativa, **When** o usuário pausa,
   **Then** nenhuma publicação nova sai, o que já estava na fila é preservado, e a tela diz que está pausada.
4. **Given** dois projetos ativos, **When** ambos operam,
   **Then** ofertas, publicações, mensagens e ritmo de um nunca aparecem nem interferem no outro.
5. **Given** um projeto existente, **When** o usuário duplica,
   **Then** a cópia nasce pausada, sem histórico de ofertas e publicações do original.

---

### User Story 4 - Configurar o que a Afilify deve encontrar, e testar antes de ligar (Priority: P1)

Na automação, o usuário abre a Fonte "Busca Mercado Livre" e descreve o que quer encontrar:
palavras-chave, onde buscar, desconto mínimo, faixa de preço. Clica em "Testar busca" e vê,
em segundos, exemplos reais do que aquela configuração traria. Ajusta e liga.

**Why this priority**: é o que transforma a Afilify de "o agente do Júlio" em ferramenta de
qualquer nicho. Sem isso, cada novo nicho continua sendo um commit.

**Independent Test**: configurar uma busca para um nicho diferente de perfumes, testar,
ver resultados coerentes e depois confirmar que as ofertas coletadas correspondem ao teste.

**Acceptance Scenarios**:

1. **Given** uma Fonte de busca em branco, **When** o usuário informa palavras-chave e critérios,
   **Then** consegue salvar sem precisar entender nenhum parâmetro de execução.
2. **Given** uma configuração preenchida, **When** o usuário clica em "Testar busca",
   **Then** recebe uma contagem de itens compatíveis e uma amostra real com nome, preço e desconto.
3. **Given** um teste sem nenhum resultado, **When** a amostra volta vazia,
   **Then** a Afilify diz o que provavelmente está restringindo demais e sugere o ajuste.
4. **Given** uma Fonte ativa, **When** ela roda e encontra apenas ofertas já conhecidas,
   **Then** nada é duplicado e o usuário consegue ver que a coleta rodou mesmo sem novidades.
5. **Given** uma Fonte ativa, **When** a plataforma de origem responde com bloqueio ou erro,
   **Then** o usuário vê que a coleta falhou e por qual motivo em linguagem comum, e a automação
   não fica silenciosamente parada.

---

### User Story 5 - Acompanhar ofertas e publicações e agir sobre elas (Priority: P2)

O usuário vê o catálogo de ofertas encontradas, o que está para sair, o que já saiu e o que deu
problema. Pode segurar uma oferta, devolvê-la à fila ou publicá-la agora.

**Why this priority**: é a operação diária, mas depende do domínio (US3) estar formalizado.

**Independent Test**: encontrar uma oferta na lista, publicá-la em um destino e ver a publicação
registrada com horário, destino e resultado.

**Acceptance Scenarios**:

1. **Given** uma oferta encontrada, **When** ela é publicada em dois destinos,
   **Then** existem duas publicações distintas, cada uma com seu próprio resultado.
2. **Given** uma publicação que falhou, **When** o usuário abre o item,
   **Then** lê o motivo em linguagem comum e pode tentar de novo.
3. **Given** uma oferta antiga além da validade configurada, **When** a fila é servida,
   **Then** ela não é publicada e o usuário consegue entender por quê.

---

### User Story 6 - Ajustar ritmo e regras sem virar operador de infraestrutura (Priority: P2)

O usuário define quantas publicações por dia, em que janela de horário e por quanto tempo uma
oferta continua válida. Não vê dispersão, jitter, threads nem hora decimal.

**Why this priority**: o ritmo é decisão legítima do usuário, mas a página atual mistura decisão
de produto com constante interna calibrada.

**Independent Test**: alterar a janela e a cota e verificar que as publicações do dia seguinte
respeitam os novos limites.

**Acceptance Scenarios**:

1. **Given** uma automação ativa, **When** o usuário muda a janela de publicação,
   **Then** a interface informa a partir de quando a mudança passa a valer.
2. **Given** limites do plano, **When** o usuário tenta exceder,
   **Then** a Afilify informa o limite e o que fazer, sem falhar silenciosamente.

---

### User Story 7 - Entender o estado da operação em uma tela (Priority: P2)

O Dashboard responde três perguntas: está funcionando, o que aconteceu hoje, e o que precisa da
minha atenção. Nenhum termo de infraestrutura aparece.

**Independent Test**: com uma conexão caída e ofertas em erro, verificar que o Dashboard aponta
exatamente esses dois fatos e leva às telas onde se resolve cada um.

**Acceptance Scenarios**:

1. **Given** uma conexão caída, **When** o usuário abre o Dashboard,
   **Then** vê que a operação está interrompida e qual conexão resolver.
2. **Given** um indicador clicável, **When** o usuário clica,
   **Then** a lista de destino usa exatamente o mesmo critério do número exibido.

---

### Edge Cases

- QR expira enquanto o usuário procura o celular → novo código sob demanda, sem recriar a conexão.
- Usuário escaneia o QR com um WhatsApp diferente do pretendido → a Afilify mostra o número
  conectado antes de qualquer publicação, permitindo desfazer.
- Conexão de WhatsApp removida enquanto automações a utilizam como destino → o sistema impede
  ou avisa explicitamente quais automações ficarão paradas.
- Grupo de destino em que a conta perdeu permissão de enviar → publicação falha com motivo claro,
  e falhas repetidas do mesmo destino são sinalizadas em vez de repetidas indefinidamente.
- Sessão do Mercado Livre expira no meio de uma coleta → ofertas ficam retidas, não descartadas,
  e voltam a andar sozinhas quando a conexão é renovada.
- Mesma oferta encontrada pela busca e pelo monitoramento → uma única oferta, sem publicação dupla.
- Mesmo produto vendido por anúncios diferentes (ids distintos, título quase igual) → tratado
  como repetição para efeito de publicação.
- Preço cai de novo depois de já publicado → decidido pela regra de repromoção, não por acaso.
- Duas automações do mesmo workspace apontando para o mesmo grupo → o usuário é avisado do
  risco de dobrar o volume naquele grupo.
- Plataforma de origem responde com bloqueio anti-robô → tratado como falha recuperável e visível.
- Teste de busca disparado repetidamente → protegido contra abuso sem expor limites técnicos.
- Automação ativa sem nenhuma conexão válida → não fica "ativa" mentindo; estado próprio e visível.

## Requirements *(mandatory)*

### Requisitos funcionais — Domínio

- **FR-001**: O sistema DEVE representar Workspace, Projeto, Automação, Conexão, Fonte, Destino,
  Oferta e Publicação como entidades persistidas, não como arquivos de código ou variáveis de ambiente.
- **FR-002**: Usuários DEVEM conseguir criar, renomear, pausar, duplicar e excluir Projetos e
  Automações pela interface, sem reinício de processo e sem intervenção técnica.
- **FR-003**: O sistema DEVE isolar completamente os dados entre Projetos: ofertas, publicações,
  mensagens, fontes, destinos e ritmo pertencem a um Projeto e nunca vazam para outro.
- **FR-004**: O sistema DEVE isolar completamente os dados e credenciais entre Workspaces.
- **FR-005**: Todo nome exibido ao usuário DEVE ser um nome escolhido por ele ou um rótulo de
  produto; identificadores técnicos (slugs, ids de grupo, ids de anúncio, tokens) só podem
  aparecer em área avançada/administrativa explicitamente marcada.
- **FR-006**: O sistema DEVE tratar Oferta e Publicação como entidades distintas, permitindo que
  uma Oferta gere múltiplas Publicações com resultados independentes.
- **FR-007**: O sistema DEVE preservar o histórico de Publicações de um Destino mesmo quando o
  Destino da Automação é trocado.
- **FR-008**: A operação atual em produção (projeto de perfumes) DEVE continuar funcionando
  durante e depois da migração, sem perda de ofertas, publicações, configuração ou histórico.

### Requisitos funcionais — Conexões

- **FR-010**: Usuários DEVEM conseguir criar uma conexão de WhatsApp inteiramente dentro da
  Afilify, obtendo o código de pareamento sem contato com o provedor de infraestrutura.
- **FR-011**: O sistema DEVE expor os estados de conexão: criando, gerando código, código
  disponível, aguardando leitura, código expirado, conectando, conectado, desconectado,
  sessão perdida, reconectando e erro — em linguagem de produto.
- **FR-012**: O sistema DEVE atualizar o estado da conexão na tela sem exigir recarga manual
  enquanto o usuário aguarda o pareamento.
- **FR-013**: O sistema DEVE persistir a conexão de modo que ela sobreviva a recarga de página,
  reinício da plataforma e troca de dispositivo do usuário.
- **FR-014**: O sistema DEVE detectar perda de sessão e sinalizar ao usuário, sem esperar que
  ele descubra pela ausência de publicações.
- **FR-015**: Usuários DEVEM conseguir sincronizar grupos, renomear, reconectar e desconectar
  uma conexão de WhatsApp.
- **FR-016**: O sistema DEVE exibir grupos por nome, com identificador técnico apenas em
  detalhes avançados, e DEVE continuar permitindo selecionar grupos cujo nome não seja resolvível.
- **FR-017**: O sistema DEVE permitir conectar uma conta de afiliado do Mercado Livre e DEVE
  registrar qual tag de afiliado será usada nos links daquele workspace.
- **FR-018**: O sistema DEVE validar a conexão do Mercado Livre no momento da conexão, provando
  que ela consegue gerar um link atribuído à tag informada.
- **FR-019**: O sistema DEVE detectar e comunicar a expiração da sessão do Mercado Livre com
  antecedência, e DEVE reter (não descartar) as ofertas afetadas até a renovação.
- **FR-020**: O sistema DEVE armazenar credenciais de conexão cifradas em repouso e NUNCA
  exibi-las de volta ao usuário, nem em logs, nem em telas de detalhe técnico.
- **FR-021**: O sistema DEVE suportar mais de uma conexão por plataforma no mesmo workspace, e
  cada Automação DEVE declarar qual conexão utiliza.
- **FR-022**: O sistema DEVE impedir — ou avisar de forma inequívoca — a remoção de uma conexão
  que automações ativas utilizam.

### Requisitos funcionais — Fontes

- **FR-030**: A Fonte de busca DEVE expor exatamente quatro controles no fluxo comum: palavras-chave
  do que se quer encontrar; onde buscar (resultados da busca e/ou página de ofertas, combináveis);
  desconto mínimo; e faixa de preço. Palavras e marcas a excluir DEVEM existir em uma seção
  Avançado recolhida. Nenhum outro controle DEVE ser adicionado ao fluxo comum sem decisão explícita.
- **FR-031**: O sistema NÃO DEVE expor concorrência, timeouts, número de requisições, pausas,
  proxies, tentativas internas ou paginação técnica na configuração da Fonte.
- **FR-032**: O sistema DEVE oferecer "Testar busca": uma amostra executada sob demanda que
  retorna a contagem de itens compatíveis e exemplos reais com nome, preço e desconto.
- **FR-033**: O teste DEVE refletir os mesmos critérios que a Fonte usará quando ativa, de modo
  que a amostra seja previsão honesta e não demonstração.
- **FR-034**: O sistema DEVE deduplicar ofertas, garantindo que a mesma oportunidade encontrada
  mais de uma vez ou por fontes diferentes não gere publicação repetida.
- **FR-035**: O sistema DEVE registrar cada execução de coleta com seu resultado (quantas
  encontradas, quantas novas, falha e motivo), visível em linguagem comum.
- **FR-036**: O sistema DEVE permitir que o usuário defina quando a coleta acontece, sem expor
  o mecanismo de agendamento.
- **FR-037**: O sistema DEVE aplicar limites de uso por plano à execução de coletas e testes,
  comunicando o limite quando atingido.
- **FR-038**: A qualificação de ofertas (o que impede publicar falsificação, paralela e produto
  fora do padrão do nicho) NÃO É configurada pelo usuário. Ela vem de duas camadas combinadas:
  (a) um **tipo de nicho** escolhido na criação do Projeto, que traz curadoria pronta — marcas
  aceitas, palavras proibidas, unidade mínima; e (b) **sinais automáticos do próprio anúncio** —
  loja oficial, reputação do vendedor, avaliação e coerência de preço. As duas camadas DEVEM
  funcionar como barreiras independentes.
- **FR-039**: O sistema DEVE oferecer ao menos um tipo de nicho pronto por vertical suportada, e
  DEVE degradar com aviso — nunca em silêncio — quando um projeto for criado sem tipo de nicho
  correspondente.

### Requisitos funcionais — Publicação, mensagens e ritmo

- **FR-040**: Usuários DEVEM conseguir enviar publicações de uma Automação para mais de um Destino.
- **FR-041**: O sistema DEVE tornar visível a fila do dia, o histórico e as falhas, com motivo
  legível e ação de nova tentativa.
- **FR-042**: O sistema DEVE reter, e não descartar, ofertas que não puderam ser publicadas por
  falha de conexão ou de link, retomando quando a causa for resolvida.
- **FR-043**: Usuários DEVEM editar a mensagem publicada com pré-visualização fiel do resultado,
  usando uma oferta real do próprio projeto.
- **FR-044**: Usuários DEVEM controlar volume diário, janela de horário e validade da oferta;
  a Afilify DEVE decidir sozinha a distribuição interna dos envios dentro dessa janela.
- **FR-045**: O sistema DEVE informar a partir de quando cada mudança de ritmo entra em vigor.
- **FR-046**: O sistema DEVE aplicar um teto de segurança de envios por conexão conectada,
  independente da soma dos ritmos das automações que a utilizam, espaçando ou segurando envios
  para preservar a saúde da conta. Esse teto É decidido pela Afilify e NÃO DEVE aparecer como
  configuração do usuário; quando ele segurar publicações, o motivo DEVE ser visível em
  linguagem comum.

### Requisitos funcionais — Plataforma

- **FR-050**: O sistema DEVE autenticar usuários com contas próprias e associá-los a um workspace.
- **FR-051**: O sistema DEVE apresentar, em toda a experiência comum, apenas vocabulário de
  produto — a auditoria de linguagem faz parte do critério de pronto.
- **FR-052**: O sistema DEVE manter registros técnicos acessíveis em área administrativa,
  e DEVE apresentar eventos relevantes ao usuário de forma contextualizada na tela onde importam.
- **FR-053**: Todo estado exibido DEVE derivar de dado real; a plataforma NÃO DEVE simular
  sucesso, progresso ou disponibilidade.
- **FR-054**: O sistema DEVE tratar explicitamente estados de carregamento, vazio e erro em
  todas as telas da experiência comum.

### Requisitos funcionais — decisões da sessão de Clarify

- **FR-060**: O sistema DEVE provisionar uma instância dedicada por conexão de WhatsApp,
  criada pela própria Afilify no momento em que o usuário adiciona a conexão, de modo que a
  queda ou o bloqueio de uma conexão nunca afete outra. O número de conexões simultâneas DEVE
  ser um limite configurável do plano.
- **FR-061**: Um Projeto DEVE poder conter várias Automações, e cada Automação DEVE poder
  publicar em vários Destinos. Fontes, mensagem e ritmo pertencem à Automação, não ao Projeto.
- **FR-062**: O destino final da conexão com o Mercado Livre É uma extensão de navegador
  oficial da Afilify, que captura e renova a sessão da conta de afiliado do próprio usuário e a
  entrega cifrada à plataforma. Nenhuma outra forma de conexão assistida DEVE ser construída
  como solução intermediária.
- **FR-063**: Enquanto a extensão não existir, a renovação da sessão do Mercado Livre permanece
  fora da Afilify. A plataforma DEVE, ainda assim, exibir o estado real da sessão, avisar com
  antecedência da expiração e reter as ofertas afetadas — sem simular um fluxo de conexão que
  não existe.
- **FR-065**: Quando uma Automação tem vários Destinos, todos DEVEM receber as mesmas ofertas
  com a mesma mensagem, e o sistema DEVE aplicar um intervalo entre os envios aos diferentes
  destinos para proteger a saúde das contas conectadas. Esse intervalo É decisão da Afilify,
  não configuração do usuário.
- **FR-066**: Uma Oferta já publicada em um Destino DEVE voltar à fila daquele Destino quando
  seu preço cair abaixo do preço da publicação anterior, e apenas nesse caso.
- **FR-067**: Publicações originadas de monitoramento de grupos NÃO DEVEM ser bloqueadas pela
  regra de repetição: quando o monitoramento identifica uma oportunidade, ela é publicada
  mesmo que a mesma oferta tenha saído recentemente.
- **FR-064**: A plataforma DEVE funcionar para um único workspace nesta fase, porém sem
  nenhuma decisão de modelagem que impeça múltiplos workspaces, múltiplos usuários e limites
  por plano depois — chaves de workspace, isolamento e limites existem desde já, mesmo que a
  interface de cadastro e cobrança não seja construída agora.

### Key Entities

- **Workspace**: a conta. Contém usuários, assinatura, conexões e configurações globais.
- **Projeto**: uma operação/nicho ("Perfumes"). Agrupa automações e é a unidade de isolamento
  de dados operacionais. Sucede o atual `perfil`.
- **Automação**: como um processo funciona dentro de um projeto ("Ofertas Mercado Livre").
  Combina fontes, destinos, mensagem, ritmo e as conexões de que depende. Tem estado próprio
  (rascunho, ativa, pausada, impedida) e é o que liga e desliga.
- **Conexão**: uma conta externa que a Afilify consegue operar (WhatsApp, Mercado Livre
  Afiliados, Shopee Afiliados). Pertence ao Workspace, guarda credencial cifrada e estado de sessão.
- **Fonte**: de onde as ofertas são descobertas (busca automática, monitoramento). Guarda a
  intenção do usuário e o histórico de execuções.
- **Destino**: para onde as publicações vão (grupo de WhatsApp hoje). Referencia uma Conexão e
  um alvo dentro dela, com nome legível.
- **Oferta**: a oportunidade encontrada — produto, preços, desconto, origem, link de afiliado
  e validade. Pertence a um Projeto.
- **Publicação**: uma execução de uma Oferta em um Destino, com horário, resultado, tentativas
  e mensagem efetivamente enviada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário novo conecta seu WhatsApp e vê seus grupos em menos de 3 minutos,
  sem ajuda e sem acessar nada fora da Afilify.
- **SC-002**: Um usuário cria um projeto, configura uma fonte, testa a busca e ativa a automação
  em menos de 15 minutos, sem editar arquivo, sem reiniciar nada e sem suporte.
- **SC-003**: Nenhum termo de implementação aparece na experiência comum — verificado por
  auditoria automatizada de vocabulário sobre todas as telas de usuário.
- **SC-004**: 100% dos estados de conexão listados são reproduzíveis e verificados contra o
  serviço real, incluindo expiração, queda e reconexão.
- **SC-005**: "Testar busca" devolve amostra em até 30 segundos, e o que a fonte coleta depois
  corresponde ao que a amostra prometeu.
- **SC-006**: Nenhuma oferta é perdida por falha de conexão ou de link: 100% das afetadas ficam
  retidas e retomam sozinhas após a renovação.
- **SC-007**: Dois projetos ativos no mesmo workspace operam sem nenhum vazamento de dados entre si.
- **SC-008**: A operação de perfumes em produção mantém seu volume e sua taxa de erro após a
  migração, medidos na semana seguinte ao corte.
- **SC-009**: Nenhuma tela da experiência comum exibe dado simulado; toda ausência de dado
  aparece como estado vazio honesto.

## Assumptions

- Esta rodada atende apenas a operação do próprio dono (um workspace). Cadastro público,
  onboarding de terceiros, permissões e cobrança ficam fora do escopo — mas o modelo de dados,
  o isolamento e os limites nascem prontos para eles, para que abrir a plataforma depois seja
  configuração e interface, nunca migração de dados.
- O Clonador continua funcionando exatamente como está; a modelagem trata "monitoramento" como
  um tipo de Fonte para efeito de leitura e apresentação, sem alterar sua lógica.
- A Shopee permanece com credencial de API oficial e não exige fluxo de sessão.
- O motor continua rodando fora do navegador, em processo próprio; a interface nunca executa
  a automação diretamente.
- Português do Brasil é o idioma da interface; internacionalização está fora desta fase.
- Nesta rodada NÃO há migração da operação viva. Todo o sistema é construído e validado na
  worktree, com publicações reais em um grupo de teste, usando a conexão de WhatsApp que já
  existe. O corte da operação de perfumes acontece somente depois da validação manual do dono
  e do merge — e será especificado então, preservando ofertas, publicações e histórico.
- A validação usa o mesmo número de WhatsApp da operação. Em consequência, exercícios de queda,
  reconexão e volume DEVEM ser conduzidos de forma a não ameaçar a conta que sustenta o grupo
  em produção — essa é uma restrição de projeto, não um detalhe de teste.
- O trabalho acontece na worktree `feat/afilify-saas-redesign`, sem merge, push ou deploy
  automáticos, e sem alterar `main`.
