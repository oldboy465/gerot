from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, send_file
from flask_login import login_required, current_user
from datetime import datetime
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.models.lancamento import Lancamento
from app.models.atividade import AtividadePadrao
from app.services.calculo_bi import CalculoBI
from app.services.exportacao import ExportacaoService
from app.services.exportacao_pptx import ExportacaoPPTXService

relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.route('/')
@login_required
def index():
    """
    Central de Relatórios de Produção com visualização e download de evidências.
    Respeita estritamente o isolamento de setores autorizados para coordenadores.
    """
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso restrito à gestão de relatórios.', 'warning')
        return redirect(url_for('operacao.painel'))

    page = request.args.get('page', 1, type=int)
    setor_id = request.args.get('setor_id', type=int)
    usuario_id = request.args.get('usuario_id', type=int)
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    status_prazo = request.args.get('status_prazo')
    export_action = request.args.get('export')

    # Regra de Negócio de Setores para Coordenador
    if current_user.is_coordenador and not current_user.is_gestor:
        setores_permitidos_ids = current_user.todos_setores_ids
        if setor_id and setor_id not in setores_permitidos_ids:
            flash('Acesso negado a este setor nos relatórios.', 'danger')
            return redirect(url_for('relatorios.index', setor_id=current_user.setor_id))

    query = Lancamento.query.join(Usuario, Lancamento.usuario_id == Usuario.id)

    if setor_id:
        query = query.filter(Lancamento.setor_id == setor_id)
    elif current_user.is_coordenador and not current_user.is_gestor:
        query = query.filter(Lancamento.setor_id.in_(current_user.todos_setores_ids))

    if usuario_id:
        query = query.filter(Lancamento.usuario_id == usuario_id)

    if data_inicio_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            query = query.filter(Lancamento.data_programada >= dt_inicio)
        except ValueError:
            pass

    if data_fim_str:
        try:
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            query = query.filter(Lancamento.data_programada <= dt_fim)
        except ValueError:
            pass

    if status_prazo == 'no_prazo':
        query = query.filter(Lancamento.dentro_do_prazo == True)
    elif status_prazo == 'atrasado':
        query = query.filter(Lancamento.dentro_do_prazo == False)

    query = query.order_by(Lancamento.data_hora_inicio.desc())

    if export_action == 'excel':
        return ExportacaoService.gerar_excel(query.all())
    elif export_action == 'whatsapp':
        periodo_str = f"{data_inicio_str or 'Início'} até {data_fim_str or 'Hoje'}"
        setor_nome = Setor.query.get(setor_id).nome if setor_id else "Todos os Setores Autorizados"
        usuario_nome = Usuario.query.get(usuario_id).nome_completo if usuario_id else "Todos"

        texto_wa = ExportacaoService.gerar_texto_whatsapp(
            query.all(), periodo_str, setor_nome, usuario_nome
        )
        return Response(texto_wa, mimetype='text/plain')

    pagination = query.paginate(page=page, per_page=10, error_out=False)

    if current_user.is_coordenador and not current_user.is_gestor:
        setores = Setor.query.filter(Setor.id.in_(current_user.todos_setores_ids)).order_by(Setor.nome.asc()).all()
        usuarios = Usuario.query.filter(Usuario.setor_id.in_(current_user.todos_setores_ids), Usuario.ativo==True).order_by(Usuario.nome_completo.asc()).all()
    else:
        setores = Setor.query.order_by(Setor.nome.asc()).all()
        usuarios = Usuario.query.filter_by(ativo=True).order_by(Usuario.nome_completo.asc()).all()

    return render_template(
        'relatorios/index.html',
        lancamentos=pagination.items,
        pagination=pagination,
        setores=setores,
        usuarios=usuarios,
        filtro_setor_id=setor_id,
        filtro_usuario_id=usuario_id,
        filtro_data_inicio=data_inicio_str or '',
        filtro_data_fim=data_fim_str or '',
        filtro_status_prazo=status_prazo or '',
        CalculoBI=CalculoBI
    )

