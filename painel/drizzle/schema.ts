/**
 * Espelho do schema operacional (db/0001_init.sql). O dono do DDL nesta fase
 * ainda é o SQL puro do motor; o Drizzle lê. Quando o modelo completo do
 * painel chegar (projects/channels/deliveries), o drizzle-kit assume as
 * migrations novas.
 */
import { pgTable, text, integer, doublePrecision } from "drizzle-orm/pg-core";

export const workspaces = pgTable("workspaces", {
  id: text("id").primaryKey(),
  nome: text("nome").notNull(),
  criadoEm: text("criado_em").notNull(),
});

export const ofertas = pgTable("ofertas", {
  mlbId: text("mlb_id").primaryKey(),
  workspaceId: text("workspace_id").notNull().default("ws-afilify"),
  perfil: text("perfil").notNull().default("perfumes-ml"),
  nome: text("nome").notNull(),
  url: text("url").notNull(),
  imagem: text("imagem").notNull().default(""),
  precoOriginal: doublePrecision("preco_original"),
  precoPromocional: doublePrecision("preco_promocional"),
  descontoPct: integer("desconto_pct"),
  badge: text("badge").notNull().default("PROMOÇÃO GERAL"),
  condicao: text("condicao").notNull().default(""),
  marca: text("marca").notNull().default(""),
  familia: text("familia").notNull().default(""),
  tituloNorm: text("titulo_norm").notNull().default(""),
  vendedor: text("vendedor").notNull().default(""),
  loja: text("loja").notNull().default(""),
  lojaOficial: integer("loja_oficial").notNull().default(0),
  avaliacao: doublePrecision("avaliacao").notNull().default(0),
  vendidos: text("vendidos").notNull().default(""),
  linkAfiliado: text("link_afiliado").notNull().default(""),
  origem: text("origem").notNull().default("busca"),
  rivalNome: text("rival_nome").notNull().default(""),
  rivalPreco: doublePrecision("rival_preco"),
  rivalLink: text("rival_link").notNull().default(""),
  statusEnvio: text("status_envio").notNull().default("PENDENTE"),
  erro: text("erro").notNull().default(""),
  tentativas: integer("tentativas").notNull().default(0),
  proximaTentativa: text("proxima_tentativa"),
  criadoEm: text("criado_em").notNull(),
  atualizadoEm: text("atualizado_em").notNull(),
  enviadoEm: text("enviado_em"),
  precoEnviado: doublePrecision("preco_enviado"),
});

export const estado = pgTable("estado", {
  chave: text("chave").primaryKey(),
  valor: text("valor").notNull(),
});

export const config = pgTable("config", {
  perfil: text("perfil").notNull(),
  chave: text("chave").notNull(),
  valor: text("valor").notNull(),
  atualizadoEm: text("atualizado_em").notNull(),
});
