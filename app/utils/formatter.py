import html
from datetime import date, timedelta


def formatar_ocorrencias(ocorrencias: list[dict], periodo: str = "hoje", user_id: int | str = None, user_name: str | None = None) -> str:
    hoje = date.today()


    if periodo == "d7":
        d7 = hoje - timedelta(days=7)
        label_periodo = f"{d7.strftime('%d/%m/%Y')} até {hoje.strftime('%d/%m/%Y')}"
        titulo = "📅 <b>Interativa Fibra - OS dos Últimos 7 Dias</b>"
        
    elif periodo == "amanha":
        amanha = hoje + timedelta(days=1)
        label_periodo = amanha.strftime("%d/%m/%Y")
        titulo = "📡 <b>Interativa Fibra - Ocorrências em Aberto</b>"
    else:
        label_periodo = hoje.strftime("%d/%m/%Y")
        titulo = "📡 <b>Interativa Fibra - Ocorrências em Aberto</b>"

    if not ocorrencias:
        return f"{titulo}\n\n<b>Período:</b> {label_periodo}\n\nNenhuma ocorrência encontrada."

    mensagem = f"{titulo}\n\n"
    mensagem += f"<b>Período:</b> {label_periodo}\n"
    mensagem += f"<b>Total:</b> {len(ocorrencias)}\n"
    mensagem += f"<b>Por:</b> {user_name}\n\n"

    for i, ocorrencia in enumerate(ocorrencias, start=1):
        cliente = html.escape(str(ocorrencia.get("cliente", "N/A")))
        
        #formatação da hora, antes do escape
        data_str = ocorrencia.get("os_data_agendamento", "")
        hora = data_str[11:16] if len(data_str) >= 16 else "N/A" 
        os_data_agendamento = html.escape(hora)
        ''
        cidade = html.escape(str(ocorrencia.get("endereco_cidade", "N/A")))
        bairro = html.escape(str(ocorrencia.get("endereco_bairro", "N/A")))
        endereco_numero = html.escape(str(ocorrencia.get("endereco_numero", "N/A")))
        endereco_logradouro = html.escape(str(ocorrencia.get("endereco_logradouro", "N/A")))
        os_motivo_descricao = html.escape(str(ocorrencia.get("os_motivo_descricao", "N/A")))

        # equipe técnica designada
        equipe = html.escape(
            str(ocorrencia.get("os_tecnico_responsavel") or "Não designado")
        )

        mensagem += (
            f"📌 <b>{i}. Cliente:</b> {cliente}\n"
            f"<b>OS:</b> #{html.escape(str(ocorrencia.get('os_id', 'N/A')))}\n"
            f"<b>Horário:</b> {os_data_agendamento}\n"
            f"<b>Cidade:</b> {cidade}\n"
            f"<b>Bairro:</b> {bairro}\n"
            f"<b>Rua:</b> {endereco_logradouro}\n"
            f"<b>Número:</b> {endereco_numero}\n"
            f"⚠️ <b>Motivo:</b> {os_motivo_descricao}\n"
            f"👷 <b>Equipe:</b> {equipe}\n\n"

        )

    return mensagem


def _moeda(valor) -> str:
    try:
        return f"R$ {float(valor):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "R$ -"


def _emoji_status(status: str) -> str:
    s = (status or "").strip().lower()
    if "suspens" in s:
        return "🟠"
    if "cancel" in s or "inativ" in s:
        return "🔴"
    if "ativo" in s:
        return "🟢"
    return "⚪"


def _data_br(data_iso: str) -> str:
    data_iso = str(data_iso or "")
    if len(data_iso) >= 10:
        return f"{data_iso[8:10]}/{data_iso[5:7]}/{data_iso[0:4]}"
    return "-"


def formatar_cliente(contratos: list[dict], ocorrencias_por_contrato: dict | None = None) -> str:
    if not contratos:
        return "🔎 Nenhum cliente/contrato encontrado para esse CPF/CNPJ."

    ocorrencias_por_contrato = ocorrencias_por_contrato or {}
    nome = html.escape(str(contratos[0].get("razaoSocial") or "N/A"))
    cpf = html.escape(str(contratos[0].get("cpfCnpj") or ""))

    msg = f"🔎 <b>{nome}</b>\n<b>CPF/CNPJ:</b> {cpf}\n<b>Contratos:</b> {len(contratos)}\n"

    for c in contratos:
        cid = c.get("contratoId")
        status = str(c.get("contratoStatusDisplay") or "N/A").strip()
        online_txt = "🟢 Online" if c.get("servico_online") else "🔴 Offline"
        plano = html.escape(str(c.get("planointernet") or c.get("servico_plano") or "N/A"))
        a_receber = c.get("contratoTitulosAReceber") or 0
        valor = c.get("contratoValorAberto") or 0.0
        login = html.escape(str(c.get("servico_login") or "N/A"))
        cidade = html.escape(str(c.get("endereco_cidade") or "N/A"))
        uf = html.escape(str(c.get("endereco_uf") or ""))
        ocs = ocorrencias_por_contrato.get(cid, [])

        msg += (
            f"\n📄 <b>Contrato {cid}</b> — {_emoji_status(status)} {html.escape(status)}\n"
            f"{online_txt}\n"
            f"📶 <b>Plano:</b> {plano}\n"
            f"💰 <b>Faturas em aberto:</b> {a_receber}"
        )
        if valor:
            msg += f" ({_moeda(valor)})"
        msg += (
            f"\n🎫 <b>Ocorrências abertas:</b> {len(ocs)}\n"
            f"👤 <b>Login:</b> {login}\n"
            f"📍 {cidade}/{uf}\n"
        )

    return msg


def formatar_faturas(blocos: list[dict]) -> str:
    """blocos: [{'contrato': id, 'faturas': [...]}, ...]"""
    if not any(b.get("faturas") for b in blocos):
        return "💰 Nenhuma fatura em aberto para esse cliente."

    msg = "💰 <b>Faturas em aberto</b>\n"
    for b in blocos:
        faturas = b.get("faturas") or []
        if not faturas:
            continue
        msg += f"\n📄 <b>Contrato {b.get('contrato')}</b>\n"
        for f in faturas:
            doc = html.escape(str(f.get("numeroDocumento", "")))
            venc = _data_br(f.get("dataVencimento"))
            valor = _moeda(f.get("valorCorrigido") or f.get("valor"))
            link = str(f.get("link_cobranca") or f.get("link") or "")
            msg += f"• Doc {doc} — venc {venc} — {valor}\n"
            if link:
                msg += f"  {html.escape(link)}\n"
    return msg