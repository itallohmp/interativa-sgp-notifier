from app.integrations.sgp_client import SGPClient
from app.integrations.telegram_client import TelegramClient
from app.utils.formatter import formatar_ocorrencias


class OccurrenceService:
    def __init__(self):
        self.sgp_client = SGPClient()
        self.telegram_client = TelegramClient()


    def listar_ocorrencias_abertas_do_dia(self) -> list:
        return self.sgp_client.listar_ordens_servico_do_dia()

    def listar_ocorrencias_d7(self) -> list:
        return self.sgp_client.listar_ordens_servico_d7()

    def enviar_ocorrencias_abertas_telegram(self):
        ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        mensagem = formatar_ocorrencias(ocorrencias, periodo="hoje")
        return self.telegram_client.enviar_mensagem(mensagem)

    def enviar_ocorrencias_para_chat(self, chat_id: int | str, periodo: str):
        if periodo == "hoje":
            ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        elif periodo == "d7":
            ocorrencias = self.listar_ocorrencias_d7()
        else:
            raise ValueError(f"Período inválido: {periodo}")

        mensagem = formatar_ocorrencias(ocorrencias, periodo=periodo)
        return self.telegram_client.enviar_mensagem_para(chat_id, mensagem)