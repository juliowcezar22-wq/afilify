# Progresso — núcleo SaaS da Afilify

Estado verificável do trabalho. **Este arquivo é a memória do projeto entre sessões** — o que
não está aqui não aconteceu.

Fonte de verdade das tarefas: [`specs/001-afilify-saas-core/tasks.md`](specs/001-afilify-saas-core/tasks.md)
Decisões: [`specs/001-afilify-saas-core/decisions.md`](specs/001-afilify-saas-core/decisions.md)
Evidências de validação: [`VALIDATION.md`](VALIDATION.md)

Regra: uma tarefa só é marcada concluída em `tasks.md` depois que a linha correspondente aqui
tem evidência — o que foi verificado, com que dado, e qual gate passou.

---

## Situação

**Fase atual**: 6 — Publicações e destinos (Fases 1–5 fechadas)
**Branch**: `feat/afilify-saas-redesign` (worktree isolada; sem push, sem merge, sem deploy)
**Produção**: intocada — roda na VPS/EasyPanel, com o modelo antigo

| Fase | Tarefas | Concluídas |
|---|---|---|
| 1 — Fundação bloqueante | T001–T007 | ✓ 7 de 7 |
| 2 — Contexto explícito no motor | T008–T012 | ✓ 5 de 5 |
| 3 — Conexão WhatsApp (US1) | T013–T023 | ✓ 11 de 11 |
| 4 — Projetos e Automações (US3) | T024–T030 | ✓ 7 de 7 |
| 5 — Fonte configurável (US4) | T031–T041 | ✓ 11 de 11 |
| 6 — Publicações e destinos (US5) | T042–T049 | 0 |
| 7 — Ritmo, Dashboard, conexões (US6/US7) | T050–T055 | 0 |
| 8 — Mensagens, desempenho, área técnica | T056–T060 | 0 |
| 9 — Fechamento | T061–T067 | 0 |

---

## Registro

### 2026-08-27

- **T001 · harness de execução** — `PROGRESS.md`, `VALIDATION.md` criados; tarefas e decisões
  reaproveitam os arquivos da spec, sem cópia paralela que possa divergir.
  Gate: `stop-guard.sh` religado para `specs/001-afilify-saas-core/tasks.md`.
- **T002 · gates de qualidade** — `check-mock.sh` (nada simulado no caminho de produção) e
  `guarda-congelados.sh` (Clonador e monitoramento intocados) criados e **testados com violação
  real**: ambos bloquearam com saída 1 e voltaram a passar após reverter.
  `verify-nucleo.sh` reúne os sete gates da rodada, incluindo a suíte do motor.
- **T003 · guarda do banco** — `guarda-banco.sh` recusa `DATABASE_URL`/`SQLITE_PATH` apontando
  para a operação (`afilify-db`, `julio_db`, IP da VPS, `easypanel.host`, `dados/` do projeto
  principal). Testado nos dois sentidos: bloqueia produção, libera validação.

- **T004 · entidades** — `db/0009_entidades.sql` cria 11 tabelas. Escrita em dialeto que roda
  igual nos dois bancos, para não existirem duas versões do schema: `abrir_banco()` aplica o
  MESMO arquivo no SQLite que o `psql` aplica no Postgres. Verificado: banco temporário nasce
  com as 11 tabelas novas + as 8 antigas, e as 87 testes antigos continuam passando.
- **T006 · cifra de credenciais** — `nucleo/cripto.py` (AES-256-GCM, chave mestra em
  `AFILIFY_CHAVE_MESTRA`). O contexto entra como dado autenticado: credencial de uma conexão
  não abre no lugar de outra. 13 testes, incluindo adulteração detectada e chave trocada.
  `cryptography` isolada em `.venv` da worktree — o Python do sistema não foi alterado.
- **T007 · tipos de nicho** — `nucleo/tipos_nicho.py` materializa a curadoria de `nichos/*.py`
  como dado. Verificado com os nichos reais: Perfumes com 157 marcas em 4 famílias e 31
  palavras proibidas; Casa com 29 marcas. 11 testes, um deles garantindo que termos de busca
  **não** entram na curadoria (eles pertencem à Fonte, D28).
