import socket

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

# O IPv6 do servidor é um buraco (blackhole): conexões de saída para Telegram/
# SGP resolvem primeiro em IPv6 e travam até o timeout. Diferente do curl, o
# httpx não faz fallback. Solução: preferir IPv4 na resolução de nomes.
_getaddrinfo_original = socket.getaddrinfo


def _preferir_ipv4(host, port, family=0, *args, **kwargs):
    resultados = _getaddrinfo_original(host, port, family, *args, **kwargs)
    apenas_v4 = [r for r in resultados if r[0] == socket.AF_INET]
    return apenas_v4 or resultados


socket.getaddrinfo = _preferir_ipv4

from app.config import settings
from app.integrations.telegram_client import TelegramClient
from app.scheduler import iniciar_scheduler
from app.services.occurrence_service import OccurrenceService

description = """
## Sistema de Notificação de Ocorrências SGP

API desenvolvida para integrar o **SGP** ao **Telegram**.
"""

app = FastAPI(
    title="Interativa Ocorrências API",
    root_path="/",
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
    return service.configurar_webhook()


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    # Fase 1: só aceita requisições que trazem o secret token do Telegram.
    segredo = settings.TELEGRAM_WEBHOOK_SECRET
    if segredo:
        recebido = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if recebido != segredo:
            raise HTTPException(status_code=403, detail="forbidden")
    update = await request.json()
    # responde 200 na hora; processa em thread (não bloqueia o event loop)
    background.add_task(service.processar_update, update)
    return {"ok": True}
