# Afilify — Arquitetura de Produto (redesign SaaS)

> Documento de referência do redesign (branch `feat/afilify-saas-redesign`).
> Descreve o modelo mental do produto, como ele mapeia para a implementação
> real existente, e a regra de tradução entre linguagem interna e linguagem
> de produto.

## 1. Modelo mental

```
CONTA / WORKSPACE
 ├── usuários (hoje: 1, cookie HMAC; futuro: Auth.js multiusuário)
 ├── assinatura (futuro)
 ├── CONEXÕES (contas conectadas: WhatsApp, Mercado Livre, Shopee, …)
 └── configurações globais (tracking de cliques, preferências)

PROJETO  (implementação atual: "perfil" — perfumes-ml, casa-ml-shopee)
 ├── AUTOMAÇÃO (implícita hoje: 1 automação por projeto, o daemon do perfil)
 │    ├── FONTES      de onde surgem ofertas (busca automática, monitoramento)
 │    ├── DESTINOS    para onde publica (grupo WhatsApp escolhido)
 │    ├── MENSAGENS   formato da publicação (template + headlines)
 │    └── RITMO/REGRAS cota diária, janela, validade, prioridades
 ├── OFERTAS       oportunidades encontradas (tabela `ofertas`)
 ├── PUBLICAÇÕES   execuções de uma oferta num destino (tabela `entregas`
 │                 + status_envio da oferta)
 └── DESEMPENHO    métricas operacionais por período
```

Distinções importantes:

- **Oferta ≠ Publicação.** Oferta é o produto encontrado; publicação é a
  execução (envio) dela num destino. Hoje o modelo físico aproxima os dois
  (`ofertas.status_envio` + `entregas`), mas a UI trata como conceitos
  distintos: catálogo (Ofertas) vs linha do tempo (Publicações).
- **Conexão ≠ Destino.** A conexão WhatsApp fornece a lista de grupos; o
  projeto escolhe alguns grupos como destinos. A conta Mercado Livre é uma
  conexão; ela não é um destino.
- **Fonte** é de onde a oportunidade surge: busca automática no marketplace
  (`origem='busca'`) ou monitoramento de grupos concorrentes
  (`origem='clone'`, interno). Na UI: "Busca automática" e "Monitoramento".

## 2. Implementação real (mapeamento)

| Conceito de produto | Implementação atual |
|---|---|
| Workspace | tabela `workspaces` (semeada, ainda sem uso real) |
| Projeto | `perfil` (slug: `perfumes-ml`, `casa-ml-shopee`) — arquivo em `perfis/` + linhas em `config` |
| Automação | daemon do perfil (runner.py → agente.py). 1:1 com projeto hoje |
| Oferta | linha em `ofertas` (PK `mlb_id`) |
| Publicação | `ofertas.status_envio` (`PENDENTE`/`ENVIADO`/`ERRO`) + tabela `entregas` (idempotência por `(mlb_id, canal)`) |
| Destino | JID de grupo WhatsApp em `config[perfil].canal.grupo` |
| Fonte: busca | buscador ML/Shopee (`origem='busca'`, `busca_horas`) |
| Fonte: monitoramento | clonador (`config[perfil].clonador`, `origem='clone'`) |
| Conexão WhatsApp | instância Uazapi (`UAZAPI_URL`/`UAZAPI_TOKEN`) |
| Conexão Mercado Livre | cookie de sessão (`ML_COOKIE_PATH`, ~30 dias) |
| Conexão Shopee | Open API oficial (`SHOPEE_APP_ID`/`SHOPEE_SECRET`) |
| Formato da mensagem | `config[perfil].mensagem` (`base`, `linha_loja_oficial`, `rodape`) + `config[perfil].headlines` (pools) |
| Ritmo/Regras | `config[perfil].ritmo` (cota, janelas em hora decimal, coletas, validade, proporção) |
| Estado vivo | tabela `estado`: `{perfil}:heartbeat`, `{perfil}:plano_do_dia`, `{perfil}:proximo_envio` |
| Tracking de cliques | `config[perfil].tracking` + tabela `cliques` + rota `/r/[codigo]` |
| Logs | tabela `logs` (espelho) ou arquivo `LOG_PATH` |

### Contratos que o painel usa (NÃO alterar sem registro em DECISIONS)

- `POST /api/config` — grava `(perfil, chave, valor)` com validação por chave.
  O motor lê a cada uso, sem restart. Chaves: `mensagem`, `headlines`,
  `ritmo`, `clonador`, `canal`, `tracking`.
- `POST /api/ofertas/[id]` — `{acao: "ignorar" | "reenfileirar"}`.
- `GET {UAZAPI_URL}/group/list` (header `token`) — lista de grupos da conta.
- `GET {UAZAPI_URL}/instance/status` — status da conexão WhatsApp.
- Semânticas do motor preservadas: cota/janela valem no plano de amanhã;
  demais chaves valem na próxima mensagem; `origem='clone'` tem prioridade
  na fila; retries com `proxima_tentativa`.

## 3. Regra de abstração (linguagem)

O usuário comum nunca vê: worker, Redis, filas internas, Postgres, jobs,
webhooks, tokens, Uazapi, EasyPanel, deploy, restart, polling, scraper,
LOG_PATH, variáveis de ambiente, `.env`, JID, IDs técnicos (MLB…), slugs
(`perfumes-ml`), hora decimal, "clone fura a fila".

Tradução padrão:

| Interno | Produto |
|---|---|
| `perfumes-ml` | "Perfumes" (nome amigável do projeto) |
| `Worker perfumes-ml online` | "Automação funcionando normalmente" |
| `JID 1203…@g.us` | nome do grupo ("ACHEI BARATO \| PERFUMES"); JID só em "Detalhes técnicos" |
| `status_envio=PENDENTE` | "Aguardando" |
| `status_envio=ENVIADO` | "Publicada" |
| `status_envio=ERRO` | "Precisa de atenção" (com motivo legível) |
| `origem=busca` | "Busca automática" |
| `origem=clone` | "Monitoramento" |
| hora decimal `8.75` | `08:45` |
| `uazapi` | "WhatsApp" |
| cookie `.mlcookie` | "Sessão do Mercado Livre" (renovação guiada em Detalhes) |

Identificadores técnicos continuam existindo no banco e podem aparecer sob
"Detalhes técnicos" (colapsado), nunca como informação primária.

## 4. Navegação (implementada no redesign)

```
GERAL      Dashboard (/)
OPERAÇÃO   Ofertas (/ofertas) · Publicações (/publicacoes) · Desempenho (/desempenho)
AUTOMAÇÃO  Fontes (/fontes) · Destinos (/destinos) · Mensagens (/mensagens) · Ritmo & Regras (/ritmo)
CONEXÕES   Conexões (/conexoes)
CONTA      Configurações (/configuracoes) · Ajuda (/ajuda)
```

- Contexto de projeto: seletor "Projeto: <nome> ▾" no shell, persistido em
  cookie (`afilify_projeto`). Escala de 1 a N projetos.
- Rotas antigas (`/fila`, `/canais`, `/copiador`, `/templates`, `/analytics`,
  `/config`) redirecionam para as novas (ver AFILIFY_MIGRATION_MAP.md).
- `/logs` sai da navegação comum (fica acessível por URL para operação/admin).

## 5. Fora de escopo deste redesign

- Multiusuário real, assinatura, permissões (arquitetura preparada, não implementada).
- Alterações de comportamento do motor (busca, publicação, prioridade, retry).
- Novas integrações de marketplace (apenas apresentadas como "em breve", sem botão funcional).
- Analytics de receita/conversão (dados não existem no backend).
