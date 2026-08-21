# Afilify

Plataforma de operação de ofertas com link de afiliado: agentes que
encontram promoções (Mercado Livre + Shopee), geram o link, publicam em
grupos de WhatsApp com ritmo humano — e um painel web que controla tudo
sem mexer em arquivo nem reiniciar nada.

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

nichos/                 o QUE publicar  (perfumes.py, casa.py)
perfis/                 nicho + marketplaces + grupo + ritmo = um projeto
                        (perfumes_ml.py, casa_ml_shopee.py)

painel/                 Next.js — 10 páginas, lê o MESMO banco do motor
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
no arquivo *ou* grupo escolhido na página **/canais** do painel — é
assim que o grupo de casa liga sem tocar em código.

## Painel ↔ motor: config dinâmica

O motor lê a tabela `config` a cada uso; o painel edita; **nada
reinicia**. Chaves por perfil (semeadas no primeiro boot com os valores
vigentes, nunca sobrescrevendo edição):

| chave      | página do painel | o que controla |
|------------|------------------|----------------|
| `mensagem`  | Templates       | modelo da mensagem + rodapé |
| `headlines` | Templates       | pools de abertura rotativos |
| `ritmo`     | Configurações   | cota/dia, janela, coletas, validade, proporção |
| `clonador`  | Copiador        | ligado, grupos rivais monitorados |
| `canal`     | Grupos & canais | grupo de destino da publicação |
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
