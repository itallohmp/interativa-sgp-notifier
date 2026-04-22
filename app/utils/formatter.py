import html
from datetime import date



def formatar_ocorrencias(ocorrencias: list[dict]) -> str:
    hoje = date.today().strftime("%Y-%m-%d")
    
    if not ocorrencias:
        return "📡 <b>Interativa Fibra</b>\n\nNenhuma ocorrência aberta no momento."

    mensagem = "📡 <b>Interativa Fibra - Ocorrências em aberto</b>\n\n"
    mensagem += f"<b>Dia:</b> {hoje}\n"
    mensagem += f"<b>Total:</b> {len(ocorrencias)}\n\n"

    for i, ocorrencia in enumerate(ocorrencias, start=1):
        cliente = html.escape(str(ocorrencia.get("cliente", "N/A")))
        contrato_id = html.escape(str(ocorrencia.get("contrato_id", "N/A")))
        cidade = html.escape(str(ocorrencia.get("endereco_cidade", "N/A")))
        bairro = html.escape(str(ocorrencia.get("endereco_bairro", "N/A")))
        endereco_numero = html.escape(str(ocorrencia.get("endereco_numero", "N/A")))
        endereco_logradouro = html.escape(str(ocorrencia.get("endereco_logradouro", "N/A")))
        os_motivo_descricao = html.escape(str(ocorrencia.get("os_motivo_descricao", "N/A")))

        mensagem += (
            f"📌<b>{i}. Cliente:</b> {cliente}\n"
            f"<b>Contrato:</b> {contrato_id}\n"
            f"<b>Cidade:</b> {cidade}\n"
            f"<b>Bairro:</b> {bairro}\n"
            f"<b>Rua:</b> {endereco_logradouro}\n"
            f"<b>Número:</b> {endereco_numero}\n"
            f"⚠️<b>Motivo:</b> {os_motivo_descricao}\n\n"
        )

    return mensagem