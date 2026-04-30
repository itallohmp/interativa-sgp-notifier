from fastapi import FastAPI, Request
from app.services.occurrence_service import OccurrenceService
from app.integrations.telegram_client import TelegramClient
from app.scheduler import iniciar_scheduler
from app.config import settings
import httpx

description = """
## Sistema de Notificação de Ocorrências SGP

API desenvolvida para integrar o **SGP** ao **Telegram**.
"""

app = FastAPI(
    title="Interativa Ocorrências API",
    root_path="/interativa-api",
    description=description,
    version="1.0.0",
    contact={"name": "Itallo Polito", "url": "https://itallohmp.pythonanywhere.com/"},
    license_info={"name": "Uso Interno"},
)

service = OccurrenceService()
telegram = TelegramClient()
scheduler = iniciar_scheduler()


@app.get("/")
def home():
    return {"message": "API online"}


@app.get("/ocorrencias/abertas")
def listar_ocorrencias_abertas():
    return service.listar_ocorrencias_abertas_do_dia()


@app.post("/ocorrencias/enviar-agora")
def enviar_ocorrencias_agora():
    return service.enviar_ocorrencias_abertas_telegram()


@app.post("/ocorrencias/menu")
def enviar_menu():
    return telegram.enviar_menu()


@app.post("/configurar-webhook")
def configurar_webhook():

    webhook_url = f"{settings.PUBLIC_URL}/interativa-api/webhook"
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    response = httpx.post(url, json={"url": webhook_url})
    return response.json()


@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()

    if "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback["id"]
        data = callback["data"]
        chat_id = callback["message"]["chat"]["id"]

        telegram.answer_callback_query(callback_id, texto="Buscando OS...")

        if data == "os_dia":
            service.enviar_ocorrencias_para_chat(chat_id, periodo="hoje")

        elif data == "os_d7":
            service.enviar_ocorrencias_para_chat(chat_id, periodo="d7")

        return {"ok": True}

    if "message" in update:
        mensagem = update["message"]
        chat_id = mensagem["chat"]["id"]
        texto = mensagem.get("text", "")

        if texto in ("/menu", "/os"):
            telegram.enviar_menu(chat_id=chat_id)

        return {"ok": True}

    return {"ok": True}