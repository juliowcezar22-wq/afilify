# Validação — evidências

Cada linha registra **o que foi verificado com dado real**, não o que foi implementado.
Sem evidência aqui, a tarefa correspondente não pode ser marcada concluída.

Ambiente de validação: banco próprio, nunca o `afilify-db` de produção (D35).
WhatsApp: fluxo de conexão na instância `Pessoal`; publicação em **grupo de teste** pela
instância de produção, nunca no grupo real (D33).

---

## Gates automáticos

| Gate | Comando | Última execução | Resultado |
|---|---|---|---|
| lint + typecheck | `scripts/harness/fast-check.sh` | — | — |
| build | incluso em `verify-nucleo.sh` | — | — |
| linguagem de produto | `scripts/harness/check-linguagem.sh` | 2026-08-27 | ✓ |
| anti-mock | `scripts/harness/check-mock.sh` | 2026-08-27 | ✓ (e falha comprovada) |
| congelados | `scripts/harness/guarda-congelados.sh` | 2026-08-27 | ✓ (e falha comprovada) |
| banco de validação | `scripts/harness/guarda-banco.sh` | 2026-08-27 | ✓ (e bloqueio comprovado) |
| testes do motor | `python3 -m unittest discover -s tests -t .` | 2026-08-27 | ✓ 111 testes |

## Validação com dado real

| # | Cenário | Como foi verificado | Data | Resultado |
|---|---|---|---|---|
| 1 | Entidades novas nascem em banco limpo sem quebrar as antigas | `abrir_banco()` em banco temporário: 19 tabelas, workspace padrão semeado, 87 testes herdados passando | 2026-08-27 | ✓ |
| 2 | Curadoria de qualidade sobrevive à travessia para dado | Semeado dos nichos reais: 157 marcas de perfumes em 4 famílias, 31 palavras proibidas, contratipo com famílias permitidas | 2026-08-27 | ✓ |
| 3 | Credencial cifrada não abre com chave trocada nem adulterada | 13 testes de `nucleo/cripto.py` com a biblioteca real | 2026-08-27 | ✓ |

## Contratos externos verificados

| Verificação | Data | Resultado |
|---|---|---|
| `GET /instance/all` com admin token | 2026-08-26 | ✓ 200 — 2 instâncias: `bot de promoções` (produção), `Pessoal` (livre) |
| `GET /instance/status` com token de instância | 2026-08-26 | ✓ 200 |
| Mercado Livre publica API oficial de afiliados? | 2026-08-26 | ✗ não existe — sessão é o único caminho |
| Instância criada por API expira em 1 hora? | — | **pendente (T013)** — decide se o provisionamento automático fica em pé |
| DDL de `db/0009` roda no Postgres real | — | **pendente** — exercitado só no SQLite (sem servidor local); entra no fechamento (T064) |
