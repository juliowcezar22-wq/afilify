# Implementation Plan: Afilify — núcleo SaaS

**Branch**: `feat/afilify-saas-redesign` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-afilify-saas-core/spec.md`

## Summary

Transformar a Afilify de ferramenta interna em plataforma: formalizar Workspace, Projeto,
Automação, Conexão, Fonte, Destino, Oferta e Publicação como dados; entregar a conexão de
WhatsApp ponta a ponta dentro do produto; e tornar a busca do Mercado Livre uma Fonte
configurável por intenção, com teste prévio honesto.

A abordagem técnica tem um eixo: **substituir a resolução de projeto no import por um contexto
explícito carregado do banco** (R1). Todo o resto — CRUD de projetos, automações múltiplas,
fontes configuráveis, destinos múltiplos — é consequência direta dessa refatoração. A
comunicação painel → motor passa a existir por uma fila de comandos no banco compartilhado (R3),
único mecanismo que funciona com os dois em máquinas diferentes.

A operação viva não é migrada nesta rodada (D34): tudo é construído e validado na worktree, com
publicações reais em grupo de teste, e o corte vem depois da validação manual do dono.

## Technical Context

**Language/Version**: Python 3.9 (motor) · TypeScript / Next.js 16 (painel)

**Primary Dependencies**: motor em stdlib + `psycopg[binary]` (Postgres) + `cryptography`
(nova — cifra de credenciais, R4). Painel: Next.js, `postgres.js`, `better-sqlite3`, Tailwind 4.
Nenhuma biblioteca de UI externa (decisão herdada do redesign).

**Storage**: Postgres para o modelo novo, pela camada `nucleo/storage.py` (mesmo SQL nos dois
dialetos) e `painel/lib/dados.ts`. Migrações a partir de `db/0009_`.

**Testing**: `unittest` (87 testes existentes, banco temporário obrigatório) · `pnpm lint`,
`next typegen && tsc --noEmit`, `pnpm build` · QA de browser/console/network via
`scripts/harness/` herdado · auditoria automatizada de vocabulário (`check-linguagem.sh`).

**Target Platform**: produção roda em VPS desde 22/08/2026 (EasyPanel), com três serviços
separados — `worker` (motor), `painel` (Next.js) e `db` (Postgres 16). Worker e painel só se
falam pelo banco. O Mac é backup aposentado. Isso confirma R2 (Postgres) e torna R3 (fila de
comandos no banco) não apenas conveniente, mas o único canal existente entre os dois serviços.

**Project Type**: aplicação web com motor de automação em processo separado.

**Performance Goals**: teste de busca com amostra em ≤30s (SC-005) · QR na tela em ≤10s
(US1) · estado de conexão refletido na tela sem recarga (FR-012).

**Constraints**: o motor resolve projeto no import e precisa ser refatorado sem alterar
comportamento de publicação (R1) · Clonador congelado · nenhuma credencial em claro · nenhuma
tela com dado simulado · banco de validação sempre separado do de produção.

**Scale/Scope**: 1 workspace nesta rodada, modelo pronto para muitos · ~10 telas · ~130
publicações/dia por automação no volume atual.

## Constitution Check

*GATE: avaliado antes da Fase 0 e reavaliado após a Fase 1.*

| Princípio | Como o plano atende | Situação |
|---|---|---|
| I — Intenção, nunca infraestrutura | Fonte limitada a 4 controles + exclusões (FR-030, validado no contrato de API, não só na UI); intervalo entre destinos e teto de segurança são decisões da plataforma; identificadores técnicos isolados em objeto `tecnico` | ✅ |
| II — Domínio formalizado | `data-model.md` cria as 8 entidades; `config` dissolvida nas entidades certas | ✅ |
| III — Nada simulado | Teste de busca usa o mesmo caminho de código da coleta real (R8); estados de conexão vêm do provedor; comando expirado diz "o motor não está rodando" em vez de esperar | ✅ |
| IV — Execução verificável | Harness com TASKS/PROGRESS/DECISIONS e gates de build, lint, typecheck, testes e vocabulário | ✅ |
| V — Isolamento e operação viva | Sem migração da produção (D34); banco de validação separado (D35); Clonador intocado; sem merge/push/deploy | ✅ |

**Resultado**: passa sem violações. Nenhuma entrada em Complexity Tracking.

Reavaliação pós-Fase 1: o modelo de dados não introduziu nenhuma entidade além das que a spec
exige, e o contrato de API rejeita campo técnico na configuração de Fonte — reforçando o
princípio I no lugar onde ele costuma vazar.

## Project Structure

### Documentation (this feature)

```text
specs/001-afilify-saas-core/
├── spec.md              # especificação (Clarify concluído)
├── audit.md             # auditoria do estado atual
├── decisions.md         # D24–D35
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── api-painel.md                  # Fase 1
│   └── whatsapp-provider-openapi.yaml # contrato real do provedor
├── checklists/requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
nucleo/
├── comum.py            refatorado: constantes de módulo → Contexto explícito (R1)
├── contexto.py         NOVO — carrega workspace/projeto/automação/conexões do banco
├── conexoes/           NOVO — clientes de plataforma
│   ├── whatsapp.py       instância, QR, estado, grupos, envio, webhook
│   └── mercadolivre.py   sessão, validação, geração de link
├── cripto.py           NOVO — cifra/decifra credenciais (AES-256-GCM)
├── comandos.py         NOVO — consumidor da fila painel → motor (R3)
├── storage.py          inalterado (já abstrai os dois bancos)
└── nicho.py            passa a ler tipo_nicho do banco, com os arquivos como semente

