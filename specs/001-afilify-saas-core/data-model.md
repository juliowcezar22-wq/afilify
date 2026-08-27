# Fase 1 — Modelo de dados

Deriva de `spec.md` (Key Entities) e das decisões D24–D35. Dialeto compatível com
`nucleo/storage.py` (mesmo SQL em SQLite e Postgres): datas como TEXT ISO-8601, `?` como
placeholder, UPSERT via `ON CONFLICT … excluded`.

Numeração das migrações continua a série existente, a partir de `db/0009_`.

---

## Visão geral

```
workspace ──┬── usuario
            ├── conexao ────────────────┐
            ├── plano/limites           │
            └── projeto ── automacao ──┤── fonte
                    │           │      └── destino ──→ conexao
                    │           └── ritmo, mensagem
                    ├── oferta ──→ publicacao ──→ destino
                    └── tipo_nicho (modelo de curadoria)
```

Regra de ouro do isolamento: **toda tabela operacional carrega `workspace_id` e, quando
aplicável, `projeto_id`**. Nenhuma consulta do painel ou do motor lê sem filtrar por eles.

---

## Entidades

### workspace *(já existe — `db/0001_init.sql`)*
A conta. Nesta rodada há apenas um (D27), mas todas as chaves já apontam para ele.

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| nome | TEXT | |
| criado_em | TEXT ISO | |

### usuario *(novo)*
Substitui o cookie HMAC de usuário único (`painel/lib/sessao.ts`).

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id | TEXT FK | |
| email | TEXT único | |
| senha_hash | TEXT | derivação lenta com sal |
| nome | TEXT | |
| criado_em, ultimo_acesso | TEXT ISO | |

### conexao *(novo)*
Conta externa que a Afilify opera. Pertence ao workspace, nunca ao projeto (D24, FR-021).

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id | TEXT FK | |
| plataforma | TEXT | `whatsapp` · `mercadolivre` · `shopee` |
| nome | TEXT | nome dado pelo usuário ("Promoções Principal") |
| estado | TEXT | ver máquina de estados abaixo |
| identificador_externo | TEXT | id da instância / conta — área técnica apenas |
| credencial_cifrada | BLOB/TEXT | AES-256-GCM (R4). Nunca sai do servidor |
| metadados | TEXT JSON | número mascarado, nome do perfil, tag de afiliado |
| ultimo_estado_em | TEXT ISO | |
| ultima_atividade_em | TEXT ISO | |
| expira_em | TEXT ISO | sessões com validade conhecida (Mercado Livre) |
| motivo_ultima_queda | TEXT | do provedor, higienizado antes de exibir |
| criado_em, atualizado_em | TEXT ISO | |

**Máquina de estados** (FR-011) — estados de produto, derivados do estado do provedor mais o
estado local:

```
criando → gerando_codigo → codigo_disponivel → aguardando_leitura ─┬→ conectando → conectado
                                                                   └→ codigo_expirado → (novo código)
conectado ─┬→ desconectado        (ação do usuário)
           ├→ sessao_perdida      (queda detectada)   → reconectando → conectado
           └→ precisa_reconectar  (expiração prevista)
qualquer  → erro (com motivo legível)
```

Mapeamento do provedor de WhatsApp: `disconnected`→desconectado · `connecting`→conectando ·
`connected`→conectado · `hibernated`→precisa_reconectar.

### grupo_conexao *(novo)*
Cache dos grupos de uma conexão de WhatsApp, para exibir por nome sem chamar a API a cada render
(limitação registrada na auditoria e em D16 do redesign anterior).

| campo | tipo | notas |
|---|---|---|
| conexao_id | TEXT FK | PK composta com `identificador` |
| identificador | TEXT | id do grupo — área técnica apenas |
| nome | TEXT | pode vir vazio; a UI mostra máscara e permite selecionar mesmo assim |
| participantes | INTEGER | |
| sincronizado_em | TEXT ISO | alimenta "Última sincronização" |

### tipo_nicho *(novo — versionado no produto, não editável pelo usuário)*
Materializa `nichos/*.py` como dado selecionável (D29, FR-038a).

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | `perfumes`, `casa`, … |
| nome | TEXT | "Perfumes" |
| versao | INTEGER | permite evoluir a curadoria sem quebrar projetos existentes |
| curadoria | TEXT JSON | marcas aceitas, palavras proibidas, unidade mínima, contratipo |

