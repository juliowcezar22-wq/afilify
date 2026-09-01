# Reimplantar o painel — passo a passo

Ordem importa. Cada passo é reversível, e o anterior a ele continua
funcionando enquanto o próximo não roda.

**A operação não para em nenhum momento.** O motor antigo continua com as
tabelas antigas, que a migração não toca.

---

## Antes: as variáveis novas

No EasyPanel, nos serviços **painel** e **worker**:

| Variável | Para quê | Obrigatória? |
|---|---|---|
| `AFILIFY_CHAVE_MESTRA` | cifra as credenciais das contas conectadas | **sim** — sem ela, conexões não podem ser guardadas |
| `UAZAPI_ADMIN_TOKEN` | criar conexões de WhatsApp pela tela | sim, para o QR funcionar |
| `WEBHOOK_SEGREDO` | protege o endereço que recebe avisos de queda | recomendada |
| `APP_URL` | endereço público do painel, para registrar o webhook | recomendada |

Gerar a chave mestra (uma vez, e **guarde**: perdê-la torna as credenciais
já cifradas ilegíveis):

```bash
python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Gerar o segredo do webhook:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(24))"
```

`AFILIFY_CHAVE_MESTRA` precisa ser **a mesma** nos dois serviços — é ela que
permite o painel ler o que o motor gravou, e vice-versa.

---

## 1. Backup

```bash
pg_dump "$DATABASE_URL" > afilify-antes-da-migracao.sql
```

É a rede de segurança de tudo abaixo. Não pule.

## 2. Aplicar o schema novo

Não há passo manual: `conectar_pg()` aplica todos os arquivos de `db/*.sql`
ao abrir, e eles são idempotentes (`IF NOT EXISTS`). Subir o worker com o
código novo cria as tabelas.

Se preferir aplicar antes, pelo terminal do serviço `db`:

```bash
psql "$DATABASE_URL" -f db/0009_entidades.sql
psql "$DATABASE_URL" -f db/0010_ofertas_publicacoes.sql
```

**Ponto de atenção**: este DDL foi exercitado em SQLite e verificado contra
as regras do Postgres, mas nunca rodou num Postgres de verdade — não havia
um disponível no ambiente de desenvolvimento. É o único passo com risco
residual. Ele é puro `CREATE TABLE IF NOT EXISTS`: se falhar, falha sem
alterar nada do que já existe.

## 3. Migrar a operação para o modelo novo

```bash
# no terminal do serviço worker
python3 db/migrar_operacao.py            # mostra o que faria, sem gravar
python3 db/migrar_operacao.py --aplicar  # grava
```

O que ela faz: transforma o perfil de perfumes em projeto, automação, fonte,
destino e conexão, e copia ofertas e entregas para o modelo novo.

O que ela **não** faz: nada é apagado nem alterado no modelo antigo, e a
automação nasce **pausada**. Ligar é decisão sua, depois de conferir.

Exercitada contra o banco real da virada: 356 ofertas e 159 publicações
migradas, com os estados traduzidos e o modelo antigo intacto. Rodar de novo
não duplica nada.

## 4. Reimplantar

Painel e worker, como sempre.

## 5. Conferir, nesta ordem

1. **Projetos** deve mostrar "Perfumes" com a automação **pausada**
2. **Ofertas** e **Publicações** devem mostrar o histórico real
3. **Desempenho** deve mostrar os números dos últimos dias
4. **Conexões** vai mostrar o WhatsApp da operação — confira se o estado
   bate com a realidade
5. Só então, se tudo bater, **ligue a automação**

Enquanto a automação nova estiver pausada, quem publica é o motor antigo,
como hoje. Ligar as duas ao mesmo tempo **publicaria em dobro** — por isso
a migração não liga nada sozinha.

## Se algo der errado

O modelo antigo está intacto. Para voltar ao estado anterior:

```sql
DROP TABLE IF EXISTS publicacoes, ofertas_projeto, execucoes_fonte, fontes,
  destinos, automacoes, projetos, grupos_conexao, conexoes, comandos,
  limites_plano, tipos_nicho, usuarios CASCADE;
```

O painel volta a mostrar só os blocos legados, e o motor nunca deixou de
usar as tabelas antigas.
