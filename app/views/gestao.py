from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime
from app import db
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.models.lancamento import Lancamento
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.services.calculo_bi import CalculoBI

gestao_bp = Blueprint('gestao', __name__)

@gestao_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard de Gestão com restrição rigorosa de acesso por perfil e setor.
    Coordenadores só podem visualizar dados de seus próprios setores autorizados.
    """
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso exclusivo para Gestores e Coordenadores.', 'warning')
        return redirect(url_for('operacao.painel'))

    setor_id = request.args.get('setor_id', type=int)
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    status_sla_filtro = request.args.get('status_sla')

    # Regra de Negócio de Setores para Coordenador
    if current_user.is_coordenador and not current_user.is_gestor:
        setores_permitidos_ids = current_user.todos_setores_ids
        if setor_id and setor_id not in setores_permitidos_ids:
            flash('Acesso negado a este setor. Você só pode visualizar os setores autorizados em seu cadastro.', 'danger')
            return redirect(url_for('gestao.dashboard', setor_id=current_user.setor_id))

    query = Lancamento.query.join(Usuario, Lancamento.usuario_id == Usuario.id)

    if setor_id:
        query = query.filter(Lancamento.setor_id == setor_id)
    elif current_user.is_coordenador and not current_user.is_gestor:
        query = query.filter(Lancamento.setor_id.in_(current_user.todos_setores_ids))

    if data_inicio_str:
        try:
            dt_inc = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            query = query.filter(Lancamento.data_programada >= dt_inc)
        except ValueError:
            pass

    if data_fim_str:
        try:
            dt_fm = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            query = query.filter(Lancamento.data_programada <= dt_fm)
        except ValueError:
            pass

    lancamentos_filtrados = query.all()

    total_minutos = sum(l.duracao_minutos for l in lancamentos_filtrados)
    total_horas = round(total_minutos / 60, 1)

    eficiencias = [l.eficiencia_percentual for l in lancamentos_filtrados if l.eficiencia_percentual is not None]
    media_eficiencia = round(sum(eficiencias) / len(eficiencias), 2) if eficiencias else 0.0

    if setor_id:
        total_usuarios = Usuario.query.filter_by(setor_id=setor_id).count()
    elif current_user.is_coordenador and not current_user.is_gestor:
        total_usuarios = Usuario.query.filter(Usuario.setor_id.in_(current_user.todos_setores_ids)).count()
    else:
        total_usuarios = Usuario.query.count()

    total_setores = Setor.query.count()
    total_atividades = AtividadePadrao.query.count()

    # Filtragem estrita da lista de setores visíveis no combo de acordo com o perfil
    if current_user.is_coordenador and not current_user.is_gestor:
        setores_list = Setor.query.filter(Setor.id.in_(current_user.todos_setores_ids)).order_by(Setor.nome.asc()).all()
    else:
        setores_list = Setor.query.order_by(Setor.nome.asc()).all()

    atividades_query = AtividadePadrao.query
    if setor_id:
        atividades_query = atividades_query.filter_by(setor_id=setor_id)
    elif current_user.is_coordenador and not current_user.is_gestor:
        atividades_query = atividades_query.filter(AtividadePadrao.setor_id.in_(current_user.todos_setores_ids))

    atividades_totais = atividades_query.all()
    status_sla_counts = {
        'Concluído': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Em Andamento') == 'Concluído'),
        'Em Andamento': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Em Andamento') == 'Em Andamento'),
        'Cancelado': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Em Andamento') == 'Cancelado')
    }

    labels_eficiencia_setor = []
    data_eficiencia_setor = []
    for s in setores_list:
        if setor_id and s.id != setor_id:
            continue
        q_s = db.session.query(func.avg(Lancamento.eficiencia_percentual)).filter(Lancamento.setor_id == s.id)
        if data_inicio_str:
            q_s = q_s.filter(Lancamento.data_programada >= datetime.strptime(data_inicio_str, '%Y-%m-%d').date())
        if data_fim_str:
            q_s = q_s.filter(Lancamento.data_programada <= datetime.strptime(data_fim_str, '%Y-%m-%d').date())
        val_s = q_s.scalar() or 0.0
        labels_eficiencia_setor.append(s.sigla)
        data_eficiencia_setor.append(round(val_s, 1))

    meses_labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    data_eficiencia_mensal = []
    meta_eficiencia_linha = [100.0] * 12
    ano_atual = datetime.now().year
    for mes in range(1, 13):
        q_mes = db.session.query(func.avg(Lancamento.eficiencia_percentual))\
            .filter(extract('year', Lancamento.data_programada) == ano_atual)\
            .filter(extract('month', Lancamento.data_programada) == mes)
        if setor_id:
            q_mes = q_mes.filter(Lancamento.setor_id == setor_id)
        elif current_user.is_coordenador and not current_user.is_gestor:
            q_mes = q_mes.filter(Lancamento.setor_id.in_(current_user.todos_setores_ids))
        val_m = q_mes.scalar() or 0.0
        data_eficiencia_mensal.append(round(val_m, 1))

    labels_pessoas = []
    data_pessoas = []
    for s in setores_list:
        c = s.usuarios.count()
        if c > 0:
            labels_pessoas.append(s.sigla)
            data_pessoas.append(c)

    ranking = db.session.query(
        Setor.sigla,
        func.sum(Lancamento.duracao_minutos).label('total_min')
    ).join(Lancamento, Lancamento.setor_id == Setor.id)
    if current_user.is_coordenador and not current_user.is_gestor:
        ranking = ranking.filter(Setor.id.in_(current_user.todos_setores_ids))
    ranking = ranking.group_by(Setor.id)\
     .order_by(func.sum(Lancamento.duracao_minutos).desc())\
     .limit(5).all()

    return render_template(
        'admin/dashboard_global.html',
        setores=setores_list,
        filtro_setor_id=setor_id,
        filtro_data_inicio=data_inicio_str or '',
        filtro_data_fim=data_fim_str or '',
        filtro_status_sla=status_sla_filtro or '',
        kpis={
            'horas': CalculoBI.formatar_numero_br(total_horas, 1),
            'eficiencia': CalculoBI.formatar_porcentagem_br(media_eficiencia, 2),
            'usuarios': CalculoBI.formatar_numero_br(total_usuarios, 0),
            'setores': CalculoBI.formatar_numero_br(total_setores, 0),
            'rotinas': CalculoBI.formatar_numero_br(total_atividades, 0)
        },
        status_sla_counts=status_sla_counts,
        chart_pessoas={'labels': labels_pessoas, 'data': data_pessoas},
        chart_eficiencia={'labels': meses_labels, 'data': data_eficiencia_mensal, 'meta': meta_eficiencia_linha},
        chart_efic_setor={'labels': labels_eficiencia_setor, 'data': data_eficiencia_setor},
        ranking=ranking,
        CalculoBI=CalculoBI
    )

@gestao_bp.route('/atividades')
@login_required
def listar_atividades():
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso restrito à gestão de atividades.', 'warning')
        return redirect(url_for('operacao.painel'))

    page = request.args.get('page', 1, type=int)

    if current_user.is_admin or current_user.is_gestor:
        query = AtividadePadrao.query.order_by(AtividadePadrao.titulo.asc())
    else:
        setores_permitidos_ids = current_user.todos_setores_ids
        query = AtividadePadrao.query.filter(AtividadePadrao.setor_id.in_(setores_permitidos_ids)).order_by(AtividadePadrao.titulo.asc())

    atividades_pagination = query.paginate(page=page, per_page=10, error_out=False)
    
    if current_user.is_coordenador and not current_user.is_gestor:
        setores = Setor.query.filter(Setor.id.in_(current_user.todos_setores_ids)).order_by(Setor.nome.asc()).all()
    else:
        setores = Setor.query.order_by(Setor.nome.asc()).all()

    return render_template(
        'coordenador/gerenciar_atividades.html',
        atividades=atividades_pagination.items,
        pagination=atividades_pagination,
        setores=setores,
        CalculoBI=CalculoBI
    )

@gestao_bp.route('/atividade/nova', methods=['POST'])
@login_required
def nova_atividade():
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('operacao.painel'))

    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    setor_id = request.form.get('setor_id', type=int) or current_user.setor_id
    
    if current_user.is_coordenador and not current_user.is_gestor:
        if setor_id not in current_user.todos_setores_ids:
            flash('Você não tem permissão para cadastrar atividades em um setor não autorizado.', 'danger')
            return redirect(url_for('gestao.listar_atividades'))

    tempo_valor = request.form.get('tempo_estimado_valor', type=int) or 0
    tempo_unidade = request.form.get('tempo_estimado_unidade', 'minutos')
    status_sla = request.form.get('status_sla', 'Em Andamento')

    if not titulo:
        flash('O título da atividade é obrigatório.', 'danger')
        return redirect(url_for('gestao.listar_atividades'))

    atv = AtividadePadrao(
        titulo=titulo,
        descricao=descricao,
        setor_id=setor_id,
        tempo_estimado_valor=tempo_valor,
        tempo_estimado_unidade=tempo_unidade,
        status_sla=status_sla,
        is_rotineira=True
    )
    atv.atualizar_tempo()

    db.session.add(atv)
    db.session.commit()
    flash('Atividade cadastrada com sucesso!', 'success')
    return redirect(url_for('gestao.listar_atividades'))

@gestao_bp.route('/atividade/editar/<int:id>', methods=['POST'])
@login_required
def editar_atividade(id):
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('operacao.painel'))

    atv = AtividadePadrao.query.get_or_404(id)
    if current_user.is_coordenador and not current_user.is_gestor:
        if atv.setor_id not in current_user.todos_setores_ids:
            flash('Acesso negado a esta atividade.', 'danger')
            return redirect(url_for('gestao.listar_atividades'))

    atv.titulo = request.form.get('titulo', '').strip() or atv.titulo
    atv.descricao = request.form.get('descricao', '').strip()
    atv.setor_id = request.form.get('setor_id', type=int) or atv.setor_id
    atv.tempo_estimado_valor = request.form.get('tempo_estimado_valor', type=int) or atv.tempo_estimado_valor
    atv.tempo_estimado_unidade = request.form.get('tempo_estimado_unidade') or atv.tempo_estimado_unidade
    atv.status_sla = request.form.get('status_sla') or atv.status_sla
    atv.atualizar_tempo()

    db.session.commit()
    flash('Atividade atualizada com sucesso!', 'success')
    return redirect(url_for('gestao.listar_atividades'))