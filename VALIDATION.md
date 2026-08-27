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
| lint + typecheck + testes do painel | `scripts/harness/fast-check.sh` | 2026-08-27 | ✓ 8 testes |
| build | incluso em `verify-nucleo.sh` | 2026-08-27 | ✓ 6 rotas de conexão publicadas |
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
| 4 | Motor e painel leem a credencial um do outro | Cifrado no Python e lido no Node, e vice-versa; contexto errado recusa abrir | 2026-08-27 | ✓ |
| 5 | Conexão criada guarda a credencial cifrada | Banco de validação: coluna com `v1.…`, 90 caracteres, nada em claro | 2026-08-27 | ✓ |
| 6 | QR real é gerado pela plataforma | `POST /api/conexoes/:id/conectar` → imagem de 1842 caracteres, validade de 2 min | 2026-08-27 | ✓ |
| 7 | Código vence e a tela deixa de esperar | Relógio avançado além da validade: `aguardando_leitura` → `codigo_expirado`, e não volta atrás | 2026-08-27 | ✓ |
| 8 | Gerar novo código depois de expirar | `codigo_expirado` → `aguardando_leitura` com código novo | 2026-08-27 | ✓ |
| 9 | Sincronizar grupos sem conexão explica o que fazer | "Conecte esta conta antes de sincronizar os grupos." | 2026-08-27 | ✓ |
| 10 | Remover conexão adotada NÃO destrói a conta do usuário | Conexão criada adotando `Pessoal`, removida; instância continua na conta | 2026-08-27 | ✓ (após correção) |
| 11 | Usuário escaneia o QR e a conta conecta | Feito pelo dono em 27/08: instância `Teste` criada pela Afilify e pareada; aparece no painel do provedor como `connected`, perfil "Júlio César - B2C" | 2026-08-27 | ✓ |
| 18 | Projeto e automação criados pela tela, sem arquivo | Projeto "Perfumes" → automação → ligada; supervisor listou "Perfumes · Ofertas Mercado Livre" | 2026-08-27 | ✓ |
| 19 | Automação não liga pela metade | Sem fonte/destino: 2 pendências; conexão caída: "conectar Principal — ela está desconectada" | 2026-08-27 | ✓ |
| 20 | Duplicar copia a receita, não o histórico | Cópia pausada, 1 fonte e 1 destino, automação em rascunho, zero ofertas | 2026-08-27 | ✓ (após correção do estado devolvido) |
| 21 | Mesma oferta em dois projetos não colide | MLB777 inserida nos dois; cada projeto vê exatamente a sua | 2026-08-27 | ✓ |
| 15 | Refatoração do contexto não mudou o comportamento | Constante a constante contra `perfumes_ml` e `casa_ml_shopee`: cota, janelas, dispersão, proporção, coletas, validade, destino e nicho **idênticos** | 2026-08-27 | ✓ |
| 16 | Automação do banco sobe sem tocar em arquivo | Subprocesso com `AUTOMACAO_ID`: ritmo, chave e destino vieram do banco (`origem: banco`) | 2026-08-27 | ✓ |
| 17 | Banco indisponível não derruba a operação | `AUTOMACAO_ID` inexistente → cai no arquivo do perfil, sem erro | 2026-08-27 | ✓ |
| 13 | Aviso de conexão exige a chave secreta | Chave errada → 401; chave certa → 200; corpo ilegível ou conta desconhecida não quebram | 2026-08-27 | ✓ |
| 14 | Queda de conexão aparece no Dashboard | Conexão em sessão perdida: "Uma conexão precisa da sua atenção", "as automações que dependem delas não publicam", com caminho para Conexões — sem termo técnico na tela | 2026-08-27 | ✓ |
| 12 | Limite de conexões simultâneas é respeitado e explicado | Com as 2 vagas ocupadas, adotar a 3ª instância passou (não ocupa vaga) e conectar devolveu 429 → "Todos os seus WhatsApps disponíveis já estão conectados. Desconecte um antes de conectar outro." | 2026-08-27 | ✓ |

## Contratos externos verificados

| Verificação | Data | Resultado |
|---|---|---|
| `GET /instance/all` com admin token | 2026-08-26 | ✓ 200 — 2 instâncias: `bot de promoções` (produção), `Pessoal` (livre) |
| `GET /instance/status` com token de instância | 2026-08-26 | ✓ 200 |
| Mercado Livre publica API oficial de afiliados? | 2026-08-26 | ✗ não existe — sessão é o único caminho |
| Instância criada por API expira em 1 hora? | — | **pendente (T013)** — decide se o provisionamento automático fica em pé |
| DDL de `db/0009` roda no Postgres real | — | **pendente** — exercitado só no SQLite (sem servidor local); entra no fechamento (T064) |
