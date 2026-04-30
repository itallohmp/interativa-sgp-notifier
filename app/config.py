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

settings = Settings()