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

**Fase atual**: 1 — Fundação bloqueante
**Branch**: `feat/afilify-saas-redesign` (worktree isolada; sem push, sem merge, sem deploy)
**Produção**: intocada — roda na VPS/EasyPanel, com o modelo antigo

| Fase | Tarefas | Concluídas |
|---|---|---|
| 1 — Fundação bloqueante | T001–T007 | 3 |
| 2 — Contexto explícito no motor | T008–T012 | 0 |
| 3 — Conexão WhatsApp (US1) | T013–T023 | 0 |
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

### 2026-08-26

- Auditoria do repositório, especificação, Clarify (13 perguntas em 4 rodadas), plano e task
  graph. Commit `1b09b92`.
