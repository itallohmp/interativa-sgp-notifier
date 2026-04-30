import httpx
from app.config import settings


class TelegramClient:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def enviar_mensagem(self, mensagem: str):
        return self.enviar_mensagem_para(self.chat_id, mensagem)

    def enviar_mensagem_para(self, chat_id: int | str, mensagem: str):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
        }
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()


    def enviar_menu(self, chat_id: int | str = None):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self.chat_id,
            "text": "📡 <b>Interativa Fibra</b>\n\nEscolha o período das OS:",
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "📋 OS do Dia", "callback_data": "os_dia"}],
                    [{"text": "📅 OS dos Últimos 7 Dias", "callback_data": "os_d7"}],
                ]
            },
        }
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def answer_callback_query(self, callback_query_id: str, texto: str = ""):
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id,
            "text": texto, 
        }
        httpx.post(url, json=payload, timeout=10.0)