@relatorios_bp.route('/gerar-pptx', methods=['GET'])
@login_required
def gerar_pptx():
    """
    Função exclusiva para coordenadores, gestores e administradores gerarem
    relatórios em PowerPoint (.pptx) vinculados aos filtros aplicados, respeitando setores permitidos.
    """
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso restrito para geração de relatórios executivos em PowerPoint.', 'danger')
        return redirect(url_for('operacao.painel'))

    setor_id = request.args.get('setor_id', type=int)
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    status_prazo = request.args.get('status_prazo')

    if current_user.is_coordenador and not current_user.is_gestor:
        setores_permitidos_ids = current_user.todos_setores_ids
        if setor_id and setor_id not in setores_permitidos_ids:
            flash('Acesso negado para gerar PowerPoint deste setor.', 'danger')
            return redirect(url_for('relatorios.index'))

    query = Lancamento.query.join(Usuario, Lancamento.usuario_id == Usuario.id)

    if setor_id:
        query = query.filter(Lancamento.setor_id == setor_id)
    elif current_user.is_coordenador and not current_user.is_gestor:
        query = query.filter(Lancamento.setor_id.in_(current_user.todos_setores_ids))

    if data_inicio_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            query = query.filter(Lancamento.data_programada >= dt_inicio)
        except ValueError:
            pass

    if data_fim_str:
        try:
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            query = query.filter(Lancamento.data_programada <= dt_fim)
        except ValueError:
            pass

    if status_prazo == 'no_prazo':
        query = query.filter(Lancamento.dentro_do_prazo == True)
    elif status_prazo == 'atrasado':
        query = query.filter(Lancamento.dentro_do_prazo == False)

    lancamentos = query.all()

    total_minutos = sum(l.duracao_minutos for l in lancamentos)
    total_horas = round(total_minutos / 60, 1)
    eficiencias = [l.eficiencia_percentual for l in lancamentos if l.eficiencia_percentual is not None]
    media_eficiencia = round(sum(eficiencias) / len(eficiencias), 2) if eficiencias else 0.0

    if setor_id:
        total_usuarios = Usuario.query.filter_by(setor_id=setor_id).count()
    elif current_user.is_coordenador and not current_user.is_gestor:
        total_usuarios = Usuario.query.filter(Usuario.setor_id.in_(current_user.todos_setores_ids)).count()
    else:
        total_usuarios = Usuario.query.count()

    total_atividades = AtividadePadrao.query.count()

    kpis = {
        'horas': CalculoBI.formatar_numero_br(total_horas, 1) + "h",
        'eficiencia': CalculoBI.formatar_porcentagem_br(media_eficiencia, 2),
        'usuarios': CalculoBI.formatar_numero_br(total_usuarios, 0),
        'rotinas': CalculoBI.formatar_numero_br(total_atividades, 0)
    }

    atividades_query = AtividadePadrao.query
    if setor_id:
        atividades_query = atividades_query.filter_by(setor_id=setor_id)
    elif current_user.is_coordenador and not current_user.is_gestor:
        atividades_query = atividades_query.filter(AtividadePadrao.setor_id.in_(current_user.todos_setores_ids))

    atividades_totais = atividades_query.all()
    status_counts = {
        'Concluído': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Em Andamento') == 'Concluído'),
        'Em Andamento': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Em Andamento') == 'Em Andamento'),
        'Cancelado': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Em Andamento') == 'Cancelado')
    }

    setor_nome = Setor.query.get(setor_id).nome if setor_id else "Visão Consolidada de Setores Autorizados"
    emissor_nome = current_user.nome_completo

    ppt_stream = ExportacaoPPTXService.gerar_apresentacao_completa(
        emissor_nome=emissor_nome,
        kpis=kpis,
        lancamentos=lancamentos,
        status_counts=status_counts,
        setor_nome=setor_nome
    )

    filename = f"gerot_relatorio_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    return send_file(
        ppt_stream,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        as_attachment=True,
        download_name=filename
    )