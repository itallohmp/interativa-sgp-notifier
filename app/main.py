from fastapi import FastAPI, Request, BackgroundTasks
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
async def webhook(request: Request, background: BackgroundTasks):
    update = await request.json()

    if "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback["id"]
        data = callback["data"]
        chat_id = callback["message"]["chat"]["id"]
        
        user_id = callback["from"]["id"]
        user_name = callback["from"].get("first_name") or callback["from"].get("username")

        telegram.answer_callback_query(callback_id, texto="Buscando OS...")

        if data == "os_dia":
            background.add_task(
                service.enviar_ocorrencias_para_chat, chat_id, "hoje", user_id, user_name)
        elif data == "os_d7":
            background.add_task(
                service.enviar_ocorrencias_para_chat, chat_id, "d7", user_id, user_name)
        elif data == "amanha":
            background.add_task(
                service.enviar_ocorrencias_para_chat, chat_id, "amanha", user_id, user_name)

        return {"ok": True}

    if "message" in update:
        mensagem = update["message"]
        chat_id = mensagem["chat"]["id"]
        texto = mensagem.get("text", "")

        if texto in ("/menu", "/os"):
            background.add_task(
                telegram.enviar_menu, chat_id=chat_id)

        return {"ok": True}

    return {"ok": True}