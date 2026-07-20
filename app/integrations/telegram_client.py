import httpx
from app.config import settings


class TelegramClient:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def enviar_mensagem(self, mensagem: str):
        return self.enviar_mensagem_para(self.chat_id, mensagem)

    def enviar_mensagem_para(self, chat_id: int | str, mensagem: str):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
        }
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()


    def enviar_menu(self, chat_id: int | str = None):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self.chat_id,
            "text": "📡 <b>Interativa Fibra</b>\n\nEscolha o período das OS:",
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "📋 OS do Dia", "callback_data": "os_dia"}],
                    [{"text": "📅 OS dos Últimos 7 Dias", "callback_data": "os_d7"}],
                    [{"text": "📅 OS de Amanhã", "callback_data": "amanha"}],
                    [{"text": "👷 Designar Equipe", "callback_data": "designar"}],
                ]
            },
        }
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def _enviar_com_teclado(self, chat_id, texto: str, teclado: list):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self.chat_id,
            "text": texto,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": teclado},
        }
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def enviar_selecao_os(self, chat_id: int | str, ocorrencias: list):
        """Passo 1: escolher qual OS será redesignada."""
        if not ocorrencias:
            return self.enviar_mensagem_para(
                chat_id, "Nenhuma ocorrência em aberto para designar."
            )

        teclado = []
        # 20 botões já é bastante para uma tela de celular
        for ocorrencia in ocorrencias[:20]:
            os_id = ocorrencia.get("os_id")
            cliente = str(ocorrencia.get("cliente", "N/A"))[:28]
            equipe = ocorrencia.get("os_tecnico_responsavel") or "sem equipe"
            teclado.append(
                [
                    {
                        "text": f"#{os_id} · {cliente} ({equipe})",
                        "callback_data": f"os:{os_id}",
                    }
                ]
            )

        restantes = len(ocorrencias) - len(teclado)
        rodape = f"\n\n<i>Mostrando {len(teclado)} de {len(ocorrencias)}.</i>" if restantes > 0 else ""

        return self._enviar_com_teclado(
            chat_id,
            f"👷 <b>Designar Equipe</b>\n\nEscolha a ocorrência:{rodape}",
            teclado,
        )

    def enviar_selecao_equipe(self, chat_id: int | str, os_id: int, ocorrencia: dict, tecnicos: list):
        """Passo 2: escolher a equipe de destino."""
        import html as _html

        cliente = _html.escape(str(ocorrencia.get("cliente", "N/A")))
        atual = _html.escape(
            str(ocorrencia.get("os_tecnico_responsavel") or "Não designado")
        )

        teclado = []
        for tecnico in tecnicos:
            username = tecnico.get("username")
            if not username:
                continue
            nome = tecnico.get("nome") or username
            teclado.append(
                [{"text": f"👷 {nome}", "callback_data": f"eq:{os_id}:{username}"}]
            )

        if not teclado:
            return self.enviar_mensagem_para(
                chat_id, "Nenhuma equipe técnica cadastrada no SGP."
            )

        return self._enviar_com_teclado(
            chat_id,
            (
                f"👷 <b>OS #{os_id}</b>\n"
                f"<b>Cliente:</b> {cliente}\n"
                f"<b>Equipe atual:</b> {atual}\n\n"
                f"Designar para:"
            ),
            teclado,
        )

    def answer_callback_query(self, callback_query_id: str, texto: str = ""):
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id,
            "text": texto, 
        }
        httpx.post(url, json=payload, timeout=10.0)