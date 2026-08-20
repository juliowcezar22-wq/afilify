-- Afilify · 0001 — schema operacional no Postgres
-- Espelho FIEL das tabelas do SQLite em produção (cutover sem mudança de
-- comportamento) + workspace desde o dia 1 (princípio do blueprint).
-- Datas como TEXT ISO-8601 de propósito: comparação de string funciona igual
-- nos dois dialetos e o cutover não muda semântica. Tipos nativos vêm com o
-- modelo completo do painel.

CREATE TABLE IF NOT EXISTS workspaces (
    id         TEXT PRIMARY KEY,
    nome       TEXT NOT NULL,
    criado_em  TEXT NOT NULL
);
INSERT INTO workspaces (id, nome, criado_em)
    VALUES ('ws-afilify', 'Operação Afilify', '2026-08-20T00:00:00-03:00')
    ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS ofertas (
    mlb_id            TEXT PRIMARY KEY,
    workspace_id      TEXT NOT NULL DEFAULT 'ws-afilify' REFERENCES workspaces(id),
    perfil            TEXT NOT NULL DEFAULT 'perfumes-ml',
    nome              TEXT NOT NULL,
    url               TEXT NOT NULL,
    imagem            TEXT NOT NULL DEFAULT '',
    preco_original    DOUBLE PRECISION,
    preco_promocional DOUBLE PRECISION,
    desconto_pct      INTEGER,
    badge             TEXT NOT NULL DEFAULT 'PROMOÇÃO GERAL',
    condicao          TEXT NOT NULL DEFAULT '',
    marca             TEXT NOT NULL DEFAULT '',
    familia           TEXT NOT NULL DEFAULT '',
    titulo_norm       TEXT NOT NULL DEFAULT '',
    vendedor          TEXT NOT NULL DEFAULT '',
    loja              TEXT NOT NULL DEFAULT '',
    loja_oficial      INTEGER NOT NULL DEFAULT 0,
    avaliacao         DOUBLE PRECISION NOT NULL DEFAULT 0,
    vendidos          TEXT NOT NULL DEFAULT '',
    link_afiliado     TEXT NOT NULL DEFAULT '',
    origem            TEXT NOT NULL DEFAULT 'busca',
    rival_nome        TEXT NOT NULL DEFAULT '',
    rival_preco       DOUBLE PRECISION,
    rival_link        TEXT NOT NULL DEFAULT '',
    status_envio      TEXT NOT NULL DEFAULT 'PENDENTE'
                      CHECK (status_envio IN ('PENDENTE','ENVIADO','ERRO')),
    erro              TEXT NOT NULL DEFAULT '',
    tentativas        INTEGER NOT NULL DEFAULT 0,
    proxima_tentativa TEXT,
    criado_em         TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL,
    enviado_em        TEXT
);
CREATE INDEX IF NOT EXISTS idx_ofertas_status  ON ofertas (perfil, status_envio);
CREATE INDEX IF NOT EXISTS idx_ofertas_titulo  ON ofertas (perfil, titulo_norm);
CREATE INDEX IF NOT EXISTS idx_ofertas_criado  ON ofertas (criado_em);
CREATE INDEX IF NOT EXISTS idx_ofertas_enviado ON ofertas (perfil, enviado_em);

CREATE TABLE IF NOT EXISTS estado (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
