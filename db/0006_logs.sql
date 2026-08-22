-- 0006 — logs do motor no banco (página Logs do painel na VPS)
CREATE TABLE IF NOT EXISTS logs (
    id     BIGSERIAL PRIMARY KEY,
    ts     TEXT NOT NULL,
    perfil TEXT NOT NULL DEFAULT '',
    nivel  TEXT NOT NULL,
    texto  TEXT NOT NULL
);
