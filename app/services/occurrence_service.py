from app.integrations.sgp_client import SGPClient
from app.integrations.telegram_client import TelegramClient
from app.utils.formatter import formatar_ocorrencias


class OccurrenceService:
    def __init__(self):
        self.sgp_client = SGPClient()
        self.telegram_client = TelegramClient()

    def listar_ocorrencias_abertas_do_dia(self):
        return self.sgp_client.listar_ordens_servico_do_dia()

    def enviar_ocorrencias_abertas_telegram(self):
        ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        mensagem = formatar_ocorrencias(ocorrencias)
        return self.telegram_client.enviar_mensagem(mensagem)