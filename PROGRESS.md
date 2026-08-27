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
| 3 — Conexão WhatsApp (US1) | T013–T023 | 3 |
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

### 2026-08-26

- Auditoria do repositório, especificação, Clarify (13 perguntas em 4 rodadas), plano e task
  graph. Commit `1b09b92`.
