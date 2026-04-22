import httpx
from app.config import settings


class TelegramClient:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

    def enviar_mensagem(self, mensagem: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": mensagem,
            "parse_mode": "HTML"
        }

        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()