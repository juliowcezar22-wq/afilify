"""
PERFIL: grupo de promoções de CASA — Mercado Livre + Shopee

Mesmo motor do grupo de perfumes. Muda o nicho (nichos/casa.py), os dois
marketplaces, o grupo de destino e o ritmo.

Para ativar:
    1. crie o grupo no WhatsApp e ponha o JID em GRUPO_WHATSAPP
       (python3 agente.py ml grupo --listar mostra os JIDs)
    2. PERFIL=casa_ml_shopee python3 agente.py ml buscar --seco
"""

NOME = "casa-ml-shopee"
NICHO = "casa"
MARKETPLACES = ["mercadolivre", "shopee"]

GRUPO_WHATSAPP = ""            # ← preencher com o JID do grupo de casa

# Casa cansa mais rápido que perfume: menos mensagem, janela mais curta.
ENVIOS_POR_DIA = (40, 60)
ENVIO_INICIO_JANELA = (9.0, 10.0)
ENVIO_FIM_JANELA = (21.0, 22.0)
ENVIO_DISPERSAO = 0.82

# Em casa não faz sentido priorizar "importado" — o comprador quer utilidade
# e preço, não origem da marca.
PROPORCAO_PREFERIDAS = 0.0

# Oferta de casa dura mais que perfume, então coleta menos vezes e a fila
# pode envelhecer mais antes de vencer.
BUSCA_HORAS = [8, 14, 20]
VALIDADE_HORAS = 72

CLONE_ATIVO = False            # não há grupo rival de casa mapeado ainda
CLONE_GRUPOS = []
