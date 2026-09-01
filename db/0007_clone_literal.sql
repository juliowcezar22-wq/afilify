-- 0007 — clone literal: mensagem e foto exatas do rival
ALTER TABLE ofertas ADD COLUMN IF NOT EXISTS clone_texto  TEXT NOT NULL DEFAULT '';
ALTER TABLE ofertas ADD COLUMN IF NOT EXISTS clone_imagem TEXT NOT NULL DEFAULT '';
