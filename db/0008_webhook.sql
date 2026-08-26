-- 0008 — mensagens do rival chegando por webhook da uazapi
CREATE TABLE IF NOT EXISTS rival_mensagens (
    messageid   TEXT PRIMARY KEY,
    chatid      TEXT NOT NULL,
    texto       TEXT NOT NULL DEFAULT '',
    tipo        TEXT NOT NULL DEFAULT '',
    de_mim      INTEGER NOT NULL DEFAULT 0,
    ts_mensagem TEXT NOT NULL DEFAULT '',
    recebido_em TEXT NOT NULL,
    processado  INTEGER NOT NULL DEFAULT 0,
    bruto       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_rival_pendentes
    ON rival_mensagens(chatid, processado);
