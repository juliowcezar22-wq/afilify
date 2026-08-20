-- Afilify · 0003 — preço da época do envio (re-promoção, blueprint §10)
ALTER TABLE ofertas ADD COLUMN IF NOT EXISTS preco_enviado DOUBLE PRECISION;
