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
| testes do motor | `python3 -m unittest discover -s tests -t .` | — | — |

## Validação com dado real

| # | Cenário | Como foi verificado | Data | Resultado |
|---|---|---|---|---|
| — | *(nenhuma ainda — a fundação não produz comportamento observável)* | | | |

## Contratos externos verificados

| Verificação | Data | Resultado |
|---|---|---|
| `GET /instance/all` com admin token | 2026-08-26 | ✓ 200 — 2 instâncias: `bot de promoções` (produção), `Pessoal` (livre) |
| `GET /instance/status` com token de instância | 2026-08-26 | ✓ 200 |
| Mercado Livre publica API oficial de afiliados? | 2026-08-26 | ✗ não existe — sessão é o único caminho |
| Instância criada por API expira em 1 hora? | — | **pendente (T013)** — decide se o provisionamento automático fica em pé |
