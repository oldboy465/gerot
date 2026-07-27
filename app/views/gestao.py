from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.lancamento import Lancamento
from app.models.usuario import Usuario
from app.models.setor import Setor

gestao_bp = Blueprint('gestao', __name__)

@gestao_bp.before_request
@login_required
def check_permission():
    if current_user.role not in ['admin', 'gestor', 'coordenador']:
        flash('Acesso restrito à gestão.', 'danger')
        return redirect(url_for('operacao.painel'))

@gestao_bp.route('/dashboard')
def dashboard():
    setor_id = request.args.get('setor_id', type=int) or current_user.setor_id
    
    if setor_id != current_user.setor_id and not (current_user.is_admin or current_user.is_gestor):
        flash('Acesso negado ao setor solicitado.', 'danger')
        setor_id = current_user.setor_id

    minutos_setor = db.session.query(func.sum(Lancamento.duracao_minutos))\
        .filter(Lancamento.setor_id == setor_id).scalar() or 0
    horas_setor = round(minutos_setor / 60, 1)

    total_equipe = Usuario.query.filter_by(setor_id=setor_id, ativo=True).count()

    correcoes = Lancamento.query.filter_by(
        setor_id=setor_id, 
        correcao_solicitada=True
    ).all()
    
    setores = Setor.query.all() if (current_user.is_admin or current_user.is_gestor) else []

    return render_template('coordenador/dashboard_setor.html',
                           stats={'horas': horas_setor, 'equipe': total_equipe},
                           correcoes=correcoes,
                           setores=setores,
                           setor_atual=setor_id)

@gestao_bp.route('/atividades')
def listar_atividades():
    setor_id = request.args.get('setor_id', type=int) or current_user.setor_id
    
    if setor_id != current_user.setor_id and not (current_user.is_admin or current_user.is_gestor):
        flash('Acesso negado ao setor solicitado.', 'danger')
        setor_id = current_user.setor_id

    atividades = AtividadePadrao.query.filter_by(setor_id=setor_id).all()
    usuarios_setor = Usuario.query.filter_by(setor_id=setor_id, ativo=True).all()
    setores = Setor.query.all() if (current_user.is_admin or current_user.is_gestor) else []
    
    return render_template('coordenador/gerenciar_atividades.html', 
                           atividades=atividades, 
                           usuarios=usuarios_setor,
                           setores=setores,
                           setor_atual=setor_id)

@gestao_bp.route('/atividade/nova', methods=['POST'])
def nova_atividade():
    try:
        responsavel_id = request.form.get('responsavel_id')
        setor_req = request.form.get('setor_id', type=int)
        
        setor_id = current_user.setor_id
        if setor_req and (current_user.is_admin or current_user.is_gestor):
            setor_id = setor_req
        
        nova_atv = AtividadePadrao(
            titulo=request.form.get('titulo'),
            descricao=request.form.get('descricao'),
            setor_id=setor_id,
            responsavel_id=int(responsavel_id) if responsavel_id else None,
            is_rotineira=True if request.form.get('is_rotineira') else False,
            tempo_estimado_valor=int(request.form.get('tempo_valor')),
            tempo_estimado_unidade=request.form.get('tempo_unidade') 
        )
        
        db.session.add(nova_atv)
        db.session.commit()
        flash('Atividade cadastrada com sucesso.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar: {str(e)}', 'danger')
        
    return redirect(url_for('gestao.listar_atividades', setor_id=setor_id))

@gestao_bp.route('/atividade/excluir/<int:id>')
def excluir_atividade(id):
    atv = AtividadePadrao.query.get_or_404(id)
    setor_id = atv.setor_id
    
    if atv.setor_id != current_user.setor_id and not (current_user.is_admin or current_user.is_gestor):
        flash('Você não tem permissão para alterar atividades de outro setor.', 'danger')
        return redirect(url_for('gestao.listar_atividades'))

    try:
        db.session.delete(atv)
        db.session.commit()
        flash('Atividade removida.', 'info')
    except:
        db.session.rollback()
        flash('Não é possível excluir atividades que já possuem lançamentos históricos.', 'warning')
        
    return redirect(url_for('gestao.listar_atividades', setor_id=setor_id))

@gestao_bp.route('/tarefa/nova', methods=['POST'])
def nova_tarefa():
    atividade_id = request.form.get('atividade_id')
    descricao = request.form.get('descricao')
    impacto = request.form.get('impacto_percentual') or 0

    if not atividade_id or not descricao:
        flash('Dados incompletos para criar a tarefa.', 'danger')
        return redirect(url_for('gestao.listar_atividades'))

    try:
        atv = AtividadePadrao.query.get(atividade_id)
        if atv.setor_id != current_user.setor_id and not (current_user.is_admin or current_user.is_gestor):
            flash('Permissão negada.', 'danger')
            return redirect(url_for('gestao.listar_atividades'))

        nova_t = TarefaPadrao(
            atividade_id=atividade_id,
            descricao=descricao,
            impacto_percentual=float(impacto),
            criado_por_id=current_user.id
        )
        
        db.session.add(nova_t)
        db.session.commit()
        flash('Tarefa adicionada à rotina com sucesso.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar tarefa: {str(e)}', 'danger')

    return redirect(url_for('gestao.listar_atividades', setor_id=atv.setor_id if 'atv' in locals() else None))

@gestao_bp.route('/validar/<int:lancamento_id>', methods=['POST'])
def validar_correcao(lancamento_id):
    lancamento = Lancamento.query.get_or_404(lancamento_id)
    
    if lancamento.setor_id != current_user.setor_id and not (current_user.is_admin or current_user.is_gestor):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('gestao.dashboard'))
        
    acao = request.form.get('acao')
    
    if acao == 'aprovar':
        lancamento.correcao_solicitada = False
        lancamento.correcao_aprovada_por = current_user.id
        lancamento.observacoes += f" [Correção Aprovada por {current_user.username}]"
        flash('Correção aprovada.', 'success')
    else:
        lancamento.observacoes += f" [Correção REJEITADA por {current_user.username}]"
        flash('Solicitação rejeitada.', 'warning')
        
    db.session.commit()
    return redirect(url_for('gestao.dashboard', setor_id=lancamento.setor_id))