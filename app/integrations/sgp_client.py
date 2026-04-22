import httpx
from datetime import date
from app.config import settings
from datetime import date, timedelta

class SGPClient:
    def __init__(self):
        self.base_url = settings.SGP_BASE_URL.rstrip("/")
        self.token = settings.SGP_TOKEN
        self.app = settings.SGP_APP

    def listar_ordens_servico_do_dia(self):
        hoje = date.today().strftime("%Y-%m-%d")
        # hoje = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

        url = f"{self.base_url}/api/os/list"

        payload = {
            "app": self.app,
            "token": self.token,
            "status_encerrada": 0,
            "agendamento_inicial": hoje,
            "filtro_data": 1
        }

        response = httpx.post(url, json=payload, timeout=30.0)

        print("URL FINAL:", url)
        print("PAYLOAD:", payload)
        print("STATUS CODE:", response.status_code)
        print("RESPOSTA:", response.text)

        response.raise_for_status()
        return response.json()
    
        # dados = response.json()
        # print("PRIMEIRO ITEM:", dados[0])
        # return dados