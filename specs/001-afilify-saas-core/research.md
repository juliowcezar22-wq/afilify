# Fase 0 — Pesquisa e decisões técnicas

Base: `spec.md` + `audit.md` + `decisions.md` (D24–D35) + contrato real do provedor de
WhatsApp em `contracts/whatsapp-provider-openapi.yaml`.

---

## R1 — O motor resolve o projeto no import: é o risco central

**Achado**: `nucleo/comum.py` monta constantes de módulo a partir do perfil ativo no momento
do import (`PERFIL = perfil.ativo()`, `UAZAPI_GRUPO`, `ENVIOS_POR_DIA`, `PERFIL_ATIVO`…).
`runner.py` documenta explicitamente por que existe: *"os módulos do motor resolvem o perfil no
import… trocar isso em runtime exigiria reescrever assinaturas de dezenas de funções"*. Por isso
hoje cada projeto é um **processo separado**.

**Decisão**: introduzir um objeto de contexto explícito (`Contexto`: workspace, projeto,
automação, conexões, fonte, ritmo) carregado do banco e **passado como parâmetro** para as
funções do motor, substituindo as constantes de módulo. O supervisor continua subindo um
processo por Automação ativa — o isolamento por processo é uma qualidade, não um defeito, e
mantém a falha de uma automação contida.

**Racional**: sem isso, "criar projeto pela interface" é impossível — todo projeto novo exigiria
um arquivo e um restart. É a fundação de FR-001 e FR-002.

**Alternativas rejeitadas**:
- Manter constantes globais e gerar arquivos de perfil a partir do banco: mantém restart no
  caminho crítico e cria duas fontes de verdade.
- Reescrever o motor do zero: joga fora a lógica calibrada (ritmo lognormal, filtros de nicho,
  extração) que é o ativo real do produto.

**Mitigação do risco**: a refatoração é mecânica mas ampla. Será feita em uma tarefa dedicada,
com a suíte atual (87 testes) como rede — nenhum comportamento de publicação pode mudar.

---

## R2 — Onde o modelo novo vive

**Decisão**: Postgres como banco do modelo novo, usando a camada `nucleo/storage.py` que já
existe (mesmo SQL nos dois dialetos) e `painel/lib/dados.ts` no painel. Nenhum ORM novo no motor.

**Racional**: as migrações `db/0001..0008` já preparam o Postgres e o cutover foi desenhado. As
entidades novas (workspace, projeto, automação, conexão, fonte, destino) exigem chaves
estrangeiras e unicidade composta — território natural de um banco relacional real.

**Consequência para a validação (D35)**: a worktree usa um banco próprio, nunca o
`afilify-db` da VPS. `DATABASE_URL` do ambiente de validação aponta para uma base separada,
semeada com cópia (`pg_dump`) dos dados reais quando a fidelidade importar.

---

## R3 — Como o painel dispara ações no motor

**Problema**: "Testar busca", "conectar WhatsApp", "sincronizar grupos" e "publicar agora" são
ações do usuário que exigem trabalho do motor. Hoje painel e motor só se comunicam por leitura
da tabela `config` — não há request/response. Em produção (VPS/EasyPanel desde 22/08/2026) painel e motor são **contêineres separados**
(`painel` e `worker`) que compartilham apenas o serviço `db` (Postgres 16).

**Decisão**: tabela de **comandos** no banco (fila de trabalho): o painel insere um comando com
parâmetros e fica lendo o resultado; o motor consome, executa e grava o resultado no mesmo
registro. Cada comando tem estado (`pendente`, `executando`, `concluído`, `falhou`), prazo de
validade e resultado em JSON.

**Racional**: é o único mecanismo que funciona com painel e motor em máquinas diferentes, sem
abrir porta no motor nem expor a máquina do operador na internet. Reaproveita o banco que os dois
já compartilham. Latência medida em segundos, dentro do alvo de SC-005 (30s para o teste de busca).

**Alternativas rejeitadas**:
- HTTP direto no motor: exigiria expor o contêiner `worker` — que é justamente o que publica
  no WhatsApp e guarda credenciais. A decisão registrada no projeto para o webhook seguiu o
  mesmo princípio: o que vem da internet chega no painel, nunca no worker.
- Fazer o painel executar o scraping em Node: duplicaria a lógica de extração — a parte mais
  frágil e mais calibrada do sistema.

**Consequência**: ações do usuário são assíncronas por natureza. A interface mostra progresso
real ("procurando…"), não spinner decorativo, e trata o caso de o motor estar parado — dizendo
exatamente isso, em vez de esperar para sempre.

---

## R4 — Credenciais cifradas em repouso

**Decisão**: AES-256-GCM com chave mestra em variável de ambiente do servidor, cifrando o token
de instância do WhatsApp e a sessão do Mercado Livre antes de gravar. No Python, via
`cryptography` (nova dependência, junto de `psycopg` que já é exigido no modo Postgres); no
painel, via `node:crypto` nativo. Nenhuma credencial volta ao cliente, nem mascarada.

**Racional**: FR-020 exige cifra em repouso. O motor já abandona o modo "stdlib pura" quando roda
em Postgres, então a dependência não introduz uma restrição nova.

**Alternativa rejeitada**: guardar em claro contando com o acesso restrito ao banco — inaceitável
para um sistema que passará a guardar sessões de contas de terceiros.

---

## R5 — Fluxo de conexão do WhatsApp

**Contrato confirmado** (`contracts/whatsapp-provider-openapi.yaml`, validado contra a conta real):

