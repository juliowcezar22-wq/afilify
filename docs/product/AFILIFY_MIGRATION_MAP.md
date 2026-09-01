# Afilify — Mapa de migração (telas antigas → novas)

| Antiga (rota) | Nova (rota) | Redirect | Dados/endpoints (inalterados) |
|---|---|---|---|
| Dashboard `/` | Dashboard `/` | — | `ofertas` (contagens), `estado` (heartbeat), últimas enviadas |
| Ofertas `/ofertas` | Ofertas `/ofertas` | — | `ofertas` + `POST /api/ofertas/[id]` |
| Fila de publicação `/fila` | Publicações `/publicacoes` | 308 | `estado` (plano_do_dia, proximo_envio), `ofertas` PENDENTE/retry, `entregas` |
| Grupos & canais `/canais` | Destinos `/destinos` | 308 | `config.canal`, Uazapi `/group/list`, `entregas` (hoje) |
| Copiador `/copiador` | Fontes `/fontes` | 308 | `config.clonador`, `config.ritmo` (busca_horas), Uazapi `/group/list`, `ofertas origem='clone'` |
| Templates & headlines `/templates` | Mensagens `/mensagens` | 308 | `config.mensagem`, `config.headlines`, amostra de `ofertas` |
| Conexões `/conexoes` | Conexões `/conexoes` | — | `ML_COOKIE_PATH` stat, Uazapi `/instance/status`, `SHOPEE_*` env |
| Analytics `/analytics` | Desempenho `/desempenho` | 308 | `ofertas` agregadas, `cliques` |
| Logs `/logs` | `/logs` (fora da navegação) | — | tabela `logs` / `LOG_PATH` |
| Configurações `/config` | Ritmo & Regras `/ritmo` (por projeto) + Configurações `/configuracoes` (tracking, conta) | 308 → `/ritmo` | `config.ritmo`, `config.tracking` |
| — | Ajuda `/ajuda` (nova) | — | estático |
| Login `/login` | `/login` | — | `POST /api/login` |

## Componentes/arquivos novos

- `painel/components/shell/` — Sidebar, NavMovel (drawer), SeletorProjeto,
  Topbar.
- `painel/components/ui/` — Botao, Cartao, Selo (badge), EstadoVazio,
  CabecalhoPagina, Indicador (stat), Paginacao, DetalhesTecnicos, Icone,
  SemDados, e a classe `CONTROLE` (inputs/selects com label próprio).
- `painel/lib/projetos.ts` — nomes amigáveis, cookie de projeto ativo.
- `painel/lib/formatos.ts` — datas pt-BR relativas, moeda, hora decimal↔HH:MM,
  rótulos de status/origem.
- `painel/app/api/projeto/route.ts` — grava cookie do projeto ativo (novo,
  só cookie; nenhuma escrita no banco).

## APIs / contratos

Nenhum endpoint alterado ou removido. Um endpoint novo (cookie de projeto).
Validações de `/api/config` inalteradas. SQL continua nos Server Components
(mesmo padrão do código atual).
