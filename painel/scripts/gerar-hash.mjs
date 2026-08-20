// node scripts/gerar-hash.mjs "minha senha"  → cole em ADMIN_PASSWORD_HASH
import { scryptSync, randomBytes } from "node:crypto";
const senha = process.argv[2];
if (!senha) { console.error("uso: node scripts/gerar-hash.mjs \"senha\""); process.exit(1); }
const salt = randomBytes(16).toString("hex");
console.log(`${salt}:${scryptSync(senha, salt, 32).toString("hex")}`);
