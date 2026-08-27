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

**Fase atual**: 3 — Conexão WhatsApp (P0), em paralelo com a 2
**Branch**: `feat/afilify-saas-redesign` (worktree isolada; sem push, sem merge, sem deploy)
**Produção**: intocada — roda na VPS/EasyPanel, com o modelo antigo

| Fase | Tarefas | Concluídas |
|---|---|---|
| 1 — Fundação bloqueante | T001–T007 | 6 (falta T005) |
| 2 — Contexto explícito no motor | T008–T012 | 0 |
| 3 — Conexão WhatsApp (US1) | T013–T023 | 9 |
| 4 — Projetos e Automações (US3) | T024–T030 | 0 |
| 5 — Fonte configurável (US4) | T031–T041 | 0 |
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

### 2026-08-26

- Auditoria do repositório, especificação, Clarify (13 perguntas em 4 rodadas), plano e task
  graph. Commit `1b09b92`.