- **Pendência registrada**: o DDL foi exercitado no SQLite; falta exercitá-lo no Postgres real
  (sem servidor local, Docker parado). Entra no fechamento (T064).

**Suíte**: 111 testes, todos passando (87 herdados + 24 novos). Gates de congelados, anti-mock
e linguagem: ✓.

- **T013 · risco do provisionamento, resolvido** — criada instância descartável na conta real:
  `POST /instance/create` devolveu 200 com `info` **vazio**. O aviso de "apagada em 1 hora" que
  aparece no OpenAPI era exemplo, não comportamento desta conta. `DELETE /instance` removeu, e
  a listagem voltou às duas instâncias originais. **O provisionamento automático fica em pé.**
- **T014 · cliente de WhatsApp** — `nucleo/conexoes/whatsapp.py`: criar, adotar, parear (QR e
  código digitável), consultar, desconectar, apagar, listar/criar grupos, limites do número e
  espaçamento nativo. É o único módulo que sabe qual é o fornecedor.
  Verificado contra a conta real: 2 contas traduzidas para estados de produto, 4 grupos por
  nome, diagnóstico de limites respondendo "sem restrição".
- **T015 · tradutor de estados** — quatro estados do provedor viram os onze do produto. Estado
  desconhecido vira `erro`, nunca "conectado" — um estado novo do fornecedor não pode ser lido
  como "está tudo bem".
- **T022 (parcial) · testes** — 23 testes do cliente, sem rede, sobre respostas capturadas da
  API real. Cobrem o que quebra na prática: já conectado antes de a tela pedir, resposta sem
  código, grupo sem nome, queda de rede — e garantem que nenhuma mensagem de usuário cita
  fornecedor, token ou código HTTP.

**Descoberta útil**: já existe um grupo chamado `Teste` (2 participantes) na conta de produção —
serve como grupo de validação sem criar nada novo (D33).

- **T016, T018, T021 · conexão ponta a ponta no painel** — cifra interoperável entre motor e
  painel (testada nos dois sentidos), repositório de conexões, seis rotas e a tela com QR,
  contagem regressiva do código, sincronizar grupos, desconectar e remover.
  Exercitado contra o serviço real: QR de 1842 caracteres gerado, credencial gravada cifrada
  (`v1.…`, 90 caracteres), ciclo `aguardando_leitura → codigo_expirado → aguardando_leitura`.
- **T022 · testes da tradução de estados** — 8 casos, importando o módulo real (`lib/estados.ts`),
  rodando no test runner do Node sem dependência nova. Ligados ao `fast-check`.

**Três defeitos encontrados pelo teste com serviço real, não por revisão de código:**

1. **Rotas invisíveis** — `route.ts` exportava um utilitário além dos handlers, e o Next
   descartou as seis rotas **sem erro**. Só apareceu ao conferir a saída do build linha a linha.
   Corrigido movendo para `lib/resposta.ts`.
2. **"Conectando" enganoso** — o provedor fica em `connecting` durante todo o pareamento
   pendente. Traduzido direto, a tela dizia "Conectando" enquanto, na verdade, esperava o
   usuário pegar o celular — e o código venceria sem nada mudar na tela. Depois de vencido,
   `connecting` ainda apagava o aviso de expiração, prendendo a conexão. A lógica virou função
   pura em `lib/estados.ts`, com teste para cada engano.
3. **Remoção destrutiva** — remover uma conexão apagava a conta no provedor mesmo quando ela
   tinha sido **adotada** (já existia antes da Afilify). Durante o teste isso apagou a
   instância `Pessoal` da conta real. Ela estava desconectada, então nenhuma sessão de WhatsApp
   caiu; foi recriada em seguida. Corrigido: só destruímos o que nós criamos
   (`provisionadaPelaAfilify`), e o teste de integração confirma que a conta adotada sobrevive.