### projeto *(novo — sucede `perfis/*.py`)*

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id | TEXT FK | |
| nome | TEXT | nome do usuário: "Perfumes". Nunca um slug |
| tipo_nicho_id | TEXT FK | curadoria aplicada (D29) |
| estado | TEXT | `ativo` · `pausado` · `arquivado` |
| criado_em, atualizado_em | TEXT ISO | |

Únicos por (workspace_id, nome). Exclusão é **arquivamento**: o histórico de publicações
sobrevive (FR-007).

### automacao *(novo — a entidade que o brief pede formalizar)*

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id, projeto_id | TEXT FK | |
| nome | TEXT | "Ofertas Mercado Livre" |
| estado | TEXT | `rascunho` · `ativa` · `pausada` · `impedida` |
| motivo_impedida | TEXT | o que falta, em linguagem comum (FR-002 cenário 2) |
| ritmo | TEXT JSON | publicações/dia, janela, validade — o que é do usuário (FR-044) |
| mensagem | TEXT JSON | template, rodapé, biblioteca de chamadas |
| criado_em, atualizado_em | TEXT ISO | |

`impedida` é estado próprio: uma automação sem destino, sem conexão válida ou com conexão caída
**não** aparece como ativa (edge case da spec).

### fonte *(novo)*

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id, automacao_id | TEXT FK | |
| tipo | TEXT | `busca` · `monitoramento` |
| conexao_id | TEXT FK nulo | monitoramento exige conexão de WhatsApp |
| ativa | INTEGER | |
| criterios | TEXT JSON | **exatamente** o de FR-030 (ver abaixo) |
| agenda | TEXT JSON | quando coletar, em linguagem de intenção (FR-036) |
| ultima_execucao_em | TEXT ISO | |
| criado_em, atualizado_em | TEXT ISO | |

`criterios` para `tipo='busca'`:

```json
{
  "palavras_chave": ["perfume masculino", "perfume árabe"],
  "onde": { "busca": true, "pagina_ofertas": true },
  "desconto_minimo": 30,
  "preco": { "min": 50, "max": 500 },
  "excluir": { "palavras": [], "marcas": [] }
}
```

Nada além disso é aceito no fluxo comum. Paginação, pausas, categoria, cabeçalhos e tentativas
**não** têm campo aqui — são internos (R7).

### execucao_fonte *(novo)*
Histórico de coletas (FR-035), base do "rodou mesmo sem novidades".

| campo | tipo | notas |
|---|---|---|
| id | BIGSERIAL PK | |
| fonte_id | TEXT FK | |
| iniciada_em, terminada_em | TEXT ISO | |
| resultado | TEXT | `ok` · `sem_novidades` · `falhou` |
| encontradas, novas | INTEGER | |
| motivo | TEXT | legível; bloqueio anti-robô cai aqui |

### destino *(novo — sucede `config.canal`)*

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id, automacao_id | TEXT FK | |
| conexao_id | TEXT FK | de qual conta sai a publicação (FR-021) |
| alvo | TEXT | id do grupo — área técnica apenas |
| nome | TEXT | nome legível, do cache de grupos |
| ordem | INTEGER | ordem de envio entre destinos (D30) |
| ativo | INTEGER | |

### oferta *(evolução da tabela atual)*

Mudança estrutural: sai a chave primária global `mlb_id`, entra identidade por projeto (R10).

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id, projeto_id | TEXT FK | |
| identificador_anuncio | TEXT | único junto de `projeto_id` |
| nome, url, imagem, marca, familia, titulo_norm | TEXT | como hoje |
| preco_original, preco_promocional, desconto_pct | numérico | |
| loja, loja_oficial, vendedor, avaliacao, vendidos | | alimentam os sinais automáticos (R7) |
| link_afiliado | TEXT | |
| origem | TEXT | `busca` · `monitoramento` |
| fonte_id | TEXT FK nulo | qual fonte encontrou |
| estado | TEXT | `nova` · `pronta` · `retida` · `publicada` · `ignorada` · `expirada` |
| motivo_retencao | TEXT | ex.: conexão do Mercado Livre expirada (FR-019, FR-042) |
| validade_ate | TEXT ISO | derivada do ritmo da automação |
| criado_em, atualizado_em | TEXT ISO | |

