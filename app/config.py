import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SGP_BASE_URL = os.getenv("SGP_BASE_URL")
    SGP_TOKEN = os.getenv("SGP_TOKEN")
    SGP_APP = os.getenv("SGP_APP")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    PUBLIC_URL = os.getenv("PUBLIC_URL")

    # Segredo compartilhado com o Telegram (header X-Telegram-Bot-Api-Secret-Token)
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    # Allowlists (CSV). Vazio = sem restrição (chat cai no TELEGRAM_CHAT_ID).
    TELEGRAM_ALLOWED_CHAT_IDS = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
    TELEGRAM_ALLOWED_USER_IDS = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")

    @staticmethod
    def _csv_set(valor: str) -> set:
        return {p.strip() for p in (valor or "").split(",") if p.strip()}

    @property
    def allowed_chat_ids(self) -> set:
        """Chats autorizados; se não configurado, usa o grupo oficial."""
        ids = self._csv_set(self.TELEGRAM_ALLOWED_CHAT_IDS)
        if not ids and self.TELEGRAM_CHAT_ID:
            ids = {str(self.TELEGRAM_CHAT_ID).strip()}
        return ids

    @property
    def allowed_user_ids(self) -> set:
        """Usuários autorizados; vazio = qualquer um no chat permitido."""
        return self._csv_set(self.TELEGRAM_ALLOWED_USER_IDS)

settings = Settings()