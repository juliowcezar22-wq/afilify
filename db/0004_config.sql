-- Afilify · 0004 — config dinâmica por perfil (Fase 5: painel edita, motor obedece)
CREATE TABLE IF NOT EXISTS config (
    perfil        TEXT NOT NULL,
    chave         TEXT NOT NULL,
    valor         TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY (perfil, chave)
);
