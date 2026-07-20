import html
import time
from datetime import date, datetime

import httpx
from fastapi import BackgroundTasks

from app.config import settings
from app.integrations.sgp_client import SGPClient
from app.integrations.telegram_client import TelegramClient
from app.utils.formatter import formatar_ocorrencias


class OccurrenceService:
    def __init__(self):
        self.sgp_client = SGPClient()
        self.telegram_client = TelegramClient()
        # quem está digitando um novo horário: "chat_id:user_id" -> os_id
        self._aguardando_horario: dict[str, int] = {}

    def listar_ocorrencias_abertas_do_dia(self) -> list:
        return self.sgp_client.listar_ordens_servico_do_dia()

    def listar_ocorrencias_d7(self) -> list:
        return self.sgp_client.listar_ordens_servico_d7()

    def listar_ocorrencias_amanha(self) -> list:
        return self.sgp_client.listar_ordens_amanha()

    def enviar_ocorrencias_abertas_telegram(self):
        ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        mensagem = formatar_ocorrencias(ocorrencias, periodo="hoje")
        return self.telegram_client.enviar_mensagem(mensagem)

    def enviar_ocorrencias_para_chat(
        self,
        chat_id: int | str,
        periodo: str,
        user_id: int | str = None,
        user_name: str | None = None,
    ):

        if periodo == "hoje":
            ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        elif periodo == "d7":
            ocorrencias = self.listar_ocorrencias_d7()
        elif periodo == "amanha":
            ocorrencias = self.listar_ocorrencias_amanha()
        else:
            raise ValueError(f"Período inválido: {periodo}")
        inicio = time.time()
        mensagem = formatar_ocorrencias(
            ocorrencias, periodo=periodo, user_id=user_id, user_name=user_name
        )
        fim = time.time()
        print(f"Rota inteira demorou: {fim - inicio:.2f} segundos")
        teclado = [[{"text": "📋 Menu", "callback_data": "menu"}]]
        return self.telegram_client._enviar_com_teclado(chat_id, mensagem, teclado)

    def iniciar_designacao(self, chat_id: int | str):
        """Passo 1: pergunta o período (dia ou amanhã)."""
        return self.telegram_client.enviar_periodo_designacao(chat_id)

    def listar_os_designacao(self, chat_id: int | str, periodo: str):
        """Passo 2: lista as OS do período escolhido."""
        if periodo == "amanha":
            ocorrencias = self.listar_ocorrencias_amanha()
        else:
            periodo = "hoje"
            ocorrencias = self.listar_ocorrencias_abertas_do_dia()
        return self.telegram_client.enviar_selecao_os(chat_id, ocorrencias, periodo)

    def abrir_acoes_os(self, chat_id: int | str, os_id: int):
        """Passo 3: mostra as ações possíveis (equipe ou horário)."""
        ocorrencia = self.sgp_client.buscar_os_por_id(os_id)
        if not ocorrencia:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, f"OS #{os_id} não encontrada."
            )
        return self.telegram_client.enviar_acoes_os(chat_id, os_id, ocorrencia)

    def escolher_equipe(self, chat_id: int | str, os_id: int):
        """Manda as equipes disponíveis para aquela OS."""
        ocorrencia = self.sgp_client.buscar_os_por_id(os_id)
        if not ocorrencia:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, f"OS #{os_id} não encontrada."
            )

        tecnicos = self.sgp_client.listar_tecnicos()
        return self.telegram_client.enviar_selecao_equipe(
            chat_id, os_id, ocorrencia, tecnicos
        )

    def aplicar_designacao(
        self,
        chat_id: int | str,
        os_id: int,
        tecnico: str,
        user_name: str | None = None,
    ):
        """Passo 3: grava no SGP e confirma no grupo."""
        anterior = self.sgp_client.buscar_os_por_id(os_id) or {}
        equipe_anterior = anterior.get("os_tecnico_responsavel") or "Não designado"

        try:
            self.sgp_client.designar_equipe(os_id, tecnico)
        except httpx.HTTPError as erro:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, f"❌ Falha ao designar a OS #{os_id}: {erro}"
            )

        # relê para confirmar o que o SGP de fato gravou
        atualizada = self.sgp_client.buscar_os_por_id(os_id) or {}
        equipe_nova = atualizada.get("os_tecnico_responsavel") or tecnico

        mensagem = (
            f"✅ <b>OS #{os_id} redesignada</b>\n"
            f"<b>Cliente:</b> {html.escape(str(atualizada.get('cliente', 'N/A')))}\n"
            f"<b>De:</b> {html.escape(str(equipe_anterior))}\n"
            f"<b>Para:</b> {html.escape(str(equipe_nova))}\n"
            f"<b>Por:</b> {html.escape(str(user_name or 'desconhecido'))}"
        )
        teclado = [[{"text": "📋 Menu", "callback_data": "menu"}]]
        return self.telegram_client._enviar_com_teclado(chat_id, mensagem, teclado)

    def pedir_horario(
        self,
        chat_id: int | str,
        user_id: int | str,
        os_id: int,
    ):
        """Guarda o estado e pede o novo horário por texto."""
        self._aguardando_horario[f"{chat_id}:{user_id}"] = os_id
        return self.telegram_client.enviar_mensagem_para(
            chat_id,
            (
                f"🕐 <b>Reagendar OS #{os_id}</b>\n\n"
                f"Envie a nova data e hora no formato:\n"
                f"<code>DD/MM/AAAA HH:MM</code>\n"
                f"Exemplo: <code>21/07/2026 14:30</code>"
            ),
        )

    def _parse_datetime(self, texto: str) -> str | None:
        """Converte o texto do usuário em 'AAAA-MM-DD HH:MM:SS' ou None."""
        texto = texto.strip()
        formatos = ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m %H:%M")
        for fmt in formatos:
            try:
                dt = datetime.strptime(texto, fmt)
            except ValueError:
                continue
            if "%Y" not in fmt:
                dt = dt.replace(year=date.today().year)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def aplicar_horario(
        self,
        chat_id: int | str,
        user_id: int | str,
        texto: str,
        user_name: str | None = None,
    ):
        """Recebe o horário digitado, grava no SGP e confirma."""
        chave = f"{chat_id}:{user_id}"
        os_id = self._aguardando_horario.get(chave)
        if os_id is None:
            return None

        quando = self._parse_datetime(texto)
        if not quando:
            return self.telegram_client.enviar_mensagem_para(
                chat_id,
                (
                    "❌ Formato inválido. Envie <code>DD/MM/AAAA HH:MM</code>, "
                    "ex.: <code>21/07/2026 14:30</code>"
                ),
            )

        anterior = self.sgp_client.buscar_os_por_id(os_id) or {}
        ag_ant = str(anterior.get("os_data_agendamento", ""))
        antes = (
            f"{ag_ant[8:10]}/{ag_ant[5:7]}/{ag_ant[0:4]} {ag_ant[11:16]}"
            if len(ag_ant) >= 16
            else "N/A"
        )

        try:
            self.sgp_client.alterar_agendamento(os_id, quando)
        except httpx.HTTPError as erro:
            self._aguardando_horario.pop(chave, None)
            return self.telegram_client.enviar_mensagem_para(
                chat_id, f"❌ Falha ao reagendar a OS #{os_id}: {erro}"
            )

        self._aguardando_horario.pop(chave, None)

        atual = self.sgp_client.buscar_os_por_id(os_id) or {}
        ag_novo = str(atual.get("os_data_agendamento", ""))
        depois = (
            f"{ag_novo[8:10]}/{ag_novo[5:7]}/{ag_novo[0:4]} {ag_novo[11:16]}"
            if len(ag_novo) >= 16
            else quando
        )

        mensagem = (
            f"✅ <b>OS #{os_id} reagendada</b>\n"
            f"<b>Cliente:</b> {html.escape(str(atual.get('cliente', 'N/A')))}\n"
            f"<b>De:</b> {html.escape(antes)}\n"
            f"<b>Para:</b> {html.escape(depois)}\n"
            f"<b>Por:</b> {html.escape(str(user_name or 'desconhecido'))}"
        )
        teclado = [[{"text": "📋 Menu", "callback_data": "menu"}]]
        return self.telegram_client._enviar_com_teclado(chat_id, mensagem, teclado)

    def configurar_webhook(self):
        webhook_url = f"{settings.PUBLIC_URL}/webhook"

        url = (
            f"https://api.telegram.org/bot" f"{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        )

        response = httpx.post(url, json={"url": webhook_url})

        return response.json()

    async def processar_webhook(self, update: dict, background: BackgroundTasks):

        if "callback_query" in update:

            callback = update["callback_query"]
            callback_id = callback["id"]
            data = callback["data"]
            chat_id = callback["message"]["chat"]["id"]
            user_id = callback["from"]["id"]
            user_name = callback["from"].get("first_name") or callback["from"].get(
                "username"
            )

            mapa_periodos = {
                "os_dia": "hoje",
                "os_d7": "d7",
                "amanha": "amanha",
            }

            periodo = mapa_periodos.get(data)

            if periodo:
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Buscando OS..."
                )
                background.add_task(
                    self.enviar_ocorrencias_para_chat,
                    chat_id,
                    periodo,
                    user_id,
                    user_name,
                )

            elif data == "menu":
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(
                    self.telegram_client.enviar_menu, chat_id=chat_id
                )

            elif data == "designar":
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self.iniciar_designacao, chat_id)

            elif data.startswith("dsg:"):
                periodo = data.split(":", 1)[1]
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Carregando ocorrências..."
                )
                background.add_task(self.listar_os_designacao, chat_id, periodo)

            elif data.startswith("os:"):
                os_id = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self.abrir_acoes_os, chat_id, os_id)

            elif data.startswith("eql:"):
                os_id = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Carregando equipes..."
                )
                background.add_task(self.escolher_equipe, chat_id, os_id)

            elif data.startswith("hr:"):
                os_id = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self.pedir_horario, chat_id, user_id, os_id)

            elif data.startswith("eq:"):
                _, os_id, tecnico = data.split(":", 2)
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Designando..."
                )
                background.add_task(
                    self.aplicar_designacao,
                    chat_id,
                    int(os_id),
                    tecnico,
                    user_name,
                )

            else:
                self.telegram_client.answer_callback_query(callback_id)

            return {"ok": True}

        if "message" in update:
            mensagem = update["message"]
            chat_id = mensagem["chat"]["id"]
            texto = mensagem.get("text", "")
            de = mensagem.get("from", {})
            user_id = de.get("id")
            user_name = de.get("first_name") or de.get("username")
            chave = f"{chat_id}:{user_id}"

            if texto in ("/menu", "/os"):
                self._aguardando_horario.pop(chave, None)
                background.add_task(self.telegram_client.enviar_menu, chat_id=chat_id)

            elif texto.startswith("/designar"):
                self._aguardando_horario.pop(chave, None)
                background.add_task(self.iniciar_designacao, chat_id)

            elif chave in self._aguardando_horario:
                background.add_task(
                    self.aplicar_horario, chat_id, user_id, texto, user_name
                )

            return {"ok": True}

        return {"ok": True}
