# Afilify — Decisões e Assumptions do redesign

Formato: data · decisão · motivo · reversibilidade.

## 2026-08-22 · D1 — Escopo frontend-only
O redesign acontece inteiro em `painel/` (+ docs + harness). Nenhum arquivo
do motor (`nucleo/`, `mercadolivre/`, `shopee/`, `perfis/`, `nichos/`,
`runner.py`, `agente.py`, `db/`, `tests/`) é modificado — há workstream
paralela dedicada aos agentes. Reversível: total.

## 2026-08-22 · D2 — "Projeto" = perfil existente
A UI chama `perfil` de **projeto**. O mapeamento slug → nome amigável fica
em `painel/lib/projetos.ts` (`perfumes-ml` → "Perfumes", `casa-ml-shopee` →
"Casa"), com humanização automática de slugs desconhecidos (novo perfil
nunca quebra a UI). Não há tabela nova; quando o SaaS tiver cadastro de
projetos, o mapa vira consulta. Reversível: total.

## 2026-08-22 · D3 — Automação implícita (1 por projeto)
Hoje cada projeto tem exatamente uma automação (o daemon do perfil). A UI
não cria a entidade "Automação" separada; as seções Fontes/Destinos/
Mensagens/Ritmo já são os aspectos dela. Criar CRUD de automações agora
seria inventar produto. Reversível: sim (as rotas são por aspecto, não por
automação).

## 2026-08-22 · D4 — Oferta vs Publicação sem mudar o schema
Publicações = leitura combinada de `ofertas.status_envio` + `entregas` +
`estado` (plano do dia). Nenhuma tabela nova. A separação é conceitual/de
apresentação. Reversível: total.

## 2026-08-22 · D5 — Rotas novas + redirects permanentes
`/fila→/publicacoes`, `/canais→/destinos`, `/copiador→/fontes`,
`/templates→/mensagens`, `/analytics→/desempenho`, `/config→/ritmo`.
Redirects via `next.config.ts`. `/logs` continua existindo mas sai da
navegação. Motivo: URLs viram vocabulário do produto. Reversível: sim.

## 2026-08-22 · D6 — Hora decimal permanece no contrato
O motor lê `inicio_janela`/`fim_janela` como hora decimal. A UI edita em
HH:MM e converte na borda (passo de 15 min = 0.25). O valor gravado
continua decimal — zero mudança de contrato. Reversível: total.

## 2026-08-22 · D7 — Tracking de cliques vai para Configurações (conta)
É armazenado por perfil (contrato do motor), mas conceitualmente é
configuração de infraestrutura do workspace (URL pública). A página
Configurações grava a mesma chave `tracking` por projeto, com a URL base
compartilhada na edição (aplicada a todos os projetos ao salvar).
Assumption: na prática só há uma base pública. Reversível: sim.

## 2026-08-22 · D8 — Edição estruturada de mensagens, template em Avançado
O fluxo comum edita: rodapé, linha da loja e a biblioteca de chamadas
(headlines por categoria, item a item). O template `base` (com `{tokens}`)
só aparece em "Modo avançado" colapsado — parsear o template em blocos
estruturados seria frágil e arriscaria mensagem quebrada no grupo. As
validações da API continuam as mesmas. Reversível: total.

## 2026-08-22 · D9 — Nomes das categorias de headline
Pools internos ganham rótulos humanos fixos na UI: `relampago`→"Relâmpago",
`oferta_do_dia`→"Oferta do dia", `desconto_alto`→"Desconto alto",
`desconto_medio`→"Desconto médio", `mais_vendido`→"Mais vendido",
`geral`→"Geral". Pools desconhecidos: humanização automática. As chaves
gravadas não mudam. Reversível: total.

## 2026-08-22 · D10 — Saúde percebida sem a palavra "worker"
Dashboard deriva o estado da automação do heartbeat (`estado` table) +
ofertas em ERRO: "Funcionando normalmente" / "Sem sinal da automação" /
"N publicações precisam de atenção". O detalhe por projeto existe, o termo
worker não. Reversível: total.

## 2026-08-22 · D11 — "Precisa de atenção" = status ERRO
`status_envio='ERRO'` inclui tanto falha real quanto "ignorada pelo
painel". A UI distingue pelo campo `erro`: itens ignorados aparecem como
"Ignorada" (neutro), o resto como "Precisa de atenção". Nenhuma semântica
de banco alterada. Reversível: total.

## 2026-08-22 · D12 — Frequência do monitoramento vira preset
`intervalo_seg` (mín. 60) é editado como seleção "Frequência de
monitoramento": Muito frequente (60s) / Frequente (180s, padrão) /
Econômica (600s). `janela_min` vira "Ignorar mensagens antigas" com
presets equivalentes. Valores fora dos presets são exibidos como
"Personalizada (Ns)" e preservados se não tocados. Reversível: total.

## 2026-08-22 · D13 — Sem QR code de conexão nesta fase
O fluxo de conectar WhatsApp por QR dentro do painel depende de endpoints
Uazapi (`/instance/connect` etc.) não usados/confirmados no código atual.
Para não simular sucesso falso, Conexões mostra estados reais e orientação;
o fluxo QR fica classificado como FUTURO. Reversível: sim.

## 2026-08-22 · D14 — Harness dentro do worktree
Hooks em `.claude/settings.json` do repositório (branch do redesign) +
scripts em `scripts/harness/`. Ao fazer merge, o time decide se mantém.

## 2026-08-22 · D15 — Baseline de qualidade herdado
Antes do redesign: `pnpm build` OK; `pnpm lint` com 5 erros pré-existentes
(páginas antigas, todas reescritas neste trabalho); `tsc --noEmit` exige
`next typegen` antes (tipos gerados `LayoutProps`). O harness usa
`next typegen && tsc --noEmit`. Testes Python (84) não são tocados e devem
continuar passando (nenhum arquivo do motor muda).

## 2026-08-22 · D16 — Grupos do WhatsApp com conexão indisponível
Sem `UAZAPI_URL`/`UAZAPI_TOKEN` no ambiente do painel, a lista de grupos
vem vazia. Destinos/Fontes mostram empty state honesto ("Conecte seu
WhatsApp para listar os grupos") + o destino já configurado (JID) com
nome mascarado "Grupo …NNNN" quando o nome não é resolvível. Reversível:
total.