- **T023 · US1 validada pelo dono** — conexão criada e pareada por dentro da Afilify; a
  instância nasceu na conta do provedor e aparece lá como `connected`. Os seis cenários de
  aceitação da US1 estão cobertos.
- **Limite de conexões — falha encontrada pelo uso real** — o painel do provedor mostrou
  "3 total de instâncias" com limite de 2, o que parecia excesso. Não era: o limite é de
  instâncias **conectadas**, e havia 2. Mas a checagem da Afilify estava errada em dois pontos:
  contava conexões **criadas** (recusaria o usuário cedo demais, com uma conta desconectada
  ocupando lugar que não ocupa) e **nenhum dos dois clientes tratava 429** — atingir o limite
  viraria "Algo deu errado por aqui", sem dizer o que fazer.
  Corrigido nos dois lados; 503 também passou a ter mensagem própria. Provado com o limite
  real: adotar a terceira instância passa, conectar devolve
  "Todos os seus WhatsApps disponíveis já estão conectados. Desconecte um antes de conectar outro."

- **T005 · Oferta e Publicação** — `db/0010`: identidade da oferta por projeto (a mesma oferta
  passa a existir em dois projetos sem colidir) e publicação com identidade própria (a mesma
  oferta em dois destinos, e republicação por queda de preço, ambas impossíveis antes).
  14 testes de integridade, cada um cobrindo um caso que o modelo antigo não comportava.
- **T017 · avisos de conexão** — assinatura do evento de estado na plataforma, rota pública
  protegida por chave secreta, e a consulta de estado mantida como rede de segurança. O aviso
  chega no painel, nunca no motor — mesmo princípio já adotado para o monitoramento.
- **T020 · queda visível** — Dashboard passa a mostrar conexões com problema antes de qualquer
  contagem de ofertas, dizendo que as automações dependentes não publicam e levando à tela
  onde se resolve.
- **Gate de fase** (`scripts/harness/fase.sh`) — uma fase só fecha sem tarefa aberta E com
  verificação completa passando. Na primeira tentativa ele **barrou** o fechamento da Fase 1:
  meus testes novos criavam banco temporário sem o prefixo `afilify-test-` e derrubavam a
  guarda que outros testes usam para recusar banco real. Corrigido e fechado.

**Fases 1 e 3 fechadas com verificação completa.**


### Fase 5 — fonte configurável e teste de busca (2026-08-27)

A promessa central do brief: um nicho novo passa a ser configuração, não commit.

**Quatro campos, e só**: palavras-chave, onde buscar, desconto mínimo, faixa de preço.
Exclusões em Avançado. A recusa de parâmetro técnico vale **no contrato** — mandar
`concurrency` ou `timeout` direto pela API devolve "Esta fonte recebeu uma configuração que a
Afilify não reconhece", não um campo escondido na tela.

**O canal painel → motor** (`comandos`): em produção os dois são contêineres separados que só
compartilham o banco. O painel deixa o pedido, o motor pega, executa e devolve. Pedido velho
não é executado — expira e a tela diz "a automação não está rodando agora", em vez de girar
para sempre.

**Testar busca com dado real**, medido nesta sessão contra o Mercado Livre:

| Critérios | Compatíveis |
|---|---|
| sem filtro | 16 |
| desconto ≥ 30% | 12 |
| ≥ 30% e até R$ 200 | 6 |
| desconto ≥ 80% | 0 — "provavelmente o desconto mínimo de 80% está restringindo demais" |

**Descoberta importante**: o Mercado Livre está **bloqueando a busca logada** agora (devolve a
página de captcha `/captcha/wall/logged` em vez dos resultados). A vitrine `/ofertas`, que não
exige sessão, continua respondendo normalmente. Isso virou tratamento de primeira classe: o
bloqueio tem erro próprio e mensagem própria, e **não** é confundido com "critérios apertados
demais" — senão o usuário passaria horas mexendo em filtros para consertar algo que não é dele.

