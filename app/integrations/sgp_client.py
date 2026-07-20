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
        return self._buscar_os(
            data_inicial=hoje, data_final=hoje
            )

    def listar_ordens_servico_d7(self) -> list:
        hoje = date.today().strftime("%Y-%m-%d")
        d7 = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        return self._buscar_os(
            data_inicial=d7, data_final=hoje
            )
    
    def listar_ordens_amanha(self) -> list:
        amanha = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

        return self._buscar_os(
            data_inicial=amanha,
            data_final=amanha
            )

    def listar_tecnicos(self) -> list:
        """Equipes técnicas cadastradas no SGP: id, username e nome."""
        url = f"{self.base_url}/api/ura/tecnicos/"

        response = httpx.post(
            url,
            json={"app": self.app, "token": self.token},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def buscar_os_por_id(self, os_id: int) -> dict | None:
        url = f"{self.base_url}/api/os/list/id/{os_id}"

        response = httpx.post(
            url,
            json={"app": self.app, "token": self.token},
            timeout=30.0,
        )
        response.raise_for_status()

        dados = response.json()
        if isinstance(dados, list):
            return dados[0] if dados else None
        return dados

    def _chamado_update(self, os_id: int, campos: dict) -> dict:
        """
        Altera uma OS via /api/central/chamado/update/, o único endpoint que
        aceita os_tecnico_responsavel e os_data_agendamento — /api/os/update/
        não tem esses parâmetros. Autentica com app+token (cpfcnpj+senha do
        cliente é alternativa, não obrigatória).
        """
        url = f"{self.base_url}/api/central/chamado/update/{os_id}/"

        response = httpx.post(
            url,
            json={"app": self.app, "token": self.token, **campos},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def designar_equipe(self, os_id: int, tecnico: str) -> dict:
        """Redesigna a OS para outra equipe. `tecnico` é o username."""
        return self._chamado_update(os_id, {"os_tecnico_responsavel": tecnico})

    def alterar_agendamento(self, os_id: int, quando: str) -> dict:
        """Reagenda a OS. `quando` no formato 'AAAA-MM-DD HH:MM:SS'."""
        return self._chamado_update(os_id, {"os_data_agendamento": quando})