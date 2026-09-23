import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from app.services.calculo_bi import CalculoBI

class ExportacaoPDFService:
    """
    Serviço corporativo de geração de relatórios operacionais em formato PDF.
    Estruturado em orientação paisagem com tabelas paginadas e métricas resumidas.
    """

    @staticmethod
    def gerar_relatorio_pdf(lancamentos, periodo_str="Geral", setor_nome="Todos os Setores", usuario_nome="Todos os Colaboradores"):
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(letter),
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#0B2545'),
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=12
        )

        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A')
        )

        cell_header_style = ParagraphStyle(
            'TableHeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1
        )

        # Cabeçalho
        elements.append(Paragraph("GEROT — Relatório Consolidado de Gestão Operacional", title_style))
        subtitulo = f"Período: <b>{periodo_str}</b> | Setor: <b>{setor_nome}</b> | Colaborador: <b>{usuario_nome}</b> | Emitido em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        elements.append(Paragraph(subtitulo, subtitle_style))

        # Sumário de Produção
        total_minutos = sum(l.duracao_minutos for l in lancamentos)
        total_horas = round(total_minutos / 60, 1)
        eficiencias = [l.eficiencia_percentual for l in lancamentos if l.eficiencia_percentual is not None]
        media_efic = round(sum(eficiencias) / len(eficiencias), 1) if eficiencias else 0.0

        resumo_data = [
            [
                Paragraph("<b>Total de Horas Úteis:</b>", cell_style),
                Paragraph(f"{CalculoBI.formatar_numero_br(total_horas, 1)}h", cell_style),
                Paragraph("<b>Eficiência Média:</b>", cell_style),
                Paragraph(CalculoBI.formatar_porcentagem_br(media_efic, 1), cell_style),
                Paragraph("<b>Total Entregas:</b>", cell_style),
                Paragraph(CalculoBI.formatar_numero_br(len(lancamentos), 0), cell_style)
            ]
        ]
        tabela_resumo = Table(resumo_data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 1.2*inch, 1.5*inch, 1.2*inch])
        tabela_resumo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(tabela_resumo)
        elements.append(Spacer(1, 14))

        # Tabela de Lançamentos
        headers = [
            Paragraph("Data", cell_header_style),
            Paragraph("Colaborador", cell_header_style),
            Paragraph("Setor", cell_header_style),
            Paragraph("Atividade Executada", cell_header_style),
            Paragraph("Duração Útil", cell_header_style),
            Paragraph("Eficiência", cell_header_style),
            Paragraph("SLA", cell_header_style),
            Paragraph("Anexos", cell_header_style)
        ]
        table_rows = [headers]

        for l in lancamentos:
            dt_str = l.data_programada.strftime('%d/%m/%Y') if l.data_programada else ''
            autor_str = l.autor.nome_completo if l.autor else 'N/A'
            setor_str = l.setor_snapshot.sigla if l.setor_snapshot else 'N/A'
            atv_str = l.atividade_referencia.titulo if l.atividade_referencia else 'N/A'
            dur_str = f"{CalculoBI.formatar_numero_br(l.duracao_minutos, 0)} min"
            efic_str = CalculoBI.formatar_porcentagem_br(l.eficiencia_percentual, 1) if l.eficiencia_percentual is not None else '0,0%'
            sla_str = "No Prazo" if l.dentro_do_prazo else "Atrasado"
            qtd_anexos = str(l.total_anexos)

            table_rows.append([
                Paragraph(dt_str, cell_style),
                Paragraph(autor_str, cell_style),
                Paragraph(setor_str, cell_style),
                Paragraph(atv_str, cell_style),
                Paragraph(dur_str, cell_style),
                Paragraph(efic_str, cell_style),
                Paragraph(sla_str, cell_style),
                Paragraph(qtd_anexos, cell_style)
            ])

        col_widths = [0.8*inch, 1.8*inch, 0.8*inch, 2.7*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.6*inch]
        tabela_dados = Table(table_rows, colWidths=col_widths, repeatRows=1)
        tabela_dados.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B2545')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(tabela_dados)

        doc.build(elements)
        output.seek(0)
        return output