**Dois defeitos meus, encontrados pelo teste real**: chamei `extrair_ofertas_json` com um
argumento a menos, e um `except Exception: pass` engoliu o erro — a função devolvia zero em
silêncio. Removido o `pass`; o erro apareceu na hora seguinte e foi corrigido.

A agenda da fonte manda no motor: horários configurados na tela são os horários em que a coleta
acontece. Sem isso, o usuário mexeria numa configuração que parece funcionar e não funciona.

200 testes passando.

### Fase 4 — projetos e automações (2026-08-27)

O que a Fase 2 destravou virou produto: criar projeto, criar automação, ligar e pausar — tudo
pela tela, sem arquivo, sem reinício.

**A regra que dá o tom: automação não liga pela metade.** Sem fonte, sem destino, ou com a
conexão caída, a ativação é recusada e a tela diz exatamente o que falta, em frases de gente
("escolher para onde publicar", "conectar \"Principal\" — ela está desconectada"). Nada de
"ativa com um problema" publicando no vazio.

Verificado ponta a ponta contra o serviço real:

| Passo | Resultado |
|---|---|
| Criar projeto com tipo de nicho | Perfumes · curadoria de perfumes aplicada |
| Nome repetido | "Você já tem um projeto chamado Perfumes." |
| Ligar sem fonte nem destino | recusado, 2 pendências nomeadas |
| Ligar com a conexão caída | recusado, dizendo qual conta reconectar |
| Ligar com tudo pronto | ativa |
| Supervisor enxerga a automação nova | "Perfumes · Ofertas Mercado Livre" |
| Duplicar | cópia nasce pausada, com a receita, sem histórico |
| Mesma oferta em dois projetos | sem colisão, cada um vê a sua |

**Defeito encontrado no teste**: duplicar devolvia `estado: ativo` para um projeto que ficava
`pausado` no banco — eu retornava o objeto lido antes de pausar. A tela mostraria um estado que
não existe. Corrigido e conferido contra o banco.

### Fase 2 — contexto explícito no motor (2026-08-27)

O risco central do plano, pago. `nucleo/comum.py` resolvia o projeto no import,
congelando dezenas de constantes de módulo — era por isso que criar um projeto exigia escrever
arquivo e reiniciar, e por isso que `runner.py` documentava a refatoração como "risco alto".

**A saída não foi reescrever, foi trocar a fonte.** As constantes continuam existindo (os
módulos as importam com `import *`, e trocá-las por chamadas quebraria tudo), mas agora
**derivam** de um objeto `Contexto` resolvido uma vez no início do processo. O contexto vem de
uma de duas fontes, e o motor é indiferente a qual:

    AUTOMACAO_ID=…   automação criada na interface, lida do banco
    PERFIL=…         arquivo perfis/*.py — a operação de sempre

- **T008** `nucleo/contexto.py` — projeto, automação, ritmo, destinos, monitoramento e
  curadoria num objeto só, com os dois construtores.
- **T009** as constantes derivam do contexto. Banco indisponível cai no arquivo: projeto novo
  indisponível é ruim, a operação viva parar é pior.
- **T010** trava e plano do dia passaram a ser por **automação**, não por projeto — senão a
  segunda automação de um projeto roubaria a cota da primeira e as duas disputariam a mesma
  trava. Ofertas continuam pertencendo ao projeto.
- **T011** `runner.py` supervisiona automações vindas do banco e perfis de arquivo do mesmo
  jeito. Ligar um projeto na tela sobe o processo dele no próximo ciclo.
- **T012** comparação constante a constante contra os dois arquivos de perfil: **idêntico**.
  Cota, janelas, dispersão, proporção, coletas, validade, destino e nicho — nada mudou.

169 testes passando (148 + 21 novos), incluindo três que sobem processo de verdade para provar
os dois modos de resolução.

### 2026-08-26

- Auditoria do repositório, especificação, Clarify (13 perguntas em 4 rodadas), plano e task
  graph. Commit `1b09b92`.
