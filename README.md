# Afilify

Plataforma de operação de ofertas com link de afiliado: encontra promoções
(Mercado Livre + Shopee), gera o link, publica em grupos de WhatsApp com
ritmo humano — e um painel web onde tudo é criado e operado sem tocar em
código.

**Projeto, automação, fonte, destino e conexão são DADOS**, criados pela
interface. Conectar um WhatsApp é escanear um QR na tela; configurar o que
procurar são quatro campos e um botão "Testar busca" que mostra o que aquela
configuração traria de verdade.

Motor em **Python 3.9 puro** (zero pip no modo SQLite). Painel em
**Next.js**. Um único banco compartilhado pelos dois.

## Mapa do repositório

```
runner.py               supervisor: um processo-filho por perfil ativo,
                        reinício com backoff se um filho cair
agente.py               CLI de entrada (PERFIL=... agente.py ml <cmd>)

nucleo/                 compartilhado por todos os marketplaces
  comum.py                config dinâmica, banco, mensagem, uazapi, entregas
  storage.py              mesmo código roda SQLite ou Postgres (STORAGE=)
  nicho.py, perfil.py     carregadores de nichos/ e perfis/

mercadolivre/           buscador (vitrine + busca logada), gerador de
                        links, clonador de rival, daemon de publicação
shopee/                 Open API oficial (GraphQL assinado); o daemon
                        coleta daqui quando o perfil lista "shopee"

nucleo/contexto.py      QUEM o motor está operando: automação do banco
                        (AUTOMACAO_ID) ou arquivo de perfil (PERFIL)
nucleo/conexoes/        contas externas (whatsapp.py, mercadolivre.py)
nucleo/comandos.py      pedidos do painel ao motor (testar busca etc.)
nucleo/publicacao.py    uma oferta saindo em um destino
nucleo/protecao.py      teto de segurança por número conectado
nucleo/oferta.py        ciclo de vida da oferta, incluindo retenção

nichos/                 o QUE é oferta boa (perfumes.py, casa.py) — vira
                        "tipo de nicho" escolhido ao criar o projeto
perfis/                 modo antigo: nicho + marketplaces + grupo + ritmo
                        em arquivo (perfumes_ml.py, casa_ml_shopee.py)

painel/                 Next.js — painel do produto, lê o MESMO banco do motor
db/                     migrações Postgres 0001..0005 + importador de cutover
deploy/                 compose, Dockerfiles, Caddy, backup, systemd
tests/                  84 testes (rodam em banco temporário, sempre)
dados/                  gerado em execução, fora do git (ofertas.db, logs)
```

## Operar

```bash
# tudo (perfis ativos, cada um no seu processo, lock por perfil)
python3 runner.py

# um perfil específico, manual
PERFIL=perfumes_ml python3 agente.py ml rodar          # daemon completo
PERFIL=perfumes_ml python3 agente.py ml buscar --seco  # só olhar
python3 agente.py ml grupo --listar                    # JIDs da conta

# painel (Mac/local — build normal; standalone é só para Docker)
cd painel && pnpm build && pnpm start -p 3001
```

Um perfil roda quando `ATIVO=True` **e** tem destino: `GRUPO_WHATSAPP`
no arquivo *ou* grupo escolhido na página **/destinos** do painel — é
assim que o grupo de casa liga sem tocar em código.

## Painel ↔ motor: config dinâmica

O motor lê a tabela `config` a cada uso; o painel edita; **nada
reinicia**. Chaves por perfil (semeadas no primeiro boot com os valores
vigentes, nunca sobrescrevendo edição):

| chave      | página do painel | o que controla |
|------------|------------------|----------------|
| `mensagem`  | Mensagens       | modelo da mensagem + rodapé |
| `headlines` | Mensagens       | pools de abertura rotativos |
| `ritmo`     | Ritmo & Regras  | cota/dia, janela, coletas, validade, proporção |
| `clonador`  | Fontes          | ligado, grupos rivais monitorados |
| `canal`     | Destinos        | grupo de destino da publicação |
| `tracking`  | Configurações   | cliques via `/r/{código}` (desligado por padrão) |

