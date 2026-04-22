from fastapi import FastAPI
from app.services.occurrence_service import OccurrenceService
from app.scheduler import iniciar_scheduler

description = """
## Sistema de Notificação de Ocorrências SGP

API desenvolvida para integrar o **SGP** ao **Telegram**, com o objetivo de consultar ocorrências em aberto e enviar resumos automáticos para a equipe técnica.

### Funcionalidades principais
- Consultar ocorrências em aberto no SGP
- Filtrar ocorrências do dia
- Formatar os dados para leitura rápida
- Enviar mensagens automaticamente para grupo técnico no Telegram
- Possibilitar testes manuais via endpoints da API
"""

app = FastAPI(
    title="Interativa Ocorrências API",
    description=description,
    version="1.0.0",
    contact={
        "name": "Itallo Polito",
        "url": "https://itallohmp.pythonanywhere.com/",
    },
    license_info={
        "name": "Uso Interno",
    },
)

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