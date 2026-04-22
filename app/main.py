from fastapi import FastAPI
from app.services.occurrence_service import OccurrenceService
from app.scheduler import iniciar_scheduler

app = FastAPI(title="Interativa Ocorrências API")

service = OccurrenceService()
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