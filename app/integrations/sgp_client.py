import httpx
from datetime import date, timedelta
from app.config import settings


class SGPClient:
    def __init__(self):
        self.base_url = settings.SGP_BASE_URL.rstrip("/")
        self.token = settings.SGP_TOKEN
        self.app = settings.SGP_APP

    def _buscar_os(self, data_inicial: str, data_final: str = None) -> list:
        url = f"{self.base_url}/api/os/list"

        payload = {
            "app": self.app,
            "token": self.token,
            "status_encerrada": 0,
            "agendamento_inicial": data_inicial,
            "filtro_data": 1,
        }

        if data_final:
            payload["agendamento_final"] = data_final

        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def listar_ordens_servico_do_dia(self) -> list:
        hoje = date.today().strftime("%Y-%m-%d")
        return self._buscar_os(data_inicial=hoje)

    def listar_ordens_servico_d7(self) -> list:
        hoje = date.today().strftime("%Y-%m-%d")
        d7 = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        return self._buscar_os(data_inicial=d7, data_final=hoje)