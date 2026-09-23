import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime
from werkzeug.utils import secure_filename
from app import db
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.models.lancamento import Lancamento
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.anexo import AnexoLancamento
from app.services.calculo_bi import CalculoBI

gestao_bp = Blueprint('gestao', __name__)

def arquivo_permitido(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def parse_datetime_input(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str.strip(), '%Y-%m-%dT%H:%M')
    except ValueError:
        try:
            return datetime.strptime(dt_str.strip(), '%Y-%m-%d %H:%M')
        except ValueError:
            return None

@gestao_bp.route('/dashboard')
@login_required
def dashboard():
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso exclusivo para Diretores e Líderes.', 'warning')
        return redirect(url_for('operacao.painel'))

    setor_id = request.args.get('setor_id', type=int)
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    status_sla_filtro = request.args.get('status_sla')

    if current_user.is_coordenador and not current_user.is_gestor:
        setores_permitidos_ids = current_user.todos_setores_ids
        if setor_id and setor_id not in setores_permitidos_ids:
            flash('Acesso restrito aos setores sob sua liderança.', 'danger')
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
        'Não Iniciado': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Não Iniciado') == 'Não Iniciado'),
        'Em Andamento': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Não Iniciado') == 'Em Andamento'),
        'Concluído': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Não Iniciado') == 'Concluído'),
        'Cancelado': sum(1 for a in atividades_totais if getattr(a, 'status_sla', 'Não Iniciado') == 'Cancelado')
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
    """Catálogo de Rotinas e Serviços com filtragem por status oficial e setor."""
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso restrito à gestão de rotinas.', 'warning')
        return redirect(url_for('operacao.painel'))

    page = request.args.get('page', 1, type=int)
    setor_id = request.args.get('setor_id', type=int)
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    status_sla = request.args.get('status_sla')

    if current_user.is_admin or current_user.is_gestor:
        query = AtividadePadrao.query
    else:
        setores_permitidos_ids = current_user.todos_setores_ids
        query = AtividadePadrao.query.filter(AtividadePadrao.setor_id.in_(setores_permitidos_ids))

    if setor_id:
        query = query.filter(AtividadePadrao.setor_id == setor_id)

    if status_sla and status_sla != 'Todos':
        query = query.filter(AtividadePadrao.status_sla == status_sla)

    if data_inicio_str or data_fim_str:
        query = query.join(Lancamento, AtividadePadrao.id == Lancamento.atividade_id)
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
        query = query.distinct()

    query = query.order_by(AtividadePadrao.titulo.asc())
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
        filtro_setor_id=setor_id,
        filtro_data_inicio=data_inicio_str or '',
        filtro_data_fim=data_fim_str or '',
        filtro_status_sla=status_sla or 'Todos',
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
            flash('Você não tem permissão para cadastrar rotinas fora dos seus setores.', 'danger')
            return redirect(url_for('gestao.listar_atividades'))

    tempo_valor = request.form.get('tempo_estimado_valor', type=int) or 0
    tempo_unidade = request.form.get('tempo_estimado_unidade', 'minutos')
    status_sla = request.form.get('status_sla', 'Não Iniciado')

    # Coleta os novos campos de previsão de início e término
    dt_inicio_prev = parse_datetime_input(request.form.get('data_inicio_prevista'))
    dt_fim_prev = parse_datetime_input(request.form.get('data_fim_prevista'))

    if dt_inicio_prev and dt_fim_prev and dt_fim_prev <= dt_inicio_prev:
        flash('Aviso: O prazo de término previsto deve ser posterior ao início previsto.', 'warning')

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
        data_inicio_prevista=dt_inicio_prev,
        data_fim_prevista=dt_fim_prev,
        is_rotineira=True
    )
    atv.atualizar_tempo()

    db.session.add(atv)
    db.session.commit()
    flash('Atividade/Rotina cadastrada com sucesso!', 'success')
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

    novo_setor_id = request.form.get('setor_id', type=int)
    if novo_setor_id:
        if current_user.is_coordenador and not current_user.is_gestor:
            if novo_setor_id in current_user.todos_setores_ids:
                atv.setor_id = novo_setor_id
        else:
            atv.setor_id = novo_setor_id

    atv.tempo_estimado_valor = request.form.get('tempo_estimado_valor', type=int) or atv.tempo_estimado_valor
    atv.tempo_estimado_unidade = request.form.get('tempo_estimado_unidade') or atv.tempo_estimado_unidade
    atv.status_sla = request.form.get('status_sla') or atv.status_sla

    # Atualiza prazos estimados se fornecidos
    if 'data_inicio_prevista' in request.form:
        atv.data_inicio_prevista = parse_datetime_input(request.form.get('data_inicio_prevista'))
    if 'data_fim_prevista' in request.form:
        atv.data_fim_prevista = parse_datetime_input(request.form.get('data_fim_prevista'))

    atv.atualizar_tempo()

    db.session.commit()
    flash('Rotina atualizada com sucesso!', 'success')
    return redirect(url_for('gestao.listar_atividades'))

