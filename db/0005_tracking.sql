-- 0005 — tracking de cliques (/r/{codigo} no painel)
ALTER TABLE ofertas ADD COLUMN IF NOT EXISTS codigo TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_ofertas_codigo
    ON ofertas(codigo) WHERE codigo <> '';

CREATE TABLE IF NOT EXISTS cliques (
    id     BIGSERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    quando TEXT NOT NULL,
    agente TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_cliques_codigo ON cliques(codigo);
