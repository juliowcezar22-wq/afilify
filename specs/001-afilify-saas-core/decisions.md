# Decisões — núcleo SaaS da Afilify

Continuação da numeração do redesign anterior (D1–D23 em `docs/product/AFILIFY_DECISIONS.md`).
Formato: data · decisão · motivo · reversibilidade.

## 2026-08-26 · D24 — Projeto → N Automações → N Destinos
Um Projeto agrupa várias Automações; cada Automação publica em vários Destinos. Fontes,
mensagem e ritmo pertencem à Automação. Supera a D3 do redesign anterior ("automação implícita,
1 por projeto"), que era limitação do modelo antigo e não decisão de produto.
Reversível: não sem migração de dados — por isso foi decidida antes do schema.

## 2026-08-26 · D25 — Uma instância dedicada por conexão de WhatsApp
A Afilify cria a instância no provedor quando o usuário adiciona a conexão. Isolamento total:
queda ou bloqueio de uma conexão não afeta outra. Número de conexões simultâneas vira limite
de plano.
**Contrato confirmado** (`uazapi-openapi-spec.yaml`): `POST /instance/create` exige header
`admintoken`; devolve `token` da instância. `POST /instance/connect` sem `phone` devolve
`qrcode` em base64 (validade 2 min); com `phone` devolve `paircode` (5 min). Estados reais:
`disconnected`, `connecting`, `connected`, `hibernated`.
**Admin token confirmado em 2026-08-26**: `GET /instance/all` responde 200 e lista as instâncias
da conta. O provisionamento automático é viável — D25 fica como caminho principal.
**Risco que permanece**: a resposta de criação pode trazer `info: "This instance will be
automatically disconnected and deleted after 1 hour"` — comportamento de instância sem plano.
A confirmar criando uma instância descartável na primeira tarefa de conexão.

## 2026-08-26 · D25b — Conexão sobre instância existente continua suportada
Deixou de ser fallback de indisponibilidade e virou capacidade permanente: a conexão aceita tanto
provisionar uma instância nova quanto adotar uma que já existe. Serve à validação (D33) e protege
contra perda de acesso administrativo. Reversível: total.

## 2026-08-26 · D26 — Extensão de navegador é o destino do Mercado Livre, e não é desta rodada
Verificado que o Mercado Livre não publica API oficial de afiliados; o `createLink` usado hoje é
endpoint interno autenticado por sessão. A solução final é uma extensão que captura e renova a
sessão do próprio usuário. **Nenhuma solução intermediária de conexão assistida será construída**
— nesta rodada a sessão continua sendo renovada fora da Afilify, e a plataforma apenas mostra o
estado real, avisa com antecedência e retém as ofertas afetadas.
Reversível: sim (a extensão entra depois no mesmo ponto de integração).

## 2026-08-26 · D27 — Um workspace agora, modelo pronto para muitos
Esta rodada atende apenas a operação do dono. Cadastro público, permissões, planos e cobrança
ficam fora. Mas chave de workspace, isolamento e limites nascem no modelo, para que abrir a
plataforma depois seja interface e configuração — nunca migração de dados.

## 2026-08-26 · D28 — Fonte: quatro controles no fluxo comum
Palavras-chave · onde buscar (busca e/ou página de ofertas, combináveis) · desconto mínimo ·
faixa de preço. Exclusões (palavras e marcas) em Avançado recolhido. Nada de concorrência,
timeout, contagem de requisições, pausas, proxy, tentativas ou paginação técnica.
Reversível: total.

## 2026-08-26 · D29 — Qualidade em duas barreiras independentes
(a) **Tipo de nicho** escolhido ao criar o Projeto traz a curadoria pronta (marcas aceitas,
palavras proibidas, unidade mínima) — é o que hoje vive em `nichos/*.py` e protege o grupo de
falsificação e paralela; (b) **sinais automáticos do anúncio** (loja oficial, reputação,
avaliação, coerência de preço) como segunda barreira. O usuário não configura marcas.
Custo aceito: algumas ofertas legítimas são derrubadas por passarem em só uma das barreiras.

## 2026-08-26 · D30 — Destinos recebem a mesma oferta, com intervalo entre eles
Mesma oferta e mesma mensagem em todos os Destinos da Automação; cada envio é uma Publicação
com resultado próprio. A Afilify aplica um intervalo entre os envios aos diferentes destinos
para proteger a saúde dos números. O intervalo é decisão da plataforma, não campo de formulário.
Reversível: sim (ritmo e mensagem por destino podem ser adicionados sem migração).

## 2026-08-26 · D31 — Repetição por queda de preço; monitoramento isento
Uma Oferta já publicada volta à fila daquele Destino apenas se o preço cair abaixo do preço da
publicação anterior. Publicações originadas de monitoramento de grupos **não** são bloqueadas
pela regra: quando o monitoramento identifica a oportunidade, publica — mesmo que a oferta
tenha saído recentemente.
Dependência: o Clonador está congelado nesta rodada; a regra é implementada do lado da fila.

## 2026-08-26 · D32 — Teto de segurança por conexão
Cada número conectado tem um teto de volume decidido pela Afilify, acima do ritmo somado das
automações que o utilizam. Invisível como configuração; visível como motivo quando segurar uma
publicação. A API do provedor oferece apoio real: `GET /instance/wa_messages_limits` diagnostica
limites de novas conversas, e `POST /instance/updateDelaySettings` controla espaçamento nativo.

## 2026-08-26 · D33 — Validação na worktree, com grupo de teste e o número da operação
Tudo é construído na worktree `feat/afilify-saas-redesign` e validado com publicações reais em
um grupo de teste, usando a conexão de WhatsApp que já existe. `POST /group/create` permite que
o próprio grupo de teste seja criado pela plataforma nova. Merge só após QA humano do dono,
olhando os disparos no grupo. Sem push, deploy ou alteração de `main`.
**Refinado em 2026-08-26 após inspeção da conta**: existem duas instâncias — `bot de promoções`
(connected, perfil "Achei Barato", produção) e `Pessoal` (disconnected, perfil "Júlio César - B2C").
O fluxo de conexão — QR, conectado, queda, reconexão, sincronização de grupos — é validado na
instância `Pessoal`, que está livre. Publicação, ritmo, destinos, teto de segurança e buscador são
validados pela instância de produção publicando em **grupo de teste**, nunca no grupo real.
A instância de produção nunca é reconectada nem tem sua sessão exercitada.

## 2026-08-26 · D34 — Sem cutover nesta rodada
A operação viva não migra agora. A migração do projeto de perfumes para o novo modelo — com
ofertas, publicações, configuração e histórico preservados — é trabalho posterior, especificado
depois da validação manual e do merge.

## 2026-08-26 · D35 — Banco de validação separado do banco de produção
Decorre de D33 e de incidente anterior registrado no projeto: a worktree nunca aponta para o
banco da operação. A validação usa banco próprio, semeado com cópia dos dados reais quando
precisar de fidelidade. Publicações de teste vão para o grupo de teste, nunca para o grupo real.
