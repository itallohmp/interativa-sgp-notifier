from apscheduler.schedulers.background import BackgroundScheduler
from app.integrations.telegram_client import TelegramClient


def iniciar_scheduler():
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    telegram = TelegramClient()

    scheduler.add_job(
        telegram.enviar_menu,
        trigger="cron",
        hour=7,
        minute=30,
        id="envio_ocorrencias_0730",
        replace_existing=True,
    )
    
    scheduler.add_job(
        telegram.enviar_menu,
        trigger="cron",
        hour=13,
        minute=0,
        id="envio_ocorrencias_1300",
        replace_existing=True,
    )

    scheduler.start()
    return scheduler