# Tasks: Afilify — núcleo SaaS

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`

**Formato**: `[ID] [P?] [História] Descrição` · `[P]` = paralelizável (arquivos distintos, sem
dependência entre si).

**Classificação**: P0 destrava tudo ou é a promessa central do brief · P1 é a entrega desta
rodada · P2 completa a experiência · P3 pode esperar sem prejudicar o uso.

**Testes**: obrigatórios. A Definition of Done do brief (§24) exige testes, e a suíte atual
(87 testes) é a rede de segurança da refatoração mais arriscada.

---

## Fase 1 — Fundação bloqueante (P0)

**Nada pode ser declarado pronto antes desta fase.**

- [x] T001 [P] Criar harness de execução: `TASKS.md`, `PROGRESS.md`, `DECISIONS.md`,
      `VALIDATION.md` na raiz da worktree, com estado verificável por arquivo
- [x] T002 [P] Estender `scripts/harness/` com gate de vocabulário sobre as telas novas e
      gate de "sem dado simulado" (procura por fixture/mock em caminho de produção)
- [x] T003 [P] Configurar ambiente de validação isolado (banco separado, `.env` próprio) e
      guarda que **recusa** subir apontando para o banco da operação (D35)
- [x] T004 Migração `db/0009_entidades.sql`: `usuario`, `conexao`, `grupo_conexao`,
      `tipo_nicho`, `projeto`, `automacao`, `fonte`, `execucao_fonte`, `destino`, `comando`,
      `limite_plano` (data-model.md)
- [ ] T005 Migração `db/0010_ofertas_publicacoes.sql`: nova identidade de oferta por projeto e
      tabela `publicacao` com chave de idempotência por ciclo (R9, R10)
- [x] T006 [P] `nucleo/cripto.py`: cifra/decifra AES-256-GCM com chave mestra de ambiente,
      mais o equivalente no painel com `node:crypto` (R4, FR-020)
- [x] T007 Semear `tipo_nicho` a partir de `nichos/perfumes.py` e `nichos/casa.py`, mantendo os
      arquivos como fonte de versão (FR-038a)

**Checkpoint**: banco de validação de pé, entidades criadas, credenciais cifráveis.

---

## Fase 2 — Contexto explícito no motor (P0, maior risco)

**Bloqueia US3, US4, US5, US6. Vem cedo para o risco ser pago cedo.**

- [ ] T008 `nucleo/contexto.py`: carregar workspace, projeto, automação, conexões, fonte,
      ritmo e mensagem a partir do banco, em um objeto explícito (R1)
- [ ] T009 Refatorar `nucleo/comum.py`: substituir constantes de módulo derivadas do perfil por
      parâmetros de contexto — **sem nenhuma mudança de regra de publicação** (R1)
- [ ] T010 Refatorar `mercadolivre/agente.py` e `mercadolivre/buscador.py` para receber contexto
      (`mercadolivre/clonador.py` permanece intocado)
- [ ] T011 `runner.py` passa a supervisionar por Automação ativa lida do banco, mantendo o
      isolamento por processo e a trava por automação
- [ ] T012 Rodar a suíte inteira e comparar comportamento antes/depois: mesma mensagem, mesmo
      ritmo, mesma seleção de fila. Divergência = a refatoração está errada

**Checkpoint**: o motor roda a operação atual lendo do banco, com comportamento idêntico.

---

## Fase 3 — US1: Conexão WhatsApp ponta a ponta (P0) 🎯

**Independente da Fase 2 — pode andar em paralelo desde o primeiro dia.**

**Teste independente**: criar conexão, escanear, publicar no grupo de teste, derrubar a sessão
pelo aparelho, reconectar — tudo pela interface, na instância `Pessoal`.

- [ ] T013 [US1] **Verificar o aviso de 1 hora**: criar instância descartável e observar se ela
      é mesmo apagada. O resultado decide se o provisionamento automático fica em pé (R5)
- [ ] T014 [P] [US1] `nucleo/conexoes/whatsapp.py`: criar instância, conectar (QR e pareamento),
      estado, desconectar, listar/criar grupos, enviar — sobre o contrato já validado
- [ ] T015 [US1] Tradutor de estados: quatro do provedor + estado local → onze estados de
      produto (FR-011, data-model.md)
- [ ] T016 [P] [US1] Rotas `POST /api/conexoes`, `/conectar`, `GET /estado` (api-painel.md)
- [ ] T017 [US1] Webhook `connection` como sinal primário; consulta de estado só enquanto o
      código está na tela (R5, FR-012)
- [ ] T018 [US1] Tela de conexão: QR em ≤10s, mudança de estado sem recarga, expiração com
      novo código sob demanda, número mascarado e perfil ao conectar
- [ ] T019 [US1] Sincronizar grupos com cache em `grupo_conexao` e "Última sincronização"
      (FR-015, FR-016)
- [ ] T020 [US1] Detecção de queda e reconexão, com aviso no Dashboard e nas automações
      afetadas (FR-014)
- [ ] T021 [US1] Renomear, desconectar e remover com recusa quando há automação ativa usando
      a conexão (FR-022)
- [ ] T022 [P] [US1] Testes: máquina de estados completa, expiração de código, queda,
      reconexão, remoção bloqueada
- [ ] T023 [US1] Validação real na instância `Pessoal`: percorrer os seis cenários de aceitação
      de US1 e registrar em `VALIDATION.md`

**Checkpoint**: um WhatsApp conecta, sobrevive a refresh e reconecta — sem sair da Afilify.

---

## Fase 4 — US3: Projetos e Automações (P0)

**Depende da Fase 2.**

**Teste independente**: criar projeto pela interface, ligar a automação, ver publicação sair.

- [ ] T024 [P] [US3] Rotas de projeto: criar, renomear, arquivar, duplicar (api-painel.md)
- [ ] T025 [P] [US3] Rotas de automação: criar, editar, ativar, pausar, excluir
- [ ] T026 [US3] Regra de ativação: recusa com pendências em linguagem comum; estado
      `impedida` quando falta conexão ou destino (FR-002, edge case da spec)
- [ ] T027 [US3] Seletor de projeto e automação no shell, sobre o contexto de projeto existente
- [ ] T028 [US3] Telas de criação com escolha do tipo de nicho (FR-038a, FR-039)
- [ ] T029 [P] [US3] Testes de isolamento entre projetos: ofertas, publicações, mensagens e
      ritmo de um nunca aparecem no outro (FR-003, SC-007)
- [ ] T030 [US3] Duplicação nasce pausada, sem histórico (US3 cenário 5)

**Checkpoint**: um projeto novo nasce e opera sem tocar em arquivo nem reiniciar nada.

---

## Fase 5 — US4: Fonte configurável e teste de busca (P0)

**Depende das Fases 2 e 4.**

**Teste independente**: configurar busca para um nicho diferente, testar, ativar e confirmar que
o coletado corresponde à amostra.

- [ ] T031 [US4] Fila de comandos: consumidor no motor (`nucleo/comandos.py`) e leitura de
      resultado no painel, com expiração e estado "o motor não está rodando" (R3)
- [ ] T032 [US4] `buscador.py` passa a receber os critérios da Fonte; paginação, pausas,
      categoria e tentativas continuam internos (R7, FR-031)
- [ ] T033 [P] [US4] Rotas de fonte, com rejeição de campo desconhecido em `criterios` —
      a proibição vale no contrato, não só na interface (FR-030)
- [ ] T034 [US4] Tela da Fonte: palavras-chave, onde buscar, desconto mínimo, faixa de preço,
      exclusões em Avançado recolhido (D28)
- [ ] T035 [US4] Comando `testar_busca` pelo mesmo caminho de código da coleta real, com
      limite de amostra (R8, FR-032, FR-033)
- [ ] T036 [US4] Resultado do teste: contagem, amostra com nome/preço/desconto, e explicação
      do que restringiu demais quando volta vazio (US4 cenário 3)
- [ ] T037 [US4] Sinais automáticos do anúncio como segunda barreira de qualidade (FR-038b)
- [ ] T038 [US4] `execucao_fonte`: registro de cada coleta com resultado legível, incluindo
      bloqueio da plataforma (FR-035, US4 cenário 5)
- [ ] T039 [US4] Deduplicação por identificador e título normalizado, dentro do projeto (FR-034)
- [ ] T040 [US4] Agenda de coleta em linguagem de intenção (FR-036) e limite de uso (FR-037)
- [ ] T041 [P] [US4] Testes: critérios respeitados, amostra igual à coleta, dedup, coleta vazia,
      bloqueio da origem

**Checkpoint**: um nicho novo é configurado, testado e ativado sem uma linha de código.

---

## Fase 6 — US5 e destinos múltiplos (P1)

- [ ] T042 [US5] `publicacao` substitui `entregas` no publicador, com identidade própria (R9)
- [ ] T043 [US5] Múltiplos destinos com intervalo entre eles (D30, FR-065)
- [ ] T044 [US5] Teto de segurança por conexão, com motivo visível quando segura envio
      (FR-046), apoiado por `wa_messages_limits` e `updateDelaySettings`
- [ ] T045 [US5] Estado `retida`: falha de conexão ou de link não descarta oferta; retoma
      sozinha (FR-042, SC-006)
- [ ] T046 [US5] Regra de repetição por queda de preço, com monitoramento isento (D31, FR-066/67)
- [ ] T047 [P] [US5] Telas de Ofertas e Publicações sob o modelo novo, com motivo legível e
      nova tentativa
- [ ] T048 [P] [US5] Testes: dois destinos geram duas publicações independentes; teto segura;
      oferta retida retoma; repetição só com queda; clone não é bloqueado
- [ ] T049 [US5] Aviso ao apontar dois destinos para o mesmo grupo (edge case da spec)

---

## Fase 7 — US6, US7 e conexões restantes (P1)

- [ ] T050 [US6] Ritmo & Regras sobre a automação: volume, janela, validade — sem dispersão,
      jitter, hora decimal ou proporção interna (FR-044)
- [ ] T051 [US6] Aviso de quando cada mudança entra em vigor (FR-045)
- [ ] T052 [US7] Dashboard: funcionando / o que aconteceu hoje / o que precisa de atenção, com
      indicador e lista usando o mesmo critério (FR-051, US7)
- [ ] T053 Conexão Mercado Livre: estado real da sessão, aviso antecipado de expiração e
      ofertas retidas — **sem construir fluxo de conexão** (D26, FR-063)
- [ ] T054 Validação da conexão do Mercado Livre gerando link de teste com a tag do workspace
      (FR-018) e garantia de atribuição correta (FR-002 da US2, SC recorrente)
- [ ] T055 [P] Autenticação real de usuário substituindo o cookie de usuário único (FR-050)

---

## Fase 8 — Mensagens, desempenho e área técnica (P2)

- [ ] T056 [P] Mensagens por automação, com preview usando oferta real do próprio projeto (FR-043)
- [ ] T057 [P] Desempenho por projeto, sem duplicar o Dashboard
- [ ] T058 [P] Área administrativa: registro técnico, identificadores, diagnóstico de conexão
      (FR-052)
- [ ] T059 [P] Eventos relevantes contextualizados na tela onde importam (FR-052)
- [ ] T060 Limites de plano aplicados e comunicados (FR-037, FR-046, `limite_plano`)

---

## Fase 9 — Fechamento (P1, contínuo)

- [ ] T061 Auditoria de vocabulário em todas as telas do fluxo comum (SC-003) — gate a cada tarefa
- [ ] T062 Estados de carregamento, vazio e erro em todas as telas (FR-054, SC-009)
- [ ] T063 QA de browser, console e network em todas as rotas, larguras reais incluídas
- [ ] T064 Regressão completa: suíte Python, lint, typegen, tsc, build
- [ ] T065 Validação com disparos reais no grupo de teste, registrada em `VALIDATION.md` (D33)
- [ ] T066 Documentação: README e docs de produto atualizados
- [ ] T067 Relatório final e checklist de revisão para o QA humano

---

## P3 — fora desta rodada (registrado para não se perder)

- Extensão de navegador do Mercado Livre (D26) — spec própria, próxima rodada
- Migração da operação de perfumes para o novo modelo (D34) — depois da validação e do merge
- Cadastro público, permissões, cobrança (D27)
- Novas plataformas (Amazon, Magalu, Shein, TikTok Shop, Telegram)
- Tracking com domínio próprio e página intermediária de cupom (brief §15)
- Bug das 48h do clonador e webhook — pertencem à workstream congelada

---

## Dependências

```
T001–T007 (fundação) ──→ tudo
T008–T012 (contexto)  ──→ T024–T041, T042–T051
T013                   ──→ T014 (decide se o provisionamento fica em pé)
T031 (fila comandos)   ──→ T035 (testar busca)
T014–T021 (WhatsApp)   ──→ T043 (destinos), T053
T042 (publicação)      ──→ T043, T044, T045, T046
```

**Paralelizável desde o dia 1**: Fase 3 (WhatsApp) com Fase 2 (contexto) — tocam arquivos
distintos e não compartilham dependência.

**Caminho crítico**: T004 → T008 → T009 → T012 → T024 → T031 → T035 → T041.

## Definition of Done por tarefa

Nenhuma tarefa fecha sem: comportamento verificado com dado real · testes passando · lint,
typecheck e build limpos · estados de carregamento, vazio e erro tratados · nenhum termo técnico
na tela do fluxo comum · `PROGRESS.md` e `VALIDATION.md` atualizados com evidência.
