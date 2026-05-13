from app.integrations.sgp_client import SGPClient
from app.integrations.telegram_client import TelegramClient
from app.utils.formatter import formatar_ocorrencias
from app.config import settings
from fastapi import BackgroundTasks

import httpx


class OccurrenceService:
    def __init__(self):
        self.sgp_client = SGPClient()
        self.telegram_client = TelegramClient()


    def listar_ocorrencias_abertas_do_dia(self) -> list:
        return self.sgp_client.listar_ordens_servico_do_dia()

    def listar_ocorrencias_d7(self) -> list:
        return self.sgp_client.listar_ordens_servico_d7()

    def listar_ocorrencias_amanha(self) -> list:
        return self.sgp_client.listar_ordens_amanha()
            
    def enviar_ocorrencias_abertas_telegram(self):
        ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        mensagem = formatar_ocorrencias(ocorrencias, periodo="hoje")
        return self.telegram_client.enviar_mensagem(mensagem)

    def enviar_ocorrencias_para_chat(self, chat_id: int | str, periodo: str, user_id: int | str = None, user_name: str | None = None):
        if periodo == "hoje":
            ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        elif periodo == "d7":
            ocorrencias = self.listar_ocorrencias_d7()
        elif periodo == "amanha":
            ocorrencias = self.listar_ocorrencias_amanha()
        else:
            raise ValueError(f"Período inválido: {periodo}")

        mensagem = formatar_ocorrencias(ocorrencias, periodo=periodo, user_id=user_id, user_name=user_name)
        return self.telegram_client.enviar_mensagem_para(chat_id, mensagem)
    
    def configurar_webhook(self):
        webhook_url = f"{settings.PUBLIC_URL}/interativa-api/webhook"

        url = (
            f"https://api.telegram.org/bot"
            f"{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        )

        response = httpx.post(url, json={"url": webhook_url})

        return response.json()

    async def processar_webhook(self, update: dict, background: BackgroundTasks):

        if "callback_query" in update:

            callback = update["callback_query"]
            callback_id = callback["id"]
            data = callback["data"]
            chat_id = callback["message"]["chat"]["id"]
            user_id = callback["from"]["id"]
            user_name = (callback["from"].get("first_name")
                or callback["from"].get("username")
            )

            self.telegram_client.answer_callback_query(
                callback_id,
                texto="Buscando OS..."
            )

            mapa_periodos = {
                "os_dia": "hoje",
                "os_d7": "d7",
                "amanha": "amanha",
            }

            periodo = mapa_periodos.get(data)

            if periodo:
                background.add_task(
                    self.enviar_ocorrencias_para_chat,
                    chat_id,
                    periodo,
                    user_id,
                    user_name
                )

            return {"ok": True}

        if "message" in update:
            mensagem = update["message"]
            chat_id = mensagem["chat"]["id"]
            texto = mensagem.get("text", "")

            if texto in ("/menu", "/os"):

                background.add_task(
                    self.telegram_client.enviar_menu,
                    chat_id=chat_id
                )

            return {"ok": True}

        return {"ok": True}