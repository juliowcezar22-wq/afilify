# Agente ML — Promoções de Perfume

Porte do fluxo n8n *"BOT DE Promoções do ML - PERFUMES (v2) Sem I.A"* para um
processo único em Python. Sem n8n, sem Google Sheets, sem `pip install`.

| n8n | aqui |
|---|---|
| 3 Schedule Triggers | um daemon com o mesmo calendário |
| Google Sheets (fila + dedup + status) | SQLite `ofertas.db` |
| Code node com regex de HTML | estado JSON que o próprio ML renderiza |
| só a vitrine `/ofertas` (54 anúncios) | vitrine **+ busca** (milhares) |
| Credenciais OAuth do Sheets | nenhuma |

## Comandos

```
python3 agente.py rodar       daemon — os 3 blocos no horário certo
python3 agente.py buscar      BLOCO 1 (+2) agora
python3 agente.py links       BLOCO 2 para o que ainda não tem link
python3 agente.py enviar      BLOCO 3, uma rodada
python3 agente.py listar      o que está na fila
python3 agente.py marcas      quais marcas passam e quais estão barradas
python3 agente.py termos      valida os termos de busca
python3 agente.py simular     mostra o ritmo de um dia de envios
python3 agente.py grupo       mostra o grupo de destino (--listar p/ todos)
python3 agente.py clonar      BLOCO 4: varre os grupos rivais
python3 agente.py status      raio-x da operação
python3 agente.py exportar    JSON dos dados coletados
python3 agente.py testar      confere cookie, uazapi e banco
python3 agente.py limpar      apaga enviadas com mais de 30 dias
```

Flags úteis: `--seco` (mostra e não envia), `--forcar` (ignora a janela de
horário), `--limite N`, `--paginas N`.

## Instalar na VPS

Precisa só de **Python 3.9+**. Nenhuma dependência externa.

```bash
sudo useradd -r -m -d /opt/grupo-promocoes promocoes
sudo mkdir -p /opt/grupo-promocoes
sudo rsync -a --exclude dados/ ./ /opt/grupo-promocoes/
sudo chown -R promocoes:promocoes /opt/grupo-promocoes
sudo chmod 600 /opt/grupo-promocoes/.env /opt/grupo-promocoes/.mlcookie

# confere antes de ligar
sudo -u promocoes python3 /opt/grupo-promocoes/mercadolivre/agente.py testar
sudo -u promocoes python3 /opt/grupo-promocoes/mercadolivre/agente.py enviar --seco --forcar

sudo cp deploy/agente-ml.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now agente-ml
journalctl -u agente-ml -f
```

Se você não usar o usuário `promocoes`, ajuste `User=` e os caminhos no
`deploy/agente-ml.service`.

## O cookie

`.mlcookie` é o header `Cookie` inteiro da sua sessão de afiliado — é uma
credencial completa, tratada como senha (`chmod 600`, fora do git).

**Ele expira em ~30 dias.** Quando o log mostrar
`sessão do Mercado Livre expirada`, renove:

1. Abra <https://www.mercadolivre.com.br/afiliados/linkbuilder> logado
2. F12 → aba Network → gere um link qualquer
3. Clique na requisição `createLink` → copie o header `Cookie` inteiro
4. Cole em `/opt/grupo-promocoes/.mlcookie` e `systemctl restart agente-ml`

O agente não morre com o cookie vencido: ele registra o erro, para o BLOCO 2 e
segue rodando. As ofertas ficam pendentes sem link e ninguém é publicado sem
o seu código de afiliado.

## As duas fontes

O BLOCO 1 coleta de dois lugares e faz dedup por MLB_ID **e** por título
(o mesmo perfume aparece como anúncio avulso e como catálogo, com ids
diferentes — sem isso o grupo recebe a oferta duas vezes).

| | Vitrine `/ofertas` | Busca `lista.mercadolivre.com.br` |
|---|---|---|
| Volume | ~54 anúncios | centenas a milhares por termo |
| Marcas | fracas | Rabanne, Dior, Natura, Lattafa, Lancôme… |
| Badges | `OFERTA DO DIA`, `RELÂMPAGO` | não tem |
| Cookie | não precisa | **exige `.mlcookie`** |

Vale manter as duas: a vitrine é a única com os badges que alimentam suas 4
mensagens, e funciona mesmo com o cookie vencido. A busca é o volume.