@gestao_bp.route('/atividade/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_atividade(id):
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('operacao.painel'))

    atv = AtividadePadrao.query.get_or_404(id)
    if current_user.is_coordenador and not current_user.is_gestor:
        if atv.setor_id not in current_user.todos_setores_ids:
            flash('Acesso negado para remover esta rotina.', 'danger')
            return redirect(url_for('gestao.listar_atividades'))

    try:
        Lancamento.query.filter_by(atividade_id=atv.id).delete(synchronize_session=False)
        db.session.delete(atv)
        db.session.commit()
        flash('Rotina removida com sucesso.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir rotina: {str(e)}', 'danger')

    return redirect(url_for('gestao.listar_atividades'))

@gestao_bp.route('/atividade/concluir/<int:id>', methods=['POST'])
@login_required
def concluir_atividade(id):
    """
    Permite ao Líder/Coordenador concluir uma rotina diretamente, anexando
    documentos de evidência comprobatória e gerando o log de produção.
    """
    if not (current_user.is_gestor or current_user.is_coordenador or current_user.is_admin):
        flash('Acesso restrito para conclusão direta de atividades.', 'danger')
        return redirect(url_for('gestao.listar_atividades'))

    atv = AtividadePadrao.query.get_or_404(id)
    if current_user.is_coordenador and not current_user.is_gestor:
        if atv.setor_id not in current_user.todos_setores_ids:
            flash('Você só pode concluir atividades pertencentes aos setores autorizados.', 'danger')
            return redirect(url_for('gestao.listar_atividades'))

    try:
        duracao = request.form.get('duracao_minutos', type=int) or atv.tempo_convertido_minutos or 30
        obs = request.form.get('observacoes', 'Conclusão efetuada diretamente pela Liderança do Setor.')
        agora = datetime.utcnow()

        novo_lancamento = Lancamento(
            usuario_id=current_user.id,
            setor_id=atv.setor_id,
            atividade_id=atv.id,
            tarefa_id=None,
            data_hora_inicio=agora,
            data_hora_fim=agora,
            duracao_minutos=max(1, duracao),
            eficiencia_percentual=100.0,
            dentro_do_prazo=True,
            observacoes=obs,
            data_programada=agora.date(),
            data_registro=agora
        )
        db.session.add(novo_lancamento)
        db.session.flush()

        # Upload opcional de evidências no ato de conclusão
        arquivos = request.files.getlist('arquivos_evidencia') or request.files.getlist('arquivo_evidencia')
        anexos_count = 0
        for file in arquivos:
            if file and file.filename != '':
                if arquivo_permitido(file.filename):
                    nome_original = secure_filename(file.filename)
                    ext = nome_original.rsplit('.', 1)[1].lower() if '.' in nome_original else ''
                    filename_salvo = f"lider_{novo_lancamento.id}_{uuid.uuid4().hex[:8]}.{ext}"
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_salvo)
                    file.save(upload_path)
                    
                    anexo_obj = AnexoLancamento(
                        lancamento_id=novo_lancamento.id,
                        arquivo_salvo=filename_salvo,
                        nome_original=nome_original,
                        extensao=ext,
                        tamanho_bytes=os.path.getsize(upload_path) if os.path.exists(upload_path) else 0
                    )
                    db.session.add(anexo_obj)
                    if anexos_count == 0:
                        novo_lancamento.arquivo_evidencia = filename_salvo
                        novo_lancamento.nome_original_arquivo = nome_original
                    anexos_count += 1

        atv.status_sla = 'Concluído'
        db.session.commit()
        flash(f'Atividade "{atv.titulo}" concluída e registrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao concluir atividade: {str(e)}', 'danger')

    return redirect(url_for('gestao.listar_atividades'))

@gestao_bp.route('/lancamento/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_lancamento(id):
    if current_user.is_operador:
        flash('Colaboradores não possuem permissão para excluir apontamentos. Solicite ao seu Líder.', 'danger')
        return redirect(url_for('operacao.historico'))

    lanc = Lancamento.query.get_or_404(id)
    if current_user.is_coordenador and not current_user.is_gestor:
        if lanc.setor_id not in current_user.todos_setores_ids:
            flash('Você só pode excluir lançamentos dos setores autorizados.', 'danger')
            return redirect(url_for('gestao.dashboard'))

    try:
        db.session.delete(lanc)
        db.session.commit()
        flash('Lançamento excluído com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir lançamento: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('gestao.dashboard'))