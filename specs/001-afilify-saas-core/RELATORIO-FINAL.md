# Afilify — núcleo SaaS · relatório de entrega

**Branch**: `feat/afilify-saas-redesign` · worktree isolada · sem push, sem merge, sem deploy
**Produção**: intocada. Continua rodando na VPS com o modelo antigo.
**Data**: 2026-08-27

---

## O que mudou, em uma frase

Projeto, automação, fonte, destino e conexão deixaram de ser arquivo e variável de ambiente e
viraram **dados criados pela interface** — e o motor passou a obedecer a eles sem reinício.

## Os números

| | |
|---|---|
| Fases concluídas | 9 de 9, cada uma fechada com verificação completa |
| Tarefas | 66 de 67 (a 67ª é este relatório) |
| Testes | 226 no motor, 23 no painel |
| Evidências de validação com dado real | 36 |
| Commits | 23 |
| Decisões registradas | D24–D37 |
| Arquivos do Clonador alterados | **zero** (congelado, verificado por gate a cada tarefa) |

## O que passou a existir

**Conectar um WhatsApp** é escanear um QR na tela. A conexão sobrevive a refresh, detecta queda
sozinha e oferece reconectar. Você validou isso pessoalmente: a instância nasceu na sua conta do
provedor e apareceu como conectada.

**Criar um projeto** é preencher nome e tipo de produto. Criar uma automação dentro dele é
preencher um nome. Ligar exige fonte, destino e conexão conectada — faltando qualquer um, a
ativação é recusada dizendo **o que** falta, em frase de gente. O supervisor sobe o processo da
automação nova no ciclo seguinte, sem editar código.

**Configurar o que procurar** são quatro campos: palavras-chave, onde buscar, desconto mínimo,
faixa de preço. Exclusões em Avançado. E um botão **Testar busca** que roda o mesmo caminho da
coleta real e mostra o que aquela configuração traria — com a contagem e exemplos.

**Publicar em vários grupos** funciona: cada envio é uma publicação com resultado próprio,
espaçados para proteger o número. Uma oferta volta ao mesmo grupo só quando o preço cai abaixo
do que já foi publicado.

**Nada se perde por falha nossa**: oferta que não pôde sair fica retida com o motivo, e volta
sozinha quando a causa é resolvida.

## Provado com dado real

A cadeia inteira, exercitada de ponta a ponta em 27/08:

```
critérios da Fonte  →  coleta no Mercado Livre  →  filtro  →  link de afiliado
                                                                     ↓
                                          publicado no grupo "Teste" do seu WhatsApp
```

Produto: *Perfume Sedutor Árabe Sabah 100ml*, −48%, R$ 118,15 · link `meli.la/1ybHkq7` com a sua
tag · mensagem entregue.

Outras 35 evidências em [VALIDATION.md](../../VALIDATION.md), incluindo os estados de conexão,
o limite de contas simultâneas, o isolamento entre projetos e o QA de navegador.

## O que NÃO está pronto

| Item | Situação |
|---|---|
| Conexão do Mercado Livre | Mostra estado real, valida gerando link e avisa antes de expirar — mas **renovar continua fora da Afilify**, por decisão sua (a extensão de navegador é a próxima rodada) |
| Migração da operação atual | Não acontece nesta rodada. O projeto de perfumes continua no modelo antigo até você validar e aprovar o merge |
| Busca logada do Mercado Livre | **Bloqueada pelo ML no momento** — devolve captcha. A página de ofertas, que não exige sessão, funciona normalmente |
| Cadastro público, permissões, cobrança | Fora do escopo por decisão (D27); o modelo já comporta |
| DDL no Postgres | Exercitado só no SQLite — não havia Postgres nem Docker disponíveis aqui |

## Três defeitos que só o teste com serviço real encontrou

1. **Seis rotas de API não existiam.** Um `export` a mais em `route.ts` fez o Next descartá-las
   sem erro nenhum: build, lint e typecheck passavam.
2. **A tela dizia "Conectando" enquanto esperava você pegar o celular** — e o código expirava sem
   nada mudar na tela.
3. **Remover uma conexão apagava a conta no provedor** mesmo quando ela já existia antes da
   Afilify. Isso apagou sua instância `Pessoal` durante o teste (estava desconectada, nenhuma
   sessão caiu; recriada em seguida).

Nenhum apareceria em revisão de código. Todos têm teste agora.

## Riscos que continuam abertos

- **Bloqueio da busca do ML.** A fonte de maior volume está sendo recusada agora. Vale medir
  quantos dias isso persiste antes de decidir se muda a estratégia de coleta.
- **Sessão do Mercado Livre vence em 19 dias.** Depois disso, sem renovação manual, a geração de
  link para.
- **Duas vagas de WhatsApp ocupadas** (`bot de promoções` e `Teste`). Conectar uma terceira exige
  desconectar uma — a plataforma avisa, mas vale saber.

## Como revisar

```bash
cd ~/Downloads/afilify-saas-redesign
git log --oneline main..HEAD          # 23 commits
scripts/harness/fase.sh               # as 9 fases e seu estado
scripts/harness/verify-nucleo.sh      # a verificação completa
```

Leituras, em ordem de utilidade: `PROGRESS.md` (o que foi feito e por quê),
`VALIDATION.md` (o que foi provado, com que dado), `specs/001-afilify-saas-core/decisions.md`
(por que cada escolha).

## Antes do merge

- [ ] Você operar a plataforma por conta própria (roteiro no artefato de entrega)
- [ ] Decidir o que fazer com a instância `Teste`, que hoje ocupa uma vaga
- [ ] Exercitar o DDL num Postgres real
- [ ] Especificar a migração do projeto de perfumes — trabalho separado, depois desta validação
