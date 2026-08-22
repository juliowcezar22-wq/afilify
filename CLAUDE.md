# Afilify — regras do repositório

- **Linguagem de produto na UI**: nunca expor na experiência comum termos
  internos (worker, Uazapi, JID, Postgres/SQLite, deploy, restart, LOG_PATH,
  slugs como `perfumes-ml`, hora decimal). Identificador técnico só em
  "Detalhes técnicos". Verificador: `scripts/harness/check-linguagem.sh`.
- **Separação de conceitos**: projeto (perfil) ≠ automação ≠ conexão ≠
  destino ≠ fonte; oferta ≠ publicação. Ver
  `docs/product/AFILIFY_PRODUCT_ARCHITECTURE.md`.
- **Contratos do motor são intocáveis pelo painel**: chaves de `config`
  (`mensagem`, `headlines`, `ritmo`, `clonador`, `canal`, `tracking`),
  semântica de `status_envio`/`entregas`/`estado`. Conversões (ex.: hora
  decimal ↔ HH:MM) acontecem na borda da UI.
- **Não modificar o motor Python** em trabalho de painel/UX sem necessidade
  direta — registre exceções em `docs/product/AFILIFY_DECISIONS.md`.
- **Antes de concluir tarefa de painel**: `scripts/harness/fast-check.sh`;
  ao fechar milestone: `scripts/harness/verify-redesign.sh`. Manter
  `TASKS_AFILIFY_REDESIGN.md` e `PROGRESS_AFILIFY_REDESIGN.md` atualizados
  enquanto o redesign estiver ativo.
- Testes do motor: `python3 -m unittest discover -s tests -t .` (sempre em
  banco temporário — nunca apontar para banco real).
