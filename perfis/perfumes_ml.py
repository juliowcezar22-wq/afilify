"""
PERFIL: o grupo de perfumes no Mercado Livre

Um perfil AMARRA as três coisas independentes:
    nicho          o que é oferta válida        → nichos/perfumes.py
    marketplaces   onde procurar                → mercadolivre, shopee
    grupo          para onde publicar, e o ritmo

É este arquivo que vira uma LINHA NO BANCO quando o painel existir: cada
cliente do SaaS é um perfil, e o motor é o mesmo para todos.
"""

NOME = "perfumes-ml"
NICHO = "perfumes"
MARKETPLACES = ["mercadolivre"]

GRUPO_WHATSAPP = "120363408117538302@g.us"      # #17 ACHEI BARATO | PERFUMES

# ritmo (calibrado no concorrente)
ENVIOS_POR_DIA = (95, 135)
ENVIO_INICIO_JANELA = (8.75, 9.5)
ENVIO_FIM_JANELA = (22.0, 22.75)
ENVIO_DISPERSAO = 0.82
PROPORCAO_PREFERIDAS = 0.70

BUSCA_HORAS = [7, 15]
VALIDADE_HORAS = 48

# monitor de concorrência
CLONE_ATIVO = True
CLONE_GRUPOS = ["120363406025827790@g.us"]      # #101 MAENO PROMOS | PERFUMES