mercadolivre/
├── buscador.py         busca passa a receber critérios da Fonte; internos continuam internos
├── agente.py           publicador: múltiplos destinos, intervalo, teto de segurança
└── clonador.py         INTOCADO (congelado)

runner.py               supervisiona por Automação ativa, lida do banco

db/                     0009+ (entidades novas, migração de ofertas/entregas)

painel/
├── app/(app)/          telas sob o vocabulário novo (base do redesign anterior)
├── app/api/            rotas do contrato api-painel.md
└── lib/                acesso a dados, sessão real de usuário, cifra

scripts/harness/        gates de verificação + estado persistente
```

**Structure Decision**: mantém a divisão existente motor/painel com banco compartilhado. As
adições são módulos novos em `nucleo/` (contexto, conexões, cripto, comandos) — nenhuma
reorganização de diretórios, para que a suíte de testes atual continue valendo como rede de
segurança durante a refatoração mais arriscada (R1).

## Sequenciamento e caminho crítico

```
[1] Contexto explícito no motor (R1)  ──┬─→ [3] Projetos e Automações (CRUD)
    ▲ rede: 87 testes atuais            ├─→ [4] Fontes configuráveis ─→ [5] Testar busca
[2] Migrações + entidades ──────────────┘                                    ▲
                                                                    [6] Fila de comandos (R3)
[7] Conexão WhatsApp ponta a ponta ─→ [8] Destinos múltiplos + teto de segurança
[9] Publicações e Ofertas sob o modelo novo
[10] Auditoria de vocabulário e estados vazios/erro/carregamento
```

**Caminho crítico**: [1] → [2] → [3] → [4] → [5]. A tarefa [1] bloqueia quase tudo e é a de
maior risco: é refatoração ampla em código que publica em produção. Ela vem primeiro,
justamente para que o risco seja pago cedo, com a suíte inteira como rede.

**Paralelizável**: [7] (WhatsApp) não depende de [1] e pode andar junto — toca módulos novos e
o painel. É o P0 do brief, então começa em paralelo desde o primeiro dia.

**Fora do caminho crítico**: [10] é contínuo, verificado por gate a cada tarefa, não uma fase final.

## Riscos

| Risco | Impacto | Tratamento |
|---|---|---|
| Refatoração do contexto altera comportamento de publicação | Alto — é o motor que sustenta a operação | Suíte de 87 testes como rede; nenhuma mudança de regra junto da refatoração; validação com disparos reais em grupo de teste |
| Instância criada por API expira em 1 hora (aviso no contrato) | Médio — derruba o provisionamento automático | Verificar com instância descartável **antes** de construir em cima; D25b já suporta instância existente |
| Parsing da busca do Mercado Livre é frágil por natureza | Médio — a plataforma muda o HTML sem aviso | Falha vira estado visível (`execucao_fonte.resultado='falhou'` com motivo), nunca silêncio; extração continua coberta por teste golden |
| Sessão do Mercado Livre expira durante a validação | Médio | Ofertas ficam `retida` e retomam sozinhas (FR-042); renovação continua manual nesta rodada (D26) |
| Escopo grande com autonomia alta | Médio | Harness com estado persistente e gates verificáveis impede declarar pronto cedo demais |
