# Auditoria da implementação atual — insumo da spec

Data: 2026-08-26 · Base: `main` (40a245e) + worktree `feat/afilify-saas-redesign` (cf26298)

## 1. Como o domínio existe hoje

| Conceito do produto | Como existe no código | Problema |
|---|---|---|
| Workspace | tabela `workspaces` com 1 linha fixa (`ws-afilify`), sem uso real | Existe no schema, não no comportamento |
| Projeto | **arquivo Python** `perfis/*.py` (`perfumes_ml.py`, `casa_ml_shopee.py`) carregado por `importlib` | Não é dado: criar projeto = escrever arquivo e reiniciar processo |
| Identidade do projeto | string `NOME = "perfumes-ml"` gravada na coluna `ofertas.perfil` | Slug técnico vaza para dados e UI |
| Automação | **implícita**: um processo por perfil (`runner.py` → `agente.py ml rodar`) | Entidade não existe; Fonte/Destino/Ritmo são atributos do perfil |
| Fonte | constantes `TERMOS_BUSCA` (mercadolivre/config.py) + `MERCADOLIVRE["termos"]` do nicho | Hardcoded em código, não configurável |
| Destino | `GRUPO_WHATSAPP` (JID) no perfil, sobreposto por `config.canal.grupo` | Um único destino por projeto |
| Conexão | variáveis de ambiente globais (`UAZAPI_TOKEN`, `ML_AFFILIATE_TAG`, `.mlcookie`) | Uma conexão por instalação, não por workspace |
| Oferta | tabela `ofertas`, PK = `mlb_id` | PK global: a mesma oferta não pode existir em dois projetos |
| Publicação | tabela `entregas`, PK = (`mlb_id`, `canal`) | Só uma publicação por par oferta/canal; sem histórico de repetição |
| Nicho | `nichos/*.py` (marcas, blacklist, headlines, regex) | Curadoria em código; é o filtro de qualidade real |

## 2. Configuração dinâmica (o que já funciona sem restart)

`config(perfil, chave, valor JSON)` — o motor lê a cada uso, o painel grava por `POST /api/config`.

Chaves vivas: `mensagem`, `headlines`, `ritmo`, `clonador`, `canal`, `tracking`.
Não há chave para busca/fonte: **os termos de busca não são editáveis pelo painel**.

## 3. Conexões — estado real

**WhatsApp (uazapi)**: token único de instância no `.env` do servidor. O código usa
`/group/list`, `/group/info`, `/message/find`, `/message/download`, `/send/text`,
`/send/media` e recebe webhook em `POST /api/webhook/uazapi`.
**Não existe** criação de instância, QR, detecção de queda ou reconexão.
A página `/conexoes` é somente leitura (`GET /instance/status`).

**Mercado Livre**: cookie de sessão em arquivo `.mlcookie` (chmod 600) + `ML_AFFILIATE_TAG`.
Usado em dois lugares: (a) `createLink` do Linkbuilder — endpoint interno, não público —
para gerar o link curto; (b) header da busca logada `lista.mercadolivre.com.br`.
Expira em ~30 dias; renovação é manual (F12 → copiar header Cookie → colar no arquivo).
A UI estima validade pelo **mtime do arquivo**, não pelo estado real da sessão.
Confirmado externamente: **o ML não publica API oficial de afiliados** — a sessão é o único caminho hoje.

**Shopee**: Open API oficial assinada (`SHOPEE_APP_ID`/`SHOPEE_SECRET`) — credencial permanente, sem cookie.

## 4. Buscador do Mercado Livre

Duas fontes no mesmo módulo (`mercadolivre/buscador.py`, 994 linhas):

- **Vitrine `/ofertas`** — sem login, ~54 anúncios, tem badges (relâmpago/oferta do dia), pobre em marca.
- **Busca `lista.mercadolivre.com.br`** — exige cookie, centenas por termo, é o volume real.
  Parsing frágil por desenho: o estado não vem em JSON limpo, é recortado de dentro de
  uma string JS (`_n.ctx.s.q("0:{…}")`) com scanner de chaves balanceadas.

Parâmetros hoje fixos em código: `PAGINAS_MAX=100`, `PAGINAS_VAZIAS_ATE_PARAR=2`,
`PAUSA_ENTRE_PAGINAS=(1.0,2.5)`, `PAUSA_ENTRE_BUSCAS=(4.0,8.0)`, categoria por nicho.
Filtro de qualidade (o que decide se vira oferta): `nichos/*.py` — marcas permitidas,
blacklist, unidade mínima (ml), desconto mínimo, contratipo.
**Não existe "testar busca"**: a única prova prévia é `agente.py ml buscar --seco` no terminal.

## 5. Painel

Legado (`main`): 10 páginas planas, vocabulário técnico exposto.
Worktree redesign: shell novo, contexto de projeto por cookie, rotas
`/publicacoes /fontes /destinos /mensagens /ritmo /desempenho /configuracoes /ajuda`,
design system próprio, 23 decisões registradas (D1–D23), harness de verificação.
**Escopo daquela rodada foi frontend-only (D1): zero arquivo do motor alterado.**
Classificado como FUTURO e ainda não feito: QR do WhatsApp (D13), CRUD de projetos (D17),
multiusuário/assinatura/permissões, novas plataformas.

Autenticação: cookie HMAC de usuário único, credencial no ambiente (`lib/sessao.ts`).
Não há tabela de usuários.

## 6. Elementos que a auditoria marcou para revisão

- `/logs` lê tabela `logs` ou arquivo `LOG_PATH` — técnico, fora da navegação no redesign.
- `config.tracking` gravado por projeto embora seja conceitualmente do workspace (D7).
- `entregas.canal` guarda JID cru — nome do grupo só resolve chamando a API a cada render.
- `status_envio='ERRO'` acumula falha real e "ignorada pelo painel" no mesmo estado (D11/D22).
- Bug aberto e documentado (docs/MELHORIAS-PENDENTES.md): oferta adotada pelo clonador mantém
  `criado_em` antigo e morre na regra de 48h. **Pertence à workstream do Clonador — congelado aqui.**
