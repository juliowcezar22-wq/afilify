-- Afilify · 0010 — Oferta e Publicação sob o modelo novo
--
-- Duas mudanças estruturais que o modelo antigo não comportava:
--
-- 1. IDENTIDADE DA OFERTA POR PROJETO. Antes, `ofertas.mlb_id` era chave
--    primária global: dois projetos que encontrassem o mesmo produto
--    colidiriam na mesma linha, e o segundo sobrescreveria o estado do
--    primeiro em silêncio.
--
-- 2. PUBLICAÇÃO COM IDENTIDADE PRÓPRIA. Antes, `entregas` tinha chave
--    (mlb_id, canal) — o que impedia tanto publicar a mesma oferta em dois
--    destinos quanto republicá-la após queda de preço. A proteção contra
--    envio duplicado que aquela chave dava de graça é preservada pela
--    chave de idempotência, que inclui o ciclo.
--
-- Dialeto comum a SQLite e Postgres (ver cabeçalho de 0009).
-- As tabelas antigas continuam intactas: a operação viva não migra nesta
-- rodada (D34), e o corte será especificado depois da validação.

CREATE TABLE IF NOT EXISTS ofertas_projeto (
    id                    TEXT PRIMARY KEY,
    workspace_id          TEXT NOT NULL REFERENCES workspaces(id),
    projeto_id            TEXT NOT NULL REFERENCES projetos(id),
    fonte_id              TEXT REFERENCES fontes(id),

    identificador_anuncio TEXT NOT NULL,
    nome                  TEXT NOT NULL,
    url                   TEXT NOT NULL,
    imagem                TEXT NOT NULL DEFAULT '',
    titulo_norm           TEXT NOT NULL DEFAULT '',

    preco_original        DOUBLE PRECISION,
    preco_promocional     DOUBLE PRECISION,
    desconto_pct          INTEGER,

    marca                 TEXT NOT NULL DEFAULT '',
    familia               TEXT NOT NULL DEFAULT '',
    condicao              TEXT NOT NULL DEFAULT '',
    badge                 TEXT NOT NULL DEFAULT '',

    -- sinais que alimentam a segunda barreira de qualidade (D29)
    loja                  TEXT NOT NULL DEFAULT '',
    loja_oficial          INTEGER NOT NULL DEFAULT 0,
    vendedor              TEXT NOT NULL DEFAULT '',
    avaliacao             DOUBLE PRECISION NOT NULL DEFAULT 0,
    vendidos              TEXT NOT NULL DEFAULT '',

    link_afiliado         TEXT NOT NULL DEFAULT '',
    codigo                TEXT NOT NULL DEFAULT '',
    origem                TEXT NOT NULL DEFAULT 'busca'
                          CHECK (origem IN ('busca','monitoramento')),

    -- `retida` é o estado que garante não perder oferta por falha de
    -- conexão ou de link: ela espera e volta sozinha (FR-042).
    estado                TEXT NOT NULL DEFAULT 'nova'
                          CHECK (estado IN ('nova','pronta','retida','publicada',
                                            'ignorada','expirada')),
    motivo_retencao       TEXT NOT NULL DEFAULT '',
    validade_ate          TEXT,

    criado_em             TEXT NOT NULL,
    atualizado_em         TEXT NOT NULL
);

-- A mesma oferta pode existir em projetos diferentes, sem interferência.
CREATE UNIQUE INDEX IF NOT EXISTS idx_oferta_por_projeto
    ON ofertas_projeto (projeto_id, identificador_anuncio);
-- Deduplicação secundária: anúncios distintos do mesmo produto.
CREATE INDEX IF NOT EXISTS idx_oferta_titulo   ON ofertas_projeto (projeto_id, titulo_norm);
CREATE INDEX IF NOT EXISTS idx_oferta_estado   ON ofertas_projeto (projeto_id, estado);
CREATE INDEX IF NOT EXISTS idx_oferta_criado   ON ofertas_projeto (projeto_id, criado_em);
CREATE UNIQUE INDEX IF NOT EXISTS idx_oferta_codigo
    ON ofertas_projeto (codigo) WHERE codigo <> '';

CREATE TABLE IF NOT EXISTS publicacoes (
    id                  TEXT PRIMARY KEY,
    workspace_id        TEXT NOT NULL REFERENCES workspaces(id),
    projeto_id          TEXT NOT NULL REFERENCES projetos(id),
    automacao_id        TEXT NOT NULL REFERENCES automacoes(id),
    oferta_id           TEXT NOT NULL REFERENCES ofertas_projeto(id),
    destino_id          TEXT NOT NULL REFERENCES destinos(id),

    estado              TEXT NOT NULL DEFAULT 'agendada'
                        CHECK (estado IN ('agendada','enviando','enviada','falhou','cancelada')),
    tentativa           INTEGER NOT NULL DEFAULT 1,

    -- (oferta, destino, ciclo). O ciclo sobe quando a oferta volta à fila
    -- por queda de preço (D31) — é o que permite republicar sem abrir
    -- brecha para envio duplicado.
    ciclo               INTEGER NOT NULL DEFAULT 1,
    chave_idempotencia  TEXT NOT NULL,

    preco_publicado     DOUBLE PRECISION,
    mensagem_enviada    TEXT NOT NULL DEFAULT '',
    id_externo          TEXT NOT NULL DEFAULT '',
    motivo_falha        TEXT NOT NULL DEFAULT '',

    agendada_para       TEXT,
    enviada_em          TEXT,
    criado_em           TEXT NOT NULL,
    atualizado_em       TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_publicacao_unica
    ON publicacoes (chave_idempotencia);
CREATE INDEX IF NOT EXISTS idx_publicacao_fila
    ON publicacoes (automacao_id, estado, agendada_para);
CREATE INDEX IF NOT EXISTS idx_publicacao_oferta   ON publicacoes (oferta_id);
CREATE INDEX IF NOT EXISTS idx_publicacao_destino  ON publicacoes (destino_id, enviada_em);