Cota e janela novas valem a partir do plano de **amanhã** (o plano do
dia é sorteado uma vez); o resto vale na mensagem seguinte.

## Tracking de cliques

Ligado em Configurações (exige base `https://…` pública), a mensagem sai
com `{base}/r/{código}`; a rota pública do painel grava o clique e
redireciona ao link de afiliado. Desligado (padrão), o link de afiliado
vai direto — comportamento idêntico ao de sempre.

## Cutover SQLite → Postgres

```bash
psql "$DATABASE_URL" -f db/0001_init.sql   # ...até 0005, em ordem
DATABASE_URL=postgres://... python3 db/importar_sqlite.py   # idempotente
# motor:  STORAGE=postgres DATABASE_URL=...  (pip install psycopg)
# painel: DATABASE_URL=... (sem SQLITE_PATH)
```

O importador cobre `ofertas`, `estado`, `entregas`, `config` e
`cliques` — pode rodar de novo sem duplicar nada.

## Testes

```bash
python3 -m unittest discover -s tests -t .
```

Todo módulo de teste força banco temporário e **recusa** rodar se
apontar para banco real. CI no GitHub Actions faz o mesmo.

## Deploy

`deploy/README.md` tem o passo a passo da VPS (compose + Caddy +
backup). O painel também sobe na Vercel (build normal, `DATABASE_URL`
do Postgres) — o motor não: fica numa máquina sua (Mac hoje, VPS
depois).

## O que ainda depende de insumo externo

| item | destrava |
|------|----------|
| connection string Postgres (Neon) | ensaio do cutover + painel público |
| conta Vercel | painel fora do Mac |
| domínio (afilify.com.br) | tracking em produção |
| VPS | motor 24/7 fora do Mac |
| JID do grupo casa | 2º projeto no ar (escolher em /canais) |


## Como a plataforma se organiza

```
Workspace ──┬── Conexão      (WhatsApp, Mercado Livre, Shopee)
            └── Projeto      ("Perfumes" — traz o tipo de nicho)
                  └── Automação   ("Ofertas Mercado Livre")
                        ├── Fonte    o que procurar, e onde
                        ├── Destino  para onde publicar (vários)
                        ├── Mensagem como a publicação fica
                        └── Ritmo    volume, janela, validade
```

Oferta é o que foi encontrado. Publicação é cada envio dela em um destino —
por isso a mesma oferta pode sair em dois grupos, e voltar quando o preço
cai, sem virar mensagem repetida.

## Configurar uma fonte de busca

Quatro campos, e só: palavras-chave, onde buscar (resultados e/ou página de
ofertas), desconto mínimo e faixa de preço. Exclusões ficam em Avançado.

Páginas, pausas, tentativas, categoria e cabeçalhos **não** são configuração
— são decisões da plataforma. A API recusa esses campos, não apenas a tela.

**Testar busca** roda o mesmo caminho da coleta real, só que menor, e mostra
a contagem de compatíveis com exemplos. Quando volta vazio, diz qual critério
provavelmente está apertando demais.

## Segurança das contas

Credenciais (token da instância de WhatsApp, sessão do Mercado Livre) são
cifradas em repouso com AES-256-GCM, chave mestra em `AFILIFY_CHAVE_MESTRA`.
O identificador da conexão entra como dado autenticado — credencial de uma
conexão não abre em outra.

O volume de envio tem teto por **número conectado**, não por automação: duas
automações no mesmo número somam um volume que nenhuma delas tem sozinha.
Isso é decisão da plataforma e não aparece como campo.

## Verificação

```bash
scripts/harness/fase.sh              # situação das fases
scripts/harness/ciclo.sh             # fecha fase concluída e aponta a próxima
scripts/harness/verify-nucleo.sh     # lint, typecheck, testes, build, linguagem,
                                     # anti-mock, congelados, QA de navegador
scripts/harness/guarda-banco.sh      # recusa apontar para o banco de produção
```

A especificação completa, com decisões e evidências de validação, está em
`specs/001-afilify-saas-core/`.
