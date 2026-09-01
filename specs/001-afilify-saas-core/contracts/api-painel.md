# Contrato — API do painel

Todas as rotas exigem sessão autenticada e resolvem `workspace_id` a partir dela. **Nenhuma
resposta jamais devolve credencial**, nem cifrada, nem mascarada. Erros trazem `mensagem` em
linguagem de produto; detalhe técnico vai só para o registro administrativo.

Formato de erro:

```json
{ "erro": { "codigo": "conexao_expirada", "mensagem": "Sua conexão com o Mercado Livre expirou. Reconecte sua conta para continuar gerando ofertas." } }
```

---

## Conexões

### `GET /api/conexoes`
Lista as conexões do workspace com estado de produto, número mascarado, nome do perfil,
quantidade de grupos sincronizados e última atividade.

### `POST /api/conexoes`
Cria uma conexão. Corpo: `{ plataforma, nome, instancia_existente? }`.
Para WhatsApp: provisiona instância nova (`POST /instance/create`) ou adota uma existente (D25b).
Devolve a conexão em estado `criando`.

### `POST /api/conexoes/:id/conectar`
Inicia o pareamento. Corpo opcional `{ telefone }` — com telefone, código de pareamento; sem,
QR Code. Devolve `{ estado, codigo, expira_em }` com o código já em formato exibível.

### `GET /api/conexoes/:id/estado`
Estado atual para a tela que aguarda o pareamento (FR-012). Devolve `{ estado, codigo?,
expira_em?, perfil?, numero_mascarado? }`. Consultada em intervalo curto **apenas enquanto o
código está na tela**; fora disso o estado chega por webhook.

### `POST /api/conexoes/:id/sincronizar-grupos`
Atualiza o cache de grupos. Devolve contagem e horário da sincronização.

### `POST /api/conexoes/:id/desconectar` · `POST /api/conexoes/:id/reconectar`

### `PATCH /api/conexoes/:id` — renomear.

### `DELETE /api/conexoes/:id`
Recusa com `409` e a lista de automações afetadas quando a conexão está em uso por automação
ativa (FR-022). Corpo `{ confirmar: true }` prossegue, pausando as automações e dizendo quais.

### `POST /api/webhook/whatsapp/:chave`
Recebe eventos do provedor. Trata `connection` (mudança de estado) e `history`/`messages`
(monitoramento — encaminhado para a tabela existente, sem alterar o Clonador). Autenticada por
chave secreta na URL, como a rota atual.

---

## Projetos e automações

### `GET/POST /api/projetos` · `PATCH/DELETE /api/projetos/:id`
Criação exige `{ nome, tipo_nicho_id }`. `DELETE` arquiva — não apaga histórico.

### `POST /api/projetos/:id/duplicar`
Cria cópia pausada, sem ofertas nem publicações (FR-002, US3 cenário 5).

### `GET/POST /api/automacoes` · `PATCH/DELETE /api/automacoes/:id`

### `POST /api/automacoes/:id/ativar`
Valida os pré-requisitos. Quando falta algo, responde `409` com a lista do que falta em
linguagem comum e **não** ativa parcialmente:

```json
{ "erro": { "codigo": "automacao_incompleta", "mensagem": "Falta escolher para onde publicar.",
            "pendencias": ["destino"] } }
```

### `POST /api/automacoes/:id/pausar`
Nenhuma publicação nova sai; a fila é preservada.

---

## Fontes

### `GET/POST /api/fontes` · `PATCH/DELETE /api/fontes/:id`
`criterios` aceita **somente** o conjunto de FR-030. Campo desconhecido é rejeitado com `400` —
a proibição de expor parâmetro técnico é validada no contrato, não só na interface.

### `POST /api/fontes/:id/testar`
Enfileira um comando `testar_busca` (R3) e devolve `{ comando_id }`.

### `GET /api/comandos/:id`
Estado e resultado de um comando assíncrono. Para `testar_busca`:

```json
{ "estado": "concluido",
  "resultado": { "compativeis": 27,
                 "amostra": [ { "nome": "…", "preco": 164.80, "desconto_pct": 34, "imagem": "…" } ] } }
```

Estados possíveis e o que a interface mostra:

| estado | interface |
|---|---|
| `pendente` / `executando` | "Procurando ofertas…" com progresso real |
| `concluido` | contagem e amostra |
| `falhou` | motivo legível — inclui bloqueio da plataforma de origem |
| `expirado` | "A automação não está rodando agora" — nunca espera infinita |

---

## Destinos

### `GET/POST /api/destinos` · `PATCH/DELETE /api/destinos/:id`
Aceita alvo por identificador mesmo sem nome resolvível (D16). Ao adicionar um destino já usado
por outra automação do mesmo workspace, responde `200` com `aviso` sobre dobrar o volume naquele
grupo (edge case da spec) — não bloqueia.

---

## Ofertas e publicações

### `GET /api/ofertas`
Filtros: texto, estado, origem, período. Sempre no escopo do projeto ativo.

### `PATCH /api/ofertas/:id` — ignorar / devolver à fila.

### `POST /api/ofertas/:id/publicar` — enfileira `publicar_agora`.

### `GET /api/publicacoes`
Fila do dia, histórico e falhas, com motivo legível.

### `POST /api/publicacoes/:id/repetir` — nova tentativa.

---

## Regras que valem para todo o contrato

1. Nenhum identificador técnico em resposta destinada ao fluxo comum; eles vivem num objeto
   `tecnico` separado, consumido só pela área avançada.
2. Toda rota de escrita valida o pertencimento ao workspace antes de qualquer efeito.
3. Ações que dependem do motor são assíncronas e sempre têm caminho para "o motor não está
   rodando" — a interface nunca fica esperando para sempre.
4. Limite de plano excedido responde `429` com a mensagem do limite e o que fazer.
