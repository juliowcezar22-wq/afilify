# GRUPO PROMOÇÕES

Agentes que encontram promoções de perfume, geram link de afiliado e
publicam num grupo de WhatsApp. Sem n8n, sem dependência externa —
só Python 3.9+ da biblioteca padrão.

```
.env                    credenciais (fora do git)
.mlcookie               sessão de afiliado do ML (fora do git, ~30 dias)

mercadolivre/           ← o agente pronto e em produção
  agente.py               maestro: CLI, daemon, ritmo de envio, mensagem
  comum.py                base: config, marcas, banco, HTTP, uazapi
  buscador.py             acha oferta sozinho (vitrine + busca)
  clonador.py             monitora o grupo do concorrente
  README.md               documentação completa deste agente

shopee/                 ← a fazer
  agente.py               versão antiga, será reescrita reaproveitando
                          o filtro de marcas, o ritmo e as headlines

deploy/
  agente-ml.service       unit do systemd para a VPS

dados/                  ← gerado em execução, fora do git
  ofertas.db              fila, dedup e status de envio
  agente.log

historico/
  fluxo-n8n-original.json o fluxo do n8n que deu origem a tudo
```

## Rodar

```bash
cd mercadolivre
python3 agente.py rodar      # daemon
python3 agente.py status     # como está a operação
```

Documentação de configuração, filtros, ritmo e deploy:
[mercadolivre/README.md](mercadolivre/README.md).
