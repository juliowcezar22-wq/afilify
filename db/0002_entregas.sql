-- Afilify · 0002 — entregas (idempotência de publicação, blueprint Parte 8)
CREATE TABLE IF NOT EXISTS entregas (
    mlb_id        TEXT NOT NULL,
    canal         TEXT NOT NULL,
    perfil        TEXT NOT NULL DEFAULT 'perfumes-ml',
    status        TEXT NOT NULL DEFAULT 'enviando'
                  CHECK (status IN ('enviando','enviada','falhou')),
    tentativa     INTEGER NOT NULL DEFAULT 1,
    id_externo    TEXT NOT NULL DEFAULT '',
    erro          TEXT NOT NULL DEFAULT '',
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY (mlb_id, canal)
);
CREATE INDEX IF NOT EXISTS idx_entregas_status ON entregas (perfil, status);