`retida` é o estado que garante FR-042/SC-006: falha de conexão ou de link **não** descarta a
oferta; ela espera e volta sozinha.

### publicacao *(substitui `entregas`)*

| campo | tipo | notas |
|---|---|---|
| id | BIGSERIAL PK | identidade própria (R9) |
| workspace_id, projeto_id, automacao_id | TEXT FK | |
| oferta_id, destino_id | TEXT FK | |
| estado | TEXT | `agendada` · `enviando` · `enviada` · `falhou` · `cancelada` |
| tentativa | INTEGER | |
| chave_idempotencia | TEXT único | (oferta, destino, ciclo) — preserva a proteção que a chave antiga dava |
| preco_publicado | numérico | base da regra de repetição (D31) |
| mensagem_enviada | TEXT | o que de fato saiu |
| id_externo | TEXT | id da mensagem no provedor |
| motivo_falha | TEXT | legível, higienizado |
| agendada_para, enviada_em | TEXT ISO | |

`ciclo` na chave de idempotência incrementa quando a oferta volta à fila por queda de preço
(D31) — é o que permite republicar sem abrir brecha para envio duplicado.

### comando *(novo — canal painel → motor, R3)*

| campo | tipo | notas |
|---|---|---|
| id | TEXT PK | |
| workspace_id | TEXT FK | |
| tipo | TEXT | `testar_busca` · `conectar_whatsapp` · `sincronizar_grupos` · `publicar_agora` · `validar_conexao_ml` |
| parametros | TEXT JSON | |
| estado | TEXT | `pendente` · `executando` · `concluido` · `falhou` · `expirado` |
| resultado | TEXT JSON | amostra do teste, QR, lista de grupos… |
| erro | TEXT | legível |
| expira_em | TEXT ISO | comando velho não é executado |
| criado_em, atualizado_em | TEXT ISO | |

### limite_plano *(novo)*
Existe desde já para não exigir migração quando houver clientes (D27).

| campo | tipo | notas |
|---|---|---|
| workspace_id | TEXT PK | |
| max_conexoes, max_projetos, max_automacoes | INTEGER | |
| max_publicacoes_dia | INTEGER | |
| max_testes_busca_dia | INTEGER | FR-037 |
| teto_envios_conexao_hora | INTEGER | FR-046 — teto de segurança, não exibido como configuração |

---

## O que acontece com as tabelas atuais

| hoje | destino |
|---|---|
| `ofertas` | migra para o novo formato; `perfil` (TEXT) vira `projeto_id` |
| `entregas` | vira `publicacao`, com identidade própria |
| `config` (perfil, chave, valor) | dissolvida: `ritmo` e `mensagem` vão para `automacao`; `canal` vira `destino`; `clonador` vira `fonte` do tipo monitoramento; `tracking` sobe para o workspace |
| `estado` | permanece (plano do dia, batida de vida), com chave por automação |
| `logs` | permanece — área administrativa (FR-052) |
| `cliques` | permanece, ligado à oferta |
| `rival_mensagens` | permanece intocada — Clonador congelado |

**Nenhuma dessas mudanças é aplicada à operação viva nesta rodada** (D34). As migrações são
escritas e exercitadas no banco de validação; o corte da produção é trabalho posterior.

---

## Regras de integridade que o modelo precisa garantir

1. Toda leitura operacional filtra por `workspace_id` e, quando aplicável, `projeto_id` (FR-003, FR-004).
2. Automação só entra em `ativa` com ao menos um destino ativo e todas as conexões exigidas conectadas.
3. Conexão em uso por automação ativa não é removida sem confirmação explícita (FR-022).
4. Oferta é única por (projeto, identificador do anúncio); deduplicação secundária por título normalizado.
5. Publicação é única por (oferta, destino, ciclo).
6. Credencial nunca é lida fora do servidor, nem devolvida por nenhuma resposta de API (FR-020).
7. Projeto arquivado preserva ofertas e publicações; nada é apagado em cascata.