| Operação | Endpoint | Autenticação |
|---|---|---|
| Criar instância | `POST /instance/create` | `admintoken` |
| Listar instâncias | `GET /instance/all` | `admintoken` |
| Conectar (QR ou pareamento) | `POST /instance/connect` | `token` da instância |
| Estado | `GET /instance/status` | `token` |
| Desconectar | `POST /instance/disconnect` | `token` |
| Grupos | `GET /group/list` · `POST /group/create` | `token` |
| Webhook | `GET/POST /webhook` | `token` |
| Limites do número | `GET /instance/wa_messages_limits` | `token` |
| Espaçamento nativo | `POST /instance/updateDelaySettings` | `token` |

`POST /instance/connect` **sem** `phone` devolve `qrcode` em base64 (validade 2 min); **com**
`phone` devolve `paircode` (5 min). Estados do provedor: `disconnected`, `connecting`,
`connected`, `hibernated`.

**Decisão**: webhook do evento `connection` como sinal primário de mudança de estado, com
consulta de estado como rede de segurança enquanto o QR está na tela. Os quatro estados do
provedor são traduzidos para os onze estados de produto de FR-011 combinando-os com o estado
local da conexão (aguardando leitura, código expirado, reconectando…).

**Racional**: o mesmo padrão já provado no projeto para as mensagens do monitoramento —
webhook como caminho rápido, leitura periódica como rede de segurança (`docs/MELHORIAS-PENDENTES.md`).

**Risco aberto**: a resposta de criação pode trazer `info` avisando que a instância será
desconectada e apagada em 1 hora — comportamento de instância sem plano. **Verificar criando uma
instância descartável na primeira tarefa desta área**, antes de construir o provisionamento em cima.

**Validação (D33)**: o fluxo completo — QR, conectado, queda, reconexão, sincronização — é
exercitado na instância `Pessoal`, que está desconectada. A instância de produção
(`bot de promoções`) nunca é reconectada.

---

## R6 — Teto de segurança por conexão

**Decisão**: teto aplicado no publicador, antes do envio, por conexão e por janela móvel de
tempo — não por automação. Quando o teto segura uma publicação, o motivo fica visível em
linguagem comum ("segurando envios para proteger a conta"). Complementado por
`POST /instance/updateDelaySettings` (espaçamento nativo do provedor) e por
`GET /instance/wa_messages_limits`, que diagnostica restrição real do WhatsApp e alimenta o aviso.

**Racional**: FR-046. Duas automações no mesmo número somam volume que nenhuma delas tem
sozinha — o teto precisa viver na conexão, que é onde o risco existe.

---

## R7 — O que da busca vira configuração e o que fica interno

**Vira configuração** (FR-030): palavras-chave; onde buscar (resultados da busca e/ou página de
ofertas, combináveis); desconto mínimo; faixa de preço; e, em Avançado, palavras e marcas a excluir.

**Fica interno, decidido pela Afilify**: número de páginas, pausas entre requisições e entre
termos, limite de páginas vazias, categoria consultada, cabeçalhos e estratégia anti-bloqueio,
tentativas, ordem dos termos, e todo o mecanismo de agendamento.

**Fica na curadoria do tipo de nicho** (FR-038a): marcas aceitas, palavras proibidas, unidade
mínima, termos de contratipo — hoje em `nichos/*.py`, que passam a ser **modelos de nicho**
selecionáveis na criação do projeto, versionados no produto e não editáveis pelo usuário comum.

**Sinais automáticos do anúncio** (FR-038b): loja oficial, reputação do vendedor, avaliação e
coerência de preço, avaliados sobre dados que a extração já captura hoje
(`loja_oficial`, `vendedor`, `avaliacao`, `vendidos`, `preco_original`).

---

## R8 — "Testar busca" sem enganar o usuário

**Decisão**: o teste executa **o mesmo caminho de código** da coleta real, com um limite de
amostra, e devolve contagem de compatíveis mais os primeiros itens qualificados. Nunca uma
consulta diferente nem dados de exemplo.

**Racional**: FR-033. Um teste que não usa o mesmo caminho vira demonstração — e a primeira vez
que a fonte real divergir da amostra, o usuário perde a confiança na ferramenta inteira.

**Consequência**: o teste consome os mesmos recursos da coleta; por isso entra no limite de uso
de FR-037 e é protegido contra disparos repetidos.

---

## R9 — Múltiplos destinos e o intervalo entre eles

**Decisão**: a Publicação é a unidade de trabalho — uma linha por (oferta, destino, tentativa).
O publicador enfileira uma publicação por destino e aplica o intervalo entre destinos da mesma
oferta. O intervalo é derivado do teto de segurança da conexão, não configurado pelo usuário (D30).

**Consequência de modelagem**: a chave atual de `entregas` — `(mlb_id, canal)` — impede tanto
múltiplos destinos quanto repetição por queda de preço. Precisa de identidade própria por
publicação, com a idempotência garantida por outro caminho (chave de tentativa), preservando a
proteção contra envio duplicado que hoje aquela chave dá de graça.

---

## R10 — Identidade da Oferta

**Achado**: hoje `ofertas.mlb_id` é chave primária global. Dois projetos que encontrarem o mesmo
produto colidem na mesma linha, e o segundo projeto sobrescreveria o estado do primeiro.

**Decisão**: a Oferta pertence ao Projeto; a identidade passa a ser (projeto, identificador do
anúncio). A deduplicação de FR-034 acontece dentro do projeto, por identificador do anúncio e por
título normalizado — mecanismo que já existe (`titulo_norm` e seu índice).

**Racional**: FR-003 exige isolamento entre projetos. Sem isso, dois projetos do mesmo workspace
interferem um no outro silenciosamente.
