import pandas as pd
import io
from flask import Response

class ExportacaoService:
    """
    Serviço responsável por gerar extrações e relatórios do sistema GEROT.
    """
    
    @staticmethod
    def gerar_excel(lancamentos):
        """Gera um arquivo .xlsx real usando Pandas e BytesIO em memória."""
        data = []
        for l in lancamentos:
            data.append({
                'ID': l.id,
                'Data Competência': l.data_programada.strftime('%d/%m/%Y') if l.data_programada else '',
                'Colaborador': l.autor.nome_completo if l.autor else 'N/A',
                'Cargo': l.autor.cargo if l.autor else 'N/A',
                'Setor': l.setor_snapshot.nome if l.setor_snapshot else 'N/A',
                'Atividade Executada': l.atividade_referencia.titulo if l.atividade_referencia else 'N/A',
                'Data/Hora Início': l.data_hora_inicio.strftime('%d/%m/%Y %H:%M') if l.data_hora_inicio else '',
                'Data/Hora Fim': l.data_hora_fim.strftime('%d/%m/%Y %H:%M') if l.data_hora_fim else '',
                'Duração (Minutos)': l.duracao_minutos,
                'Eficiência (%)': f"{l.eficiencia_percentual:.1f}%" if l.eficiencia_percentual else '0.0%',
                'SLA Atendido': 'Sim' if l.dentro_do_prazo else 'Não',
                'Observações / Cronologia': l.observacoes or ''
            })
        
        df = pd.DataFrame(data)
        
        # Salva o dataframe em memória no formato Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Produção')
        output.seek(0)
        
        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-disposition": "attachment; filename=gerot_relatorio_producao.xlsx"}
        )

    @staticmethod
    def gerar_texto_whatsapp(lancamentos, periodo_str, setor_nome, usuario_nome):
        """Gera um texto formatado em Markdown do WhatsApp pronto para copiar e colar."""
        if not lancamentos:
            return "Nenhum dado encontrado para os filtros selecionados."

        # Cálculos rápidos para o resumo
        total_minutos = sum(l.duracao_minutos for l in lancamentos)
        horas = round(total_minutos / 60, 1)
        eficiencias = [l.eficiencia_percentual for l in lancamentos if l.eficiencia_percentual]
        media_efic = round(sum(eficiencias) / len(eficiencias), 1) if eficiencias else 0

        texto = f"*📊 RELATÓRIO DE PRODUÇÃO - GEROT*\n"
        texto += f"📅 *Período:* {periodo_str}\n"
        if setor_nome:
            texto += f"🏢 *Setor:* {setor_nome}\n"
        if usuario_nome:
            texto += f"👤 *Colaborador:* {usuario_nome}\n"
        
        texto += f"\n*RESUMO DA PRODUÇÃO:*\n"
        texto += f"⏱️ *Total de Horas:* {horas}h\n"
        texto += f"📈 *Eficiência Média:* {media_efic}%\n"
        texto += f"✅ *Tarefas Concluídas:* {len(lancamentos)}\n"

        texto += f"\n*ÚLTIMAS ENTREGAS:*\n"
        # Limita a 10 para não travar a visualização no chat
        for l in lancamentos[:10]:
            data_str = l.data_programada.strftime('%d/%m') if l.data_programada else ''
            titulo_curto = l.atividade_referencia.titulo[:35] + '...' if len(l.atividade_referencia.titulo) > 35 else l.atividade_referencia.titulo
            texto += f"▫️ {data_str} - {titulo_curto} ({l.duracao_minutos} min)\n"
        
        if len(lancamentos) > 10:
            texto += f"\n_...e mais {len(lancamentos) - 10} registros ocultos na mensagem._"

        return texto