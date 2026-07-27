from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.usuario import Usuario
from app.models.setor import Setor
from app.models.lancamento import Lancamento
from app.models.atividade import AtividadePadrao

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_gestor):
            flash('Acesso negado. Área exclusiva para a Administração e Gestão Geral.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.before_request
@login_required
@admin_required
def before_request():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    total_minutos = db.session.query(func.sum(Lancamento.duracao_minutos)).scalar() or 0
    total_horas = round(total_minutos / 60, 1)

    media_eficiencia = db.session.query(func.avg(Lancamento.eficiencia_percentual)).scalar() or 0
    media_eficiencia = round(media_eficiencia, 2)

    total_usuarios = Usuario.query.count()
    total_setores = Setor.query.count()
    total_atividades = AtividadePadrao.query.count()

    ranking = db.session.query(
        Setor.sigla,
        func.sum(Lancamento.duracao_minutos).label('total_min')
    ).join(Lancamento, Lancamento.setor_id == Setor.id)\
     .group_by(Setor.id)\
     .order_by(func.sum(Lancamento.duracao_minutos).desc())\
     .limit(5).all()

    return render_template('admin/dashboard_global.html',
                           kpis={
                               'horas': total_horas,
                               'eficiencia': media_eficiencia,
                               'usuarios': total_usuarios,
                               'setores': total_setores,
                               'rotinas': total_atividades
                           },
                           ranking=ranking)

@admin_bp.route('/setores')
def listar_setores():
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template('admin/setores.html', setores=setores)

@admin_bp.route('/setor/editar/<int:id>', methods=['GET', 'POST'])
def editar_setor(id):
    setor = Setor.query.get_or_404(id)
    if request.method == 'POST':
        try:
            setor.nome = request.form.get('nome')
            setor.sigla = request.form.get('sigla').upper()
            setor.hierarquia_pai_id = request.form.get('hierarquia_pai_id') or None
            setor.nivel_complexidade = request.form.get('nivel_complexidade')
            setor.limite_max_colaboradores = int(request.form.get('limite_max') or 0)
            setor.ativo = True if request.form.get('ativo') else False
            
            db.session.commit()
            flash(f'Estrutura do setor {setor.sigla} atualizada.', 'success')
            return redirect(url_for('admin.listar_setores'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar: {str(e)}', 'danger')

    setores_pai = Setor.query.filter(Setor.id != id).all()
    return render_template('admin/form_setor.html', setor=setor, setores_pai=setores_pai)

@admin_bp.route('/setor/excluir/<int:id>', methods=['POST'])
def excluir_setor(id):
    setor = Setor.query.get_or_404(id)
    if setor.sigla == 'ROOT':
        flash('O setor mestre não pode ser removido.', 'danger')
        return redirect(url_for('admin.listar_setores'))
    try:
        db.session.delete(setor)
        db.session.commit()
        flash('Setor removido com sucesso.', 'info')
    except:
        db.session.rollback()
        flash('Não é possível excluir: existem usuários ou lançamentos vinculados.', 'warning')
    return redirect(url_for('admin.listar_setores'))

@admin_bp.route('/setor/novo', methods=['GET', 'POST'])
def novo_setor():
    if request.method == 'POST':
        sigla_input = request.form.get('sigla').upper()
        codigo_input = request.form.get('codigo_interno')
        
        setor_existente = Setor.query.filter(
            (Setor.sigla == sigla_input) | (Setor.codigo_interno == codigo_input)
        ).first()
        
        if setor_existente:
            flash(f'Erro: Já existe um setor cadastrado com a sigla {sigla_input} ou código {codigo_input}.', 'danger')
            return redirect(url_for('admin.novo_setor'))

        try:
            novo_setor = Setor(
                nome=request.form.get('nome'),
                sigla=sigla_input,
                codigo_interno=codigo_input,
                hierarquia_pai_id=request.form.get('hierarquia_pai_id') or None,
                responsavel_id=request.form.get('responsavel_id') or None,
                substituto_id=request.form.get('substituto_id') or None,
                tipo_setor=request.form.get('tipo_setor'),
                natureza_atuacao=request.form.get('natureza_atuacao'),
                missao_setor=request.form.get('missao_setor'),
                descricao_atividades=request.form.get('descricao_atividades'),
                nivel_complexidade=request.form.get('nivel_complexidade'),
                nivel_repetitividade=request.form.get('nivel_repetitividade'),
                limite_max_colaboradores=int(request.form.get('limite_max') or 0),
                cargos_permitidos=request.form.get('cargos_permitidos'),
                turno_operacao=request.form.get('turno_operacao'),
                escala_trabalho=request.form.get('escala_trabalho')
            )
            
            db.session.add(novo_setor)
            db.session.commit()
            flash('Estrutura organizacional atualizada: Setor criado com sucesso!', 'success')
            return redirect(url_for('admin.listar_setores'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro técnico ao processar estrutura: {str(e)}', 'danger')

    setores_hierarquia = Setor.query.order_by(Setor.nome).all()
    possiveis_gestores = Usuario.query.filter(Usuario.role.in_(['admin', 'coordenador', 'gestor'])).all()
    
    return render_template('admin/form_setor.html', 
                           setores_pai=setores_hierarquia,
                           usuarios=possiveis_gestores)

@admin_bp.route('/usuarios')
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nome_completo).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin_bp.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            usuario.nome_completo = request.form.get('nome')
            usuario.email = request.form.get('email')
            usuario.cargo = request.form.get('cargo')
            usuario.setor_id = request.form.get('setor_id')
            usuario.role = request.form.get('role')
            usuario.ativo = True if request.form.get('ativo') else False
            
            nova_senha = request.form.get('nova_senha')
            if nova_senha:
                usuario.set_password(nova_senha)
                flash(f'Senha de {usuario.username} redefinida.', 'info')

            db.session.commit()
            flash(f'Perfil de {usuario.nome_completo} atualizado com sucesso.', 'success')
            return redirect(url_for('admin.listar_usuarios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar colaborador: {str(e)}', 'danger')

    setores = Setor.query.all()
    return render_template('admin/form_usuario.html', usuario=usuario, setores=setores)

@admin_bp.route('/usuario/excluir/<int:id>', methods=['POST'])
def excluir_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuário removido do sistema.', 'warning')
    except:
        db.session.rollback()
        flash('Não é possível excluir: Usuário possui histórico de produção vinculado.', 'danger')
        
    return redirect(url_for('admin.listar_usuarios'))