# Melhorias pendentes

Coisas decididas mas ainda não feitas. Todas exigem reimplantar no
EasyPanel, então ficaram para a **madrugada**, quando reiniciar os
serviços não atrapalha o grupo.

Ordem sugerida: item 1 primeiro (é bug, está perdendo oferta hoje),
item 2 depois.

---

## 1. BUG — oferta copiada que nunca é enviada (48 horas)

**Prioridade: alta. Está perdendo oferta todo dia.**

### O que acontece

Quando o Maeno posta um produto que a nossa busca já tinha achado dias
atrás, o clonador "adota" aquela oferta antiga: marca como clone, guarda
a mensagem dele e coloca de volta na fila.

Só que a oferta continua com a **data de criação antiga**. E existe uma
regra que tira da fila tudo que tem mais de 48 horas (para não publicar
promoção velha). Resultado: o agente copia certo, mas a mensagem nunca
sai.

### Provas

Dia 26/08, das 14 ofertas do Maeno, 3 foram copiadas e não enviadas:

| Oferta | Log do worker |
|---|---|
| Lattafa Khamrah (10:04) | "clone assumiu" · não enviou |
| Bidaya Maktub Gold (10:29) | "clone assumiu" · não enviou |
| Afnan 9pm (10:39) | "clone assumiu" · não enviou |

No painel, a oferta do Khamrah aparece assim:

```
Perfume Khamrah De Lattafa... · MLBU3191457164 · criada 08-19 · PENDENTE · clone
```

Criada dia 19, sete dias antes. Fora da janela de 48h, invisível para a
fila. Às 10:32 o log confirma: "fila 0 · nenhuma oferta pendente com
link pronto", logo depois de ter copiado o Maktub.

### Conserto

Em `mercadolivre/clonador.py`, no trecho em que o clone adota uma oferta
existente (`clone assumiu`), incluir `criado_em` no UPDATE, com a data de
agora.

Faz sentido: a promoção **é** de agora — quem acabou de anunciar foi o
Maeno. A data antiga era de quando a nossa busca encontrou o produto.

Conferir também o mesmo problema na re-promoção por queda de preço
(`nucleo/comum.py`), que reabre oferta antiga do mesmo jeito.

### Esforço

Uma linha em cada lugar + teste. Reimplantar o worker.

---

## 2. Webhook da uazapi no lugar da leitura de 3 em 3 minutos

**Prioridade: média. Melhora velocidade e evita perda de ofertas.**

### Por que

Hoje o agente pergunta ao WhatsApp de 3 em 3 minutos o que há de novo no
grupo do Maeno. Dois problemas:

**a) A consulta perde mensagem.** Dia 26/08 o Maeno postou um YSL Myslf
às 10:16. A mensagem está no grupo (visto no celular), mas a API da
uazapi não a devolve — testado pedindo até 500 mensagens de histórico.
O agente nunca teve como ver. O buraco aparece nos dados: todos os
intervalos do dia são de 2 a 7 minutos, e entre 10:13 e 10:25 há 12.

**b) Atraso.** O clone sai 2 a 3 minutos depois dele. Com webhook sai em
segundos.

### Como fica

```
uazapi  →  painel (endereço público, com senha)
              ↓ grava no banco
           worker  →  clona e publica
```

Passos:

1. Endereço novo no painel (ex.: `/api/webhook/uazapi`) que recebe o
   aviso e grava numa tabela `rival_mensagens`
2. Senha secreta na URL — sem ela, o pedido é ignorado
3. Worker passa a olhar essa tabela a cada poucos segundos
4. Configurar o webhook na instância da uazapi (hoje está vazio;
   instância "bot de promoções", status connected)
5. Migração do banco para a tabela nova

### Riscos e como tratar

| Risco | Tratamento |
|---|---|
| Webhook não tem segunda chance: se o painel estiver reiniciando, a oferta some | **Manter a leitura do histórico como rede de segurança**, de 10 em 10 minutos em vez de 3 |
| Endereço público aceita mensagem falsa (alguém faria seu grupo publicar o link dele) | Senha secreta obrigatória |
| Clone duplicado (webhook + leitura) | Já resolvido: o controle de mensagens já vistas usa o id da mensagem |

### O que não dá para prometer

Se a uazapi **não recebeu** a mensagem das 10:16 (em vez de ter recebido
e não guardado), o webhook também não vai avisar. Só dá para saber
medindo depois de ligado. Mesmo assim vale pelo ganho de velocidade.

### Decisão tomada

O webhook chega no **painel**, não no worker. O worker manda mensagem no
grupo e é melhor não deixá-lo exposto na internet. O custo é o clone sair
em segundos em vez de instantâneo.

### Esforço

Cerca de 2 horas. Reimplantar painel e worker.

---

## Histórico

- 26/08/2026 — documento criado depois do diagnóstico das ofertas que
  não saíram no dia (5 de 14: 2 pela regra de repostagem, já resolvida
  por configuração; 3 pelo bug das 48 horas).
