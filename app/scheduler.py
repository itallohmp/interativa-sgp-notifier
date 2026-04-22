from apscheduler.schedulers.background import BackgroundScheduler
from app.services.occurrence_service import OccurrenceService


def iniciar_scheduler():
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    service = OccurrenceService()

    scheduler.add_job(
        service.enviar_ocorrencias_abertas_telegram,
        trigger="cron",
        hour=7,
        minute=30,
        id="envio_ocorrencias_0730",
        replace_existing=True,
    )
    
    scheduler.add_job(
        service.enviar_ocorrencias_abertas_telegram,
        trigger="cron",
        hour=13,
        minute=0,
        id="envio_ocorrencias_1300",
        replace_existing=True,
    )

    scheduler.start()
    return scheduler