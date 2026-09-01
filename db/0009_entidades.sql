-- Afilify · 0009 — entidades do núcleo SaaS
--
-- Workspace → Projeto → Automação → (Fonte, Destino) · Conexão no workspace
-- Especificação: specs/001-afilify-saas-core/data-model.md
--
-- DIALETO COMUM DE PROPÓSITO: este arquivo roda tal e qual no Postgres (via
-- psql) e no SQLite (via nucleo/comum.py), para não existirem duas versões do
-- schema que possam divergir. Por isso:
--   · chaves primárias TEXT, geradas pela aplicação — nada de BIGSERIAL
--   · datas TEXT ISO-8601, como no resto do projeto
--   · nenhum DEFAULT que dependa de função do banco
--   · DOUBLE PRECISION (o SQLite dá afinidade REAL a esse nome)

-- ── usuários ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id),
    email         TEXT NOT NULL,
    senha_hash    TEXT NOT NULL,
    nome          TEXT NOT NULL DEFAULT '',
    criado_em     TEXT NOT NULL,
    ultimo_acesso TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios (email);

-- ── conexões (contas externas do workspace) ───────────────────────────
CREATE TABLE IF NOT EXISTS conexoes (
    id                    TEXT PRIMARY KEY,
    workspace_id          TEXT NOT NULL REFERENCES workspaces(id),
    plataforma            TEXT NOT NULL
                          CHECK (plataforma IN ('whatsapp','mercadolivre','shopee')),
    nome                  TEXT NOT NULL,
    estado                TEXT NOT NULL DEFAULT 'criando'
                          CHECK (estado IN ('criando','gerando_codigo','codigo_disponivel',
                                            'aguardando_leitura','codigo_expirado','conectando',
                                            'conectado','desconectado','sessao_perdida',
                                            'precisa_reconectar','reconectando','erro')),
    identificador_externo TEXT NOT NULL DEFAULT '',
    credencial_cifrada    TEXT NOT NULL DEFAULT '',
    metadados             TEXT NOT NULL DEFAULT '{}',
    ultimo_estado_em      TEXT NOT NULL,
    ultima_atividade_em   TEXT,
    expira_em             TEXT,
    motivo_ultima_queda   TEXT NOT NULL DEFAULT '',
    criado_em             TEXT NOT NULL,
    atualizado_em         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conexoes_ws ON conexoes (workspace_id, plataforma);

-- Grupos de uma conexão de WhatsApp: cache para exibir por NOME sem chamar a
-- API a cada render (limitação registrada na auditoria).
CREATE TABLE IF NOT EXISTS grupos_conexao (
    conexao_id      TEXT NOT NULL REFERENCES conexoes(id),
    identificador   TEXT NOT NULL,
    nome            TEXT NOT NULL DEFAULT '',
    participantes   INTEGER NOT NULL DEFAULT 0,
    sincronizado_em TEXT NOT NULL,
    PRIMARY KEY (conexao_id, identificador)
);

-- ── tipos de nicho (curadoria versionada, não editável pelo usuário) ───
CREATE TABLE IF NOT EXISTS tipos_nicho (
    id        TEXT PRIMARY KEY,
    nome      TEXT NOT NULL,
    versao    INTEGER NOT NULL DEFAULT 1,
    curadoria TEXT NOT NULL DEFAULT '{}',
    criado_em TEXT NOT NULL
);

-- ── projetos ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projetos (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id),
    nome          TEXT NOT NULL,
    tipo_nicho_id TEXT REFERENCES tipos_nicho(id),
    estado        TEXT NOT NULL DEFAULT 'ativo'
                  CHECK (estado IN ('ativo','pausado','arquivado')),
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_projetos_nome ON projetos (workspace_id, nome);

-- ── automações ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS automacoes (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id),
    projeto_id      TEXT NOT NULL REFERENCES projetos(id),
    nome            TEXT NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'rascunho'
                    CHECK (estado IN ('rascunho','ativa','pausada','impedida')),
    motivo_impedida TEXT NOT NULL DEFAULT '',
    ritmo           TEXT NOT NULL DEFAULT '{}',
    mensagem        TEXT NOT NULL DEFAULT '{}',
    criado_em       TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_automacoes_projeto ON automacoes (projeto_id, estado);

-- ── fontes ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fontes (
    id                 TEXT PRIMARY KEY,
    workspace_id       TEXT NOT NULL REFERENCES workspaces(id),
    automacao_id       TEXT NOT NULL REFERENCES automacoes(id),
    tipo               TEXT NOT NULL CHECK (tipo IN ('busca','monitoramento')),
    conexao_id         TEXT REFERENCES conexoes(id),
    ativa              INTEGER NOT NULL DEFAULT 0,
    criterios          TEXT NOT NULL DEFAULT '{}',
    agenda             TEXT NOT NULL DEFAULT '{}',
    ultima_execucao_em TEXT,
    criado_em          TEXT NOT NULL,
    atualizado_em      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fontes_automacao ON fontes (automacao_id, ativa);

CREATE TABLE IF NOT EXISTS execucoes_fonte (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    fonte_id     TEXT NOT NULL REFERENCES fontes(id),
    iniciada_em  TEXT NOT NULL,
    terminada_em TEXT,
    resultado    TEXT NOT NULL DEFAULT 'ok'
                 CHECK (resultado IN ('ok','sem_novidades','falhou')),
    encontradas  INTEGER NOT NULL DEFAULT 0,
    novas        INTEGER NOT NULL DEFAULT 0,
    motivo       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_execucoes_fonte ON execucoes_fonte (fonte_id, iniciada_em);

-- ── destinos ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS destinos (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id),
    automacao_id  TEXT NOT NULL REFERENCES automacoes(id),
    conexao_id    TEXT NOT NULL REFERENCES conexoes(id),
    alvo          TEXT NOT NULL,
    nome          TEXT NOT NULL DEFAULT '',
    ordem         INTEGER NOT NULL DEFAULT 0,
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_destinos_alvo ON destinos (automacao_id, alvo);

-- ── comandos (painel → motor) ─────────────────────────────────────────
-- Em produção painel e worker são contêineres separados que só compartilham
-- o banco. Esta tabela é o canal de pedido/resposta entre os dois.
CREATE TABLE IF NOT EXISTS comandos (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id),
    tipo          TEXT NOT NULL
                  CHECK (tipo IN ('testar_busca','conectar_whatsapp','sincronizar_grupos',
                                  'publicar_agora','validar_conexao_ml')),
    parametros    TEXT NOT NULL DEFAULT '{}',
    estado        TEXT NOT NULL DEFAULT 'pendente'
                  CHECK (estado IN ('pendente','executando','concluido','falhou','expirado')),
    resultado     TEXT NOT NULL DEFAULT '{}',
    erro          TEXT NOT NULL DEFAULT '',
    expira_em     TEXT NOT NULL,
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comandos_fila ON comandos (estado, criado_em);

-- ── limites de plano ──────────────────────────────────────────────────
-- Existe desde já para que abrir a plataforma a clientes seja configuração,
-- nunca migração de dados (D27).
CREATE TABLE IF NOT EXISTS limites_plano (
    workspace_id             TEXT PRIMARY KEY REFERENCES workspaces(id),
    max_conexoes             INTEGER NOT NULL DEFAULT 5,
    max_projetos             INTEGER NOT NULL DEFAULT 10,
    max_automacoes           INTEGER NOT NULL DEFAULT 20,
    max_publicacoes_dia      INTEGER NOT NULL DEFAULT 500,
    max_testes_busca_dia     INTEGER NOT NULL DEFAULT 50,
    teto_envios_conexao_hora INTEGER NOT NULL DEFAULT 40,
    atualizado_em            TEXT NOT NULL
);
