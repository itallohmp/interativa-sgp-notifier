import html
import re
import time
from datetime import date, datetime

import httpx
from fastapi import BackgroundTasks

from app.config import settings
from app.integrations.sgp_client import SGPClient
from app.integrations.telegram_client import TelegramClient
from app.utils.formatter import (
    formatar_cliente,
    formatar_faturas,
    formatar_ocorrencias,
)


class OccurrenceService:
    # marcador usado na pergunta de horário e lido de volta na resposta
    _MARCADOR_REAGENDAR = "Reagendar OS #{os_id}"
    _REGEX_REAGENDAR = re.compile(r"Reagendar OS #(\d+)")
    # prazo para responder o reagendamento; depois disso volta ao menu
    _PRAZO_REAGENDAR_SEGUNDOS = 15 * 60

    # motivos disponíveis ao criar OS: codigo -> (rótulo, ocorrenciatipo)
    _MOTIVOS_OS = {
        30: ("Acesso Lento", 3),
        40: ("LOS", 2),
    }

    def __init__(self):
        self.sgp_client = SGPClient()
        self.telegram_client = TelegramClient()
        # fluxo de criar OS por usuário: "chat_id:user_id" -> dict de estado
        self._criar_os_estado: dict[str, dict] = {}
        # ids vistos interagindo (para montar a allowlist): user_id -> nome
        self._usuarios_vistos: dict[int, str] = {}

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

    def pedir_horario(self, chat_id: int | str, os_id: int):
        """Pede o novo horário com ForceReply (resposta chega mesmo no grupo)."""
        marcador = self._MARCADOR_REAGENDAR.format(os_id=os_id)
        return self.telegram_client.enviar_forcando_resposta(
            chat_id,
            (
                f"🕐 <b>{marcador}</b>\n\n"
                f"Responda esta mensagem com a nova data e hora:\n"
                f"<code>DD/MM/AAAA HH:MM</code>\n"
                f"Exemplo: <code>21/07/2026 14:30</code>"
            ),
        )

    def os_id_de_reagendamento(self, reply_text: str) -> int | None:
        """Extrai o os_id do texto da mensagem respondida, se for a pergunta."""
        achado = self._REGEX_REAGENDAR.search(reply_text or "")
        return int(achado.group(1)) if achado else None

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
        os_id: int,
        texto: str,
        user_name: str | None = None,
        data_pergunta: int = 0,
        data_resposta: int = 0,
    ):
        """Recebe o horário respondido, grava no SGP e confirma."""
        # prazo expirado: não reagenda, avisa e volta ao menu principal
        if (
            data_pergunta
            and data_resposta
            and data_resposta - data_pergunta > self._PRAZO_REAGENDAR_SEGUNDOS
        ):
            minutos = self._PRAZO_REAGENDAR_SEGUNDOS // 60
            self.telegram_client.enviar_mensagem_para(
                chat_id,
                (
                    f"⏱️ Tempo esgotado para reagendar a OS #{os_id} "
                    f"(limite de {minutos} min). Voltando ao menu."
                ),
            )
            return self.telegram_client.enviar_menu(chat_id)

        quando = self._parse_datetime(texto)
        if not quando:
            # mantém o marcador para que a nova resposta ainda traga o os_id
            marcador = self._MARCADOR_REAGENDAR.format(os_id=os_id)
            return self.telegram_client.enviar_forcando_resposta(
                chat_id,
                (
                    f"❌ Formato inválido — <b>{marcador}</b>\n\n"
                    f"Responda com <code>DD/MM/AAAA HH:MM</code>, "
                    f"ex.: <code>21/07/2026 14:30</code>"
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
            return self.telegram_client.enviar_mensagem_para(
                chat_id, f"❌ Falha ao reagendar a OS #{os_id}: {erro}"
            )

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

    # ------------------------------------------------------------------ #
    #  Consulta de cliente / faturas / criação de OS por CPF
    # ------------------------------------------------------------------ #

    _TECLADO_MENU = [[{"text": "📋 Menu", "callback_data": "menu"}]]

    def _extrair_cpf(self, texto: str) -> str | None:
        """Extrai só os dígitos; CPF=11, CNPJ=14."""
        digitos = re.sub(r"\D", "", texto or "")
        return digitos if len(digitos) in (11, 14) else None

    def pedir_cpf(self, chat_id: int | str, marcador: str):
        """Pede o CPF com ForceReply (chega ao webhook mesmo no grupo)."""
        return self.telegram_client.enviar_forcando_resposta(
            chat_id,
            f"{marcador}\n\nResponda com o <b>CPF/CNPJ</b> do cliente.",
        )

    def consulta_cliente(self, chat_id: int | str, cpf_texto: str):
        cpf = self._extrair_cpf(cpf_texto)
        if not cpf:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "❌ CPF/CNPJ inválido. Envie 11 (CPF) ou 14 (CNPJ) dígitos."
            )
        contratos = self.sgp_client.consultar_cliente(cpf)
        ocs = {}
        for c in contratos:
            status = str(c.get("contratoStatusDisplay") or "").lower()
            if "cancel" not in status:
                ocs[c.get("contratoId")] = self.sgp_client.listar_ocorrencias_contrato(
                    c.get("contratoId")
                )
        mensagem = formatar_cliente(contratos, ocs)
        return self.telegram_client._enviar_com_teclado(
            chat_id, mensagem, self._TECLADO_MENU
        )

    def enviar_faturas(self, chat_id: int | str, cpf_texto: str):
        cpf = self._extrair_cpf(cpf_texto)
        if not cpf:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "❌ CPF/CNPJ inválido. Envie 11 (CPF) ou 14 (CNPJ) dígitos."
            )
        contratos = self.sgp_client.consultar_cliente(cpf)
        if not contratos:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "🔎 Nenhum cliente encontrado para esse CPF/CNPJ."
            )
        blocos = [
            {
                "contrato": c.get("contratoId"),
                "faturas": self.sgp_client.listar_faturas_abertas(c.get("contratoId")),
            }
            for c in contratos
        ]
        mensagem = formatar_faturas(blocos)
        return self.telegram_client._enviar_com_teclado(
            chat_id, mensagem, self._TECLADO_MENU
        )

    def iniciar_criar_os(self, chat_id: int | str, cpf_texto: str):
        cpf = self._extrair_cpf(cpf_texto)
        if not cpf:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "❌ CPF/CNPJ inválido. Envie 11 (CPF) ou 14 (CNPJ) dígitos."
            )
        contratos = self.sgp_client.consultar_cliente(cpf)
        ativos = [
            c
            for c in contratos
            if "cancel" not in str(c.get("contratoStatusDisplay") or "").lower()
        ]
        if not ativos:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "🔎 Nenhum contrato ativo encontrado para esse CPF/CNPJ."
            )
        if len(ativos) == 1:
            return self.criar_os_escolher_motivo(chat_id, ativos[0]["contratoId"])

        teclado = [
            [
                {
                    "text": f"Contrato {c.get('contratoId')} · {str(c.get('planointernet') or '')[:18]}",
                    "callback_data": f"cosc:{c.get('contratoId')}",
                }
            ]
            for c in ativos
        ]
        return self.telegram_client._enviar_com_teclado(
            chat_id, "🆕 <b>Criar OS</b>\n\nEscolha o contrato:", teclado
        )

    def criar_os_escolher_motivo(self, chat_id: int | str, contrato: int):
        # mostra a(s) ocorrência(s) aberta(s) com a descrição (pedido do usuário)
        ocs = self.sgp_client.listar_ocorrencias_contrato(contrato)
        aviso = ""
        if ocs:
            linhas = "\n".join(
                f"• {o.get('numero')} — "
                f"{html.escape(str(o.get('conteudo') or o.get('tipo') or ''))} "
                f"(OS: {len(o.get('ordens_servicos', []))})"
                for o in ocs[:5]
            )
            aviso = (
                "\n\n⚠️ <b>Já há ocorrência aberta neste contrato:</b>\n"
                f"{linhas}\n"
                "<i>Uma ocorrência NOVA será criada — o SGP não anexa à existente. "
                "Feche a anterior no SGP se necessário.</i>"
            )
        teclado = [
            [{"text": "📉 Acesso Lento", "callback_data": f"cosm:{contrato}:30"}],
            [{"text": "🔴 LOS", "callback_data": f"cosm:{contrato}:40"}],
        ]
        return self.telegram_client._enviar_com_teclado(
            chat_id,
            f"🆕 <b>Criar OS — Contrato {contrato}</b>{aviso}\n\nEscolha o <b>motivo</b>:",
            teclado,
        )

    def criar_os_escolher_equipe(self, chat_id: int | str, contrato: int, motivo: int):
        rotulo = self._MOTIVOS_OS.get(motivo, ("?", 5))[0]
        tecnicos = self.sgp_client.listar_tecnicos()
        teclado = []
        for t in tecnicos:
            username = t.get("username")
            if not username:
                continue
            nome = t.get("nome") or username
            teclado.append(
                [
                    {
                        "text": f"👷 {nome}",
                        "callback_data": f"cose:{contrato}:{motivo}:{username}",
                    }
                ]
            )
        if not teclado:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "Nenhuma equipe técnica cadastrada no SGP."
            )
        return self.telegram_client._enviar_com_teclado(
            chat_id,
            f"🆕 <b>Contrato {contrato}</b> · Motivo: {rotulo}\n\nEscolha a <b>equipe</b>:",
            teclado,
        )

    def criar_os_pedir_data(
        self,
        chat_id: int | str,
        user_id: int | str,
        contrato: int,
        motivo: int,
        equipe: str,
    ):
        self._criar_os_estado[f"{chat_id}:{user_id}"] = {
            "contrato": contrato,
            "motivo": motivo,
            "equipe": equipe,
            "step": "data",
        }
        return self.telegram_client.enviar_forcando_resposta(
            chat_id,
            (
                "🆕 <b>Agendamento da nova OS</b>\n\n"
                "Responda com a <b>data e hora</b>:\n"
                "<code>DD/MM/AAAA HH:MM</code>\n"
                "Exemplo: <code>06/08/2026 14:30</code>"
            ),
        )

    def criar_os_receber_texto(
        self,
        chat_id: int | str,
        user_id: int | str,
        texto: str,
        user_name: str | None = None,
    ):
        chave = f"{chat_id}:{user_id}"
        estado = self._criar_os_estado.get(chave)
        if not estado:
            return None

        if estado["step"] == "data":
            quando = self._parse_datetime(texto)
            if not quando:
                return self.telegram_client.enviar_forcando_resposta(
                    chat_id,
                    "❌ Formato inválido. Responda <code>DD/MM/AAAA HH:MM</code>, "
                    "ex.: <code>06/08/2026 14:30</code>",
                )
            estado["data"] = quando[:16]  # 'AAAA-MM-DD HH:MM'
            estado["step"] = "obs"
            return self.telegram_client.enviar_forcando_resposta(
                chat_id,
                "📝 Responda com uma <b>observação</b> para a OS "
                "(ou <code>-</code> para pular).",
            )

        # step == "obs" -> cria a OS
        obs = "" if texto.strip() in ("-", "") else texto.strip()
        self._criar_os_estado.pop(chave, None)
        rotulo, ocorrenciatipo = self._MOTIVOS_OS.get(estado["motivo"], ("OS", 5))
        try:
            resp = self.sgp_client.criar_os(
                contrato=estado["contrato"],
                motivoos=estado["motivo"],
                ocorrenciatipo=ocorrenciatipo,
                responsavel=estado["equipe"],
                data_hora_agendamento=estado["data"],
                observacao=obs,
                conteudo=f"OS ({rotulo}) aberta via bot",
            )
        except httpx.HTTPError as erro:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, f"❌ Falha ao criar a OS: {erro}"
            )

        protocolo = resp.get("protocolo") if isinstance(resp, dict) else None
        mensagem = (
            f"✅ <b>OS criada</b>\n"
            f"<b>Contrato:</b> {estado['contrato']}\n"
            f"<b>Motivo:</b> {rotulo}\n"
            f"<b>Equipe:</b> {html.escape(str(estado['equipe']))}\n"
            f"<b>Agendada:</b> {html.escape(estado['data'])}\n"
        )
        if protocolo:
            mensagem += f"<b>Protocolo:</b> {html.escape(str(protocolo))}\n"
        mensagem += f"<b>Por:</b> {html.escape(str(user_name or 'desconhecido'))}"
        return self.telegram_client._enviar_com_teclado(
            chat_id, mensagem, self._TECLADO_MENU
        )

    def enviar_ids_grupo(self, chat_id: int | str):
        """
        Junta os administradores (getChatAdministrators) com quem já interagiu
        e monta a linha pronta para TELEGRAM_ALLOWED_USER_IDS.
        Obs.: o Telegram não permite listar TODOS os membros de um grupo.
        """
        ids: dict[int, str] = {}
        linhas = []

        for membro in self.telegram_client.listar_administradores(chat_id):
            usuario = membro.get("user", {})
            uid = usuario.get("id")
            if not uid or usuario.get("is_bot"):
                continue
            nome = usuario.get("first_name") or usuario.get("username") or "?"
            ids[uid] = nome
            linhas.append(f"👑 {html.escape(nome)} — <code>{uid}</code>")

        for uid, nome in self._usuarios_vistos.items():
            if uid not in ids:
                ids[uid] = nome
                linhas.append(f"👤 {html.escape(nome or '?')} — <code>{uid}</code>")

        if not ids:
            return self.telegram_client.enviar_mensagem_para(
                chat_id, "Nenhum id capturado ainda. Peça para a equipe usar o bot."
            )

        csv = ",".join(str(i) for i in ids)
        mensagem = (
            "🆔 <b>IDs do grupo</b>\n"
            "(👑 admin · 👤 já interagiu — o Telegram não lista os demais)\n\n"
            + "\n".join(linhas)
            + "\n\n<b>Para o .env:</b>\n"
            f"<code>TELEGRAM_ALLOWED_USER_IDS={csv}</code>"
        )
        return self.telegram_client.enviar_mensagem_para(chat_id, mensagem)

    def configurar_webhook(self):
        webhook_url = f"{settings.PUBLIC_URL}/webhook"

        url = (
            f"https://api.telegram.org/bot" f"{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        )

        payload = {"url": webhook_url}
        if settings.TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET

        response = httpx.post(url, json=payload)

        return response.json()

    def _identificar_origem(self, update: dict):
        """Retorna (chat_id, user_id, callback_id, texto) do update."""
        if "callback_query" in update:
            cq = update["callback_query"]
            chat_id = (cq.get("message") or {}).get("chat", {}).get("id")
            return chat_id, cq.get("from", {}).get("id"), cq.get("id"), None
        if "message" in update:
            m = update["message"]
            return (
                m.get("chat", {}).get("id"),
                m.get("from", {}).get("id"),
                None,
                m.get("text", ""),
            )
        return None, None, None, None

    def _autorizado(self, update: dict) -> bool:
        """
        Fase 2: só processa em chats autorizados e (opcionalmente) de
        usuários autorizados. /meuid é liberado para qualquer um coletar o id.
        """
        chat_id, user_id, callback_id, texto = self._identificar_origem(update)

        chats = settings.allowed_chat_ids
        if chats and str(chat_id) not in chats:
            return False  # chat não autorizado: ignora em silêncio

        # captura quem interage no chat autorizado (ajuda a montar a allowlist)
        origem = update.get("callback_query") or update.get("message") or {}
        frm = origem.get("from") or {}
        if frm.get("id") and not frm.get("is_bot"):
            self._usuarios_vistos[frm["id"]] = (
                frm.get("first_name") or frm.get("username") or ""
            )

        partes = (texto or "").split(maxsplit=1)
        comando = partes[0].split("@", 1)[0].lower() if partes else ""
        if comando in ("/meuid", "/id"):
            self.telegram_client.enviar_mensagem_para(
                chat_id,
                f"🆔 <b>Seu id:</b> <code>{user_id}</code>\n"
                f"<b>Chat:</b> <code>{chat_id}</code>",
            )
            return False  # já respondido; não segue o fluxo normal

        usuarios = settings.allowed_user_ids
        if usuarios and str(user_id) not in usuarios:
            if callback_id:
                self.telegram_client.answer_callback_query(
                    callback_id, texto="⛔ Sem permissão"
                )
            return False

        return True

    def _seguro(self, func, *args, **kwargs):
        """
        Executa uma tarefa de fundo sem deixar exceção subir (evita traceback
        na rota e ação silenciosamente quebrada). Loga e, se der pra saber o
        chat, avisa o usuário.
        """
        try:
            return func(*args, **kwargs)
        except Exception as erro:
            print(f"[erro] {getattr(func, '__name__', func)}: {type(erro).__name__}: {erro}")
            chat = kwargs.get("chat_id") or (args[0] if args else None)
            if isinstance(chat, (int, str)):
                self.telegram_client.enviar_mensagem_para(
                    chat, "⚠️ Não consegui concluir a ação. Tente novamente."
                )

    async def processar_webhook(self, update: dict, background: BackgroundTasks):

        if not self._autorizado(update):
            return {"ok": True}

        try:
            return await self._rotear(update, background)
        except Exception as erro:
            print(f"[erro] processar_webhook: {type(erro).__name__}: {erro}")
            return {"ok": True}

    async def _rotear(self, update: dict, background: BackgroundTasks):

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
                background.add_task(self._seguro, self.iniciar_designacao, chat_id)

            elif data.startswith("dsg:"):
                periodo = data.split(":", 1)[1]
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Carregando ocorrências..."
                )
                background.add_task(self._seguro, self.listar_os_designacao, chat_id, periodo)

            elif data.startswith("os:"):
                os_id = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self._seguro, self.abrir_acoes_os, chat_id, os_id)

            elif data.startswith("eql:"):
                os_id = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Carregando equipes..."
                )
                background.add_task(self._seguro, self.escolher_equipe, chat_id, os_id)

            elif data.startswith("hr:"):
                os_id = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self._seguro, self.pedir_horario, chat_id, os_id)

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

            elif data == "cliente":
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(
                    self.pedir_cpf, chat_id, "🔎 <b>Consultar Cliente</b>"
                )

            elif data == "faturas":
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(
                    self.pedir_cpf, chat_id, "💰 <b>Faturas do Cliente</b>"
                )

            elif data == "criaros":
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self._seguro, self.pedir_cpf, chat_id, "🆕 <b>Criar OS</b>")

            elif data.startswith("cosc:"):
                contrato = int(data.split(":", 1)[1])
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(self._seguro, self.criar_os_escolher_motivo, chat_id, contrato)

            elif data.startswith("cosm:"):
                _, contrato, motivo = data.split(":", 2)
                self.telegram_client.answer_callback_query(
                    callback_id, texto="Carregando equipes..."
                )
                background.add_task(
                    self.criar_os_escolher_equipe, chat_id, int(contrato), int(motivo)
                )

            elif data.startswith("cose:"):
                _, contrato, motivo, equipe = data.split(":", 3)
                self.telegram_client.answer_callback_query(callback_id)
                background.add_task(
                    self.criar_os_pedir_data,
                    chat_id,
                    user_id,
                    int(contrato),
                    int(motivo),
                    equipe,
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
            resposta_a = mensagem.get("reply_to_message") or {}
            reply_text = resposta_a.get("text", "")
            chave = f"{chat_id}:{user_id}"

            # normaliza o comando: "/ids@meubot arg" -> comando="/ids", arg="arg"
            partes = texto.split(maxsplit=1)
            comando = partes[0].split("@", 1)[0].lower() if partes else ""
            arg = partes[1] if len(partes) > 1 else ""

            if comando in ("/menu", "/os", "/start"):
                self._criar_os_estado.pop(chave, None)
                background.add_task(self._seguro, self.telegram_client.enviar_menu, chat_id=chat_id)

            elif comando == "/designar":
                self._criar_os_estado.pop(chave, None)
                background.add_task(self._seguro, self.iniciar_designacao, chat_id)

            elif comando in ("/ids", "/grupo"):
                background.add_task(self._seguro, self.enviar_ids_grupo, chat_id)

            elif comando == "/cliente":
                if self._extrair_cpf(arg):
                    background.add_task(self._seguro, self.consulta_cliente, chat_id, arg)
                else:
                    background.add_task(
                        self.pedir_cpf, chat_id, "🔎 <b>Consultar Cliente</b>"
                    )

            elif comando == "/fatura":
                if self._extrair_cpf(arg):
                    background.add_task(self._seguro, self.enviar_faturas, chat_id, arg)
                else:
                    background.add_task(
                        self.pedir_cpf, chat_id, "💰 <b>Faturas do Cliente</b>"
                    )

            elif comando == "/criaros":
                if self._extrair_cpf(arg):
                    background.add_task(self._seguro, self.iniciar_criar_os, chat_id, arg)
                else:
                    background.add_task(self._seguro, self.pedir_cpf, chat_id, "🆕 <b>Criar OS</b>")

            elif self.os_id_de_reagendamento(reply_text) is not None:
                background.add_task(
                    self.aplicar_horario,
                    chat_id,
                    self.os_id_de_reagendamento(reply_text),
                    texto,
                    user_name,
                    resposta_a.get("date", 0),
                    mensagem.get("date", 0),
                )

            elif "Consultar Cliente" in reply_text:
                background.add_task(self._seguro, self.consulta_cliente, chat_id, texto)

            elif "Faturas do Cliente" in reply_text:
                background.add_task(self._seguro, self.enviar_faturas, chat_id, texto)

            elif "Criar OS" in reply_text:
                background.add_task(self._seguro, self.iniciar_criar_os, chat_id, texto)

            elif chave in self._criar_os_estado:
                background.add_task(
                    self.criar_os_receber_texto, chat_id, user_id, texto, user_name
                )

            return {"ok": True}

        return {"ok": True}