Numa execução real com 15 termos: 12 da vitrine + 86 da busca = **98 ofertas únicas**.

### Termos de busca

`TERMOS_BUSCA` no topo do arquivo. Cada termo é 1 requisição e até 60 produtos.

**Valide antes de adicionar:** em algumas consultas o ML responde em streaming
e o payload não vem na primeira resposta — sem erro, só vazio. `boticario`
funciona, `perfume boticario` não.

```bash
python3 agente.py termos                      # testa os configurados
python3 agente.py termos "perfume dior" "lattafa"   # testa candidatos
```

## Cadência e volume

Medido no dia 16→17/08: coleta às 22:50 e de novo às 07:55 (9 horas) devolveu
**22 ofertas novas e 55 já conhecidas**. Com os 15 termos de busca, uma coleta
sozinha rende **~98 ofertas únicas**.

| | |
|---|---|
| Coleta | 4x ao dia (7h, 12h, 17h, 22h) |
| Oferta nova entrando | ~100–140/dia |
| Publicação | 1 por vez, intervalo adaptativo |
| Volume publicado | **60–85/dia, sorteado** — média de ~12min entre elas |

### O plano do dia

Sorteado **uma vez por dia**, na primeira vez que o agente olha o relógio:
quantas ofertas, que horas começa, que horas termina. Grupo de verdade não
posta o mesmo número todo dia entre 08:00 e 22:00 cravado.

```
plano sorteado: 66 ofertas entre 08:50 e 22:21   → 65 envios, média 13min
plano sorteado: 61 ofertas entre 08:12 e 22:18   → 60 envios, média 14min
plano sorteado: 76 ofertas entre 08:06 e 21:36   → 75 envios, média 11min
```

### Como o intervalo é decidido

Nada de intervalo fixo. A cada envio o agente recalcula, respeitando **duas**
restrições — vale sempre a mais lenta:

1. **espalhar a cota do dia pelo que resta do dia** — senão a fila cheia da
   manhã queima a cota até meio-dia e o grupo fica mudo à tarde;
2. **espalhar a fila pelo que resta até a próxima coleta** — senão 5 ofertas
   às 7h saem todas às 7h05 e o grupo fica parado até meio-dia.

Em cima disso, 30% dos envios saem em **rajada** (1–3min). A rajada é
compensada nos intervalos seguintes, então a média não muda e o dia fecha
na hora certa.

Um dia real (`simular`):

```
08:35 08:37 08:49   09:01 09:23 09:39
10:02 10:15 10:18 10:28 10:30 10:32 10:42   11:01 11:24 11:39
...
19:09 19:11 19:12 19:32 19:34 19:51 19:54   20:34   21:09 21:10
64 envios · intervalo 1–40min (média 12) · 23 colados ≤3min
```

```bash
python3 agente.py simular                      # com a fila real
python3 agente.py simular --fila 98 --entrada 30
python3 agente.py simular --cota 40            # testa uma cota fixa
```

### Sobre o número não cair

Três defesas: intervalo nunca repetido, pausa de 5–15s antes de cada POST, e
cota diária sorteada dentro de um teto.

**Para número novo ou recém-pareado, comece menor.** Uma semana com
`ENVIOS_POR_DIA = (10, 16)`, depois suba. 70/dia de cara num chip frio é o
cenário de risco — rode `simular` antes de cada aumento.

## A mensagem

```
*🔥 PELA METADE DO PREÇO*

*Eudora Club 6 Exclusive 95 mL*

De ~R$ 299,00~ ❌
Por *R$ 94,39* ✅

Loja Oficial Selvagem Essence no ML
🔗 https://meli.la/1cs8wFD
```

**Headline sorteada.** Seis pools em `HEADLINES`, escolhidos pelo contexto da
oferta — badge (relâmpago / oferta do dia / mais vendido) ou faixa de desconto
(`≥45%` choque, `≥25%` médio, resto geral). Nunca repete a headline anterior.

**Linha da loja.** Sai só quando o ML marca a loja como oficial no card — o
selo vem do ícone `icon_cockade`, não é inventado. O nome sai de quatro
formatos diferentes que o ML usa:

| template do ML | vira |
|---|---|
| `{label} por Lipx {icon}` | Loja Oficial **Lipx** no ML |
| `{label} {icon}` | Loja Oficial **Natura** no ML |
| `Gota Brasil {icon}` | Loja Oficial **Gota Brasil** no ML |
| `{label}` (sem ícone) | *sem linha de loja* |

`MOSTRAR_LOJA_COMUM = True` também mostra vendedor não-oficial.

**Título limpo.** O ML entulha de SEO: *"Perfume Ted Lapidus Pour Homme Edt M
100ml Novo Lacrado Original Homem"* vira *"Ted Lapidus Pour Homme Edt M
100ml"*. Tira prefixo (`Perfume Masculino…`) e ruído do fim, nunca o miolo, e
nunca deixa menos de 3 palavras. `LIMPAR_TITULO = False` desliga.

**Rodapé.** `RODAPE_MENSAGEM` está vazio, igual ao grupo de referência. Link de
afiliado é publicidade — se quiser sinalizar, ponha
`"_#publicidade · link de afiliado_"` ali.

## BLOCO 4 — monitor da concorrência

Lê os grupos rivais em que a sua linha já está, identifica o **produto** que
eles anunciaram e joga na sua fila com o seu link.

```
CLONE_GRUPOS = ["120363406025827790@g.us"]   # #101 MAENO PROMOS | PERFUMES
CLONE_INTERVALO_SEG = 180
```

Como funciona: lê a mensagem via `/message/find`, tira o nome em negrito e os
preços, procura o produto na busca do ML casando **título + preço** (só título
confunde 50ml com 100ml), passa pelo seu filtro de marcas e gera o seu link.
Clone **fura a fila** — o rival achou primeiro, então sai no próximo envio —
mas respeita o ritmo do dia, não dispara na hora.

O link deles não serve para identificar o produto: `meli.la/...` resolve para
a página de listas do afiliado, não para um produto único. Por isso o casamento
é por nome e preço.

**O que ele não faz, de propósito:** copiar a foto e o texto deles. Aquelas
fotos ambientizadas são produção autoral do concorrente; republicar é usar
criação de terceiro. O agente pega só a identidade do produto — que é fato
público no ML — e remonta com dado do ML e o seu formato. `CLONE_COPIAR_MIDIA`
existe, mas ligar é decisão sua.

## Proporção importado × nacional

```
PROPORCAO_IMPORTADOS = 0.70   # 7 de cada 10 envios
```

Não é ordenação fixa: a fila olha o que **já saiu hoje**. Importado abaixo da
cota fura na frente; acima, a vez é do nacional. Converge ao longo do dia sem
deixar o grupo só com um tipo. As famílias saem das listas `MARCAS_*`
(`importada`, `arabe`, `nacional`, `casa`) — importado = `importada` + `arabe`.

## Filtro de marcas

Só publica marca que esteja numa das quatro listas no topo do `agente.py`:

| Lista | Para quê |
|---|---|
| `MARCAS_IMPORTADAS` | designer/luxo — Dior, Chanel, Carolina Herrera… |
| `MARCAS_ARABES` | Lattafa, Armaf, Rasasi, Al Wataniah, Rayhaan… |
| `MARCAS_NACIONAIS` | Natura, O Boticário, Eudora e afins |
| `MARCAS_CASAS_NACIONAIS` | Lab 8, Inthebox — **as únicas onde contratipo é aceito** |

A marca vem do **rótulo que o próprio ML põe no card**, não de regex no título.
Isso pega coisas que o título esconde: *"Perfume Sedutor Árabe Sabah 100ml"* não
cita marca nenhuma, mas o ML rotula como `AL WATANIAH`. Sem rótulo, cai para o
título — e card sem rótulo é quase sempre a paralela que você não quer.

Contratipo (`inspirado`, `contratipo`, `referência olfativa`…) só passa se a
marca estiver em `MARCAS_CASAS_NACIONAIS`. Um "contratipo do Dior" vendido por
paralela é barrado; um contratipo da Lab 8 passa.

### Curando a lista

```bash
python3 agente.py marcas             # o que passa e o que está barrado
python3 agente.py marcas --detalhe   # com os títulos de cada marca barrada
```

Rode de vez em quando: a categoria muda e marca boa nova aparece. Para liberar,
acrescente o nome na lista certa.

## Ajustes

