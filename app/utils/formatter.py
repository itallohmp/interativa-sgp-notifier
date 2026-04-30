import html
from datetime import date, timedelta


def formatar_ocorrencias(ocorrencias: list[dict], periodo: str = "hoje") -> str:
    hoje = date.today()


    if periodo == "d7":
        d7 = hoje - timedelta(days=7)
        label_periodo = f"{d7.strftime('%d/%m/%Y')} até {hoje.strftime('%d/%m/%Y')}"
        titulo = "📅 <b>Interativa Fibra - OS dos Últimos 7 Dias</b>"
    else:
        label_periodo = hoje.strftime("%d/%m/%Y")
        titulo = "📡 <b>Interativa Fibra - Ocorrências em Aberto</b>"

    if not ocorrencias:
        return f"{titulo}\n\n<b>Período:</b> {label_periodo}\n\nNenhuma ocorrência encontrada."

    mensagem = f"{titulo}\n\n"
    mensagem += f"<b>Período:</b> {label_periodo}\n"
    mensagem += f"<b>Total:</b> {len(ocorrencias)}\n\n"

    for i, ocorrencia in enumerate(ocorrencias, start=1):
        cliente = html.escape(str(ocorrencia.get("cliente", "N/A")))
        
        #formatação da hora, antes do escape
        data_str = ocorrencia.get("os_data_agendamento", "")
        hora = data_str[11:16] if len(data_str) >= 16 else "N/A" 
        os_data_agendamento = html.escape(hora)
        
        cidade = html.escape(str(ocorrencia.get("endereco_cidade", "N/A")))
        bairro = html.escape(str(ocorrencia.get("endereco_bairro", "N/A")))
        endereco_numero = html.escape(str(ocorrencia.get("endereco_numero", "N/A")))
        endereco_logradouro = html.escape(str(ocorrencia.get("endereco_logradouro", "N/A")))
        os_motivo_descricao = html.escape(str(ocorrencia.get("os_motivo_descricao", "N/A")))

        mensagem += (
            f"📌 <b>{i}. Cliente:</b> {cliente}\n"
            f"<b>Horário:</b> {os_data_agendamento}\n"
            f"<b>Cidade:</b> {cidade}\n"
            f"<b>Bairro:</b> {bairro}\n"
            f"<b>Rua:</b> {endereco_logradouro}\n"
            f"<b>Número:</b> {endereco_numero}\n"
            f"⚠️ <b>Motivo:</b> {os_motivo_descricao}\n\n"
        )

    return mensagem