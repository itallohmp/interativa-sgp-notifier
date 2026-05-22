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
    return service.configurar_hook()


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    update = await request.json()
    return await service.processar_webhook(update, background)
    