Tudo no bloco `CONFIGURAÇÃO` no topo do `agente.py`:

| Constante | Padrão | O que faz |
|---|---|---|
| `BUSCA_HORAS` | `[7,12,17,22]` | quando o BLOCO 1 roda |
| `ENVIOS_POR_DIA` | `(95, 135)` | **ofertas** por dia, sorteado — calibrado no MAENO |
| `ENVIO_INICIO_JANELA` | `(8.75, 9.5)` | hora de início, sorteada |
| `ENVIO_FIM_JANELA` | `(22.0, 22.75)` | hora de fim, sorteada |
| `ENVIO_POR_EXECUCAO` | `1` | ofertas por rodada (`0` = todas) |
| `ENVIO_ADAPTATIVO` | `True` | `False` volta ao intervalo fixo sorteado |
| `ENVIO_DISPERSAO` | `0.82` | sigma do lognormal — a forma da cadência |
| `ENVIO_INTERVALO_LIMITES` | `(1, 90)` | trava de segurança, não o ritmo |
| `DESCONTO_MINIMO` | `10` | % mínimo |
| `VOLUME_MINIMO_ML` | `0` | `0` = comportamento do n8n; `50` corta decants |
| `MARCAS_*` | 4 listas | quem pode ser publicado (ver acima) |
| `TERMOS_CONTRATIPO` | 13 termos | o que marca um anúncio como contratipo |
| `TERMOS_BUSCA` | 15 termos | o que a fonte 2 varre |
| `PAUSA_ENTRE_BUSCAS` | `(4, 8)` s | a busca é mais sensível que a vitrine |
| `VALIDADE_HORAS` | `48` | não publica oferta capturada antes disso |
| `ORDEM_ENVIO` | `"novas"` | `novas` / `antigas` / `maior_desconto` |
| `HEADLINES` | 6 pools | chamadas sorteadas por contexto |
| `LIMPAR_TITULO` | `True` | tira o SEO do nome do produto |
| `RODAPE_MENSAGEM` | `""` | linha final (aviso de publicidade) |

## O que mudou em relação ao fluxo do n8n

Três bugs que estavam derrubando o resultado:

1. **O regex pegava o `href` errado.** O primeiro link do card é uma âncora de
   campanha (`#poly_black_friday`), não o produto. Somado a um regex de ID que
   não cobria catálogo (`MLB6139411` com 7 dígitos, `MLBU3402023514` com letra),
   o fluxo descartava **~85% das ofertas** — inclusive Carolina Herrera e Natura.
   Medido na mesma página: **7 aprovadas antes, 34 depois.**

2. **`Sheets: Buscar Ofertas não Enviadas` não filtrava nada.** Lia a planilha
   inteira a cada 40 min e republicava tudo, para sempre, apesar de marcar
   `STATUS ENVIO=ENVIADO`. Aqui a fila é `status = PENDENTE` de verdade.

3. **`IF: Horário 8h-22h` estava desabilitado e desconectado.** A nota dizia
   8h–22h; na prática publicava 24h. A janela agora é real, e com fuso
   explícito (`TIMEZONE`) — VPS em UTC publicaria 3h fora do horário.

Outras diferenças:

- **Dados vêm do JSON que o ML já embute na página**, não de regex de HTML. Além
  de mais estável, o preço fica exato: o regex de centavos lia R$ 159,00 onde o
  produto custa R$ 159,95. O parser de HTML continua no código como fallback
  automático caso esse JSON suma.
- **2 páginas em vez de 50.** O ML informa o total (`paging.total: 55`); o fluxo
  varria 50 páginas fixas, 4x ao dia — ~48 requisições inúteis por execução.
- **Badge voltou a funcionar.** A classe mudou para
  `poly-component__highlight-countdown`, então o regex antigo nunca casava e
  tudo caía em "PROMOÇÃO GERAL".
- **"no Pix" aparece na mensagem.** Vários preços do card só valem no Pix; sem
  isso o grupo descobre no checkout.
- **`~~texto~~` virou `~texto~`**, que é o tachado que o WhatsApp entende.
- **O daemon não publica ao subir.** Restart/deploy não vira mensagem
  inesperada; use `--agora` para forçar um ciclo.
- **SIGTERM não interrompe um envio pela metade** — ele para antes do POST.
