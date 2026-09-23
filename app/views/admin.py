from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.usuario import Usuario
from app.models.setor import Setor
from app.models.lancamento import Lancamento
from app.models.atividade import AtividadePadrao
from app.services.calculo_bi import CalculoBI

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_gestor):
            flash('Acesso negado. Área restrita à Direção e Administração Geral.', 'danger')
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
    return redirect(url_for('gestao.dashboard'))

@admin_bp.route('/setores')
def listar_setores():
    page = request.args.get('page', 1, type=int)
    setores_pagination = Setor.query.order_by(Setor.nome.asc()).paginate(page=page, per_page=10, error_out=False)
    possiveis_gestores = Usuario.query.filter(Usuario.role.in_(['admin', 'diretor', 'gestor', 'lider', 'coordenador'])).all()

    return render_template('admin/setores.html',
                           setores=setores_pagination.items,
                           pagination=setores_pagination,
                           usuarios=possiveis_gestores,
                           setor_edicao=None,
                           CalculoBI=CalculoBI)

@admin_bp.route('/setor/editar/<int:id>', methods=['GET', 'POST'])
def editar_setor(id):
    setor = Setor.query.get_or_404(id)
    if request.method == 'POST':
        try:
            setor.nome = request.form.get('nome') or setor.nome
            if request.form.get('sigla'):
                setor.sigla = request.form.get('sigla').upper()
            setor.codigo_interno = request.form.get('codigo_interno') or setor.codigo_interno
            setor.hierarquia_pai_id = request.form.get('hierarquia_pai_id') or None
            setor.responsavel_id = request.form.get('responsavel_id') or None
            setor.substituto_id = request.form.get('substituto_id') or None
            setor.tipo_setor = request.form.get('tipo_setor') or setor.tipo_setor
            setor.natureza_atuacao = request.form.get('natureza_atuacao') or setor.natureza_atuacao
            setor.missao_setor = request.form.get('missao_setor') or setor.missao_setor
            setor.descricao_atividades = request.form.get('descricao_atividades') or setor.descricao_atividades
            setor.nivel_complexidade = request.form.get('nivel_complexidade') or setor.nivel_complexidade
            setor.nivel_repetitividade = request.form.get('nivel_repetitividade') or setor.nivel_repetitividade

            lim_max = request.form.get('limite_max_colaboradores') or request.form.get('limite_max') or 0
            setor.limite_max_colaboradores = int(lim_max)

            setor.cargos_permitidos = request.form.get('cargos_permitidos') or setor.cargos_permitidos
            setor.turno_operacao = request.form.get('turno_operacao') or setor.turno_operacao
            setor.escala_trabalho = request.form.get('escala_trabalho') or setor.escala_trabalho
            setor.ativo = True if request.form.get('ativo') in ['1', 'true', 'on', True] else False

            db.session.commit()
            flash(f'Setor {setor.sigla} atualizado com sucesso.', 'success')
            return redirect(url_for('admin.listar_setores'))
        except IntegrityError:
            db.session.rollback()
            flash('Conflito: Nome, Sigla ou Código Interno do Setor já cadastrado em outra unidade.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar setor: {str(e)}', 'danger')

    setores_pai = Setor.query.filter(Setor.id != id).order_by(Setor.nome).all()
    possiveis_gestores = Usuario.query.filter(Usuario.role.in_(['admin', 'diretor', 'gestor', 'lider', 'coordenador'])).all()

    return render_template('admin/form_setor.html', setor=setor, setores_pai=setores_pai, usuarios=possiveis_gestores, CalculoBI=CalculoBI)

@admin_bp.route('/setor/excluir/<int:id>', methods=['POST'])
def excluir_setor(id):
    setor = Setor.query.get_or_404(id)
    if setor.sigla == 'ROOT':
        flash('O setor mestre não pode ser excluído.', 'danger')
        return redirect(url_for('admin.listar_setores'))
    try:
        db.session.delete(setor)
        db.session.commit()
        flash('Setor excluído com sucesso.', 'info')
    except:
        db.session.rollback()
        flash('Não é possível excluir: existem colaboradores ou lançamentos vinculados.', 'warning')
    return redirect(url_for('admin.listar_setores'))

@admin_bp.route('/setores/excluir-massa', methods=['POST'])
def excluir_massa_setores():
    ids = request.form.getlist('setor_ids')
    if not ids:
        flash('Nenhum setor selecionado para exclusão.', 'warning')
        return redirect(url_for('admin.listar_setores'))

    try:
        remv_count = 0
        for sid in ids:
            setor = Setor.query.get(int(sid))
            if setor and setor.sigla != 'ROOT':
                setor.responsavel_id = None
                setor.substituto_id = None
                db.session.commit()
                db.session.delete(setor)
                remv_count += 1
        db.session.commit()
        flash(f'{remv_count} setor(es) excluído(s) com sucesso em lote.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir setores em massa: {str(e)}', 'danger')
    return redirect(url_for('admin.listar_setores'))

@admin_bp.route('/setor/novo', methods=['GET', 'POST'])
def novo_setor():
    if request.method == 'POST':
        sigla_input = request.form.get('sigla').upper().strip() if request.form.get('sigla') else ''
        codigo_input = (request.form.get('codigo_interno') or '').strip()

        setor_existente = Setor.query.filter(
            (Setor.sigla == sigla_input) | (Setor.codigo_interno == codigo_input)
        ).first()

        if setor_existente:
            flash(f'Atenção: O setor com sigla "{sigla_input}" ou código "{codigo_input}" já existe no sistema.', 'warning')
            return redirect(url_for('admin.novo_setor'))

        try:
            lim_max = request.form.get('limite_max_colaboradores') or request.form.get('limite_max') or 0
            novo_setor_obj = Setor(
                nome=request.form.get('nome').strip(),
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
                limite_max_colaboradores=int(lim_max),
                cargos_permitidos=request.form.get('cargos_permitidos'),
                turno_operacao=request.form.get('turno_operacao'),
                escala_trabalho=request.form.get('escala_trabalho')
            )

            db.session.add(novo_setor_obj)
            db.session.commit()
            flash('Novo Setor criado com sucesso!', 'success')
            return redirect(url_for('admin.listar_setores'))

        except IntegrityError:
            db.session.rollback()
            flash('Erro de duplicidade: Já existe um setor com este Nome ou Sigla.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro técnico ao criar setor: {str(e)}', 'danger')

    setores_hierarquia = Setor.query.order_by(Setor.nome).all()
    possiveis_gestores = Usuario.query.filter(Usuario.role.in_(['admin', 'diretor', 'gestor', 'lider', 'coordenador'])).all()

    return render_template('admin/form_setor.html',
                           setores_pai=setores_hierarquia,
                           usuarios=possiveis_gestores,
                           CalculoBI=CalculoBI)

@admin_bp.route('/usuarios')
def listar_usuarios():
    page = request.args.get('page', 1, type=int)
    usuarios_pagination = Usuario.query.order_by(Usuario.nome_completo.asc()).paginate(page=page, per_page=10, error_out=False)
    setores = Setor.query.all()

    return render_template('admin/usuarios.html',
                           usuarios=usuarios_pagination.items,
                           pagination=usuarios_pagination,
                           setores=setores,
                           CalculoBI=CalculoBI)

@admin_bp.route('/usuario/novo', methods=['GET', 'POST'])
def novo_usuario():
    """Cadastro administrativo seguro de usuários com higienização e tratamento gracioso de duplicidades."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email_raw = request.form.get('email', '').strip()
        cpf_raw = request.form.get('cpf', '').strip()
        nome_completo = request.form.get('nome_completo', '').strip()
        telefone_raw = request.form.get('telefone_principal') or request.form.get('telefone') or ''
        role = request.form.get('role', 'colaborador')
        setor_id = request.form.get('setor_id', type=int)
        cargo = request.form.get('cargo', '').strip()

        # Mapeamento de papéis antigos para novos
        role_map = {'operador': 'colaborador', 'coordenador': 'lider', 'gestor': 'diretor'}
        role = role_map.get(role, role)

        # Padronização de e-mail institucional @transultransporte.com.br
        email = Usuario.sanitizar_email(email_raw)
        telefone = Usuario.sanitizar_telefone(telefone_raw)

        # Verificação prévia de duplicidade antes do insert para feedback amigável
        usuario_duplicado = Usuario.query.filter(
            (Usuario.username == username) | (Usuario.email == email) | (Usuario.cpf == cpf_raw)
        ).first()

        if usuario_duplicado:
            if usuario_duplicado.username == username:
                msg = f'O usuário com login "{username}" já existe no sistema.'
            elif usuario_duplicado.cpf == cpf_raw:
                msg = f'O CPF "{cpf_raw}" já se encontra cadastrado para {usuario_duplicado.nome_completo}.'
            else:
                msg = f'O e-mail "{email}" já está em uso.'
            flash(f'Atenção: {msg}', 'warning')
            setores = Setor.query.all()
            return render_template('admin/form_usuario.html', usuario=None, setores=setores, CalculoBI=CalculoBI)

        try:
            novo_user = Usuario(
                username=username,
                email=email,
                cpf=cpf_raw,
                nome_completo=nome_completo,
                telefone_principal=telefone,
                role=role,
                setor_id=setor_id,
                cargo=cargo,
                ativo=True,
                status_cadastro='completo'
            )
            senha_inicial = request.form.get('senha') or 'transul123'
            novo_user.set_password(senha_inicial)

            db.session.add(novo_user)
            db.session.commit()
            flash(f'Colaborador {nome_completo} ({email}) cadastrado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))

        except IntegrityError:
            db.session.rollback()
            flash('Não foi possível concluir o cadastro: Já existe um registro com os mesmos dados de identificação (CPF, Login ou E-mail).', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar colaborador: {str(e)}', 'danger')

    setores = Setor.query.all()
    return render_template('admin/form_usuario.html', usuario=None, setores=setores, CalculoBI=CalculoBI)

@admin_bp.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        try:
            cpf_edit = request.form.get('cpf')
            if cpf_edit:
                cpf_edit = cpf_edit.strip()
                usuario_mesmo_cpf = Usuario.query.filter(Usuario.cpf == cpf_edit, Usuario.id != usuario.id).first()
                if usuario_mesmo_cpf:
                    flash(f'O CPF {cpf_edit} já pertence a outro usuário ({usuario_mesmo_cpf.nome_completo}). Operação abortada.', 'warning')
                    return redirect(url_for('admin.editar_usuario', id=usuario.id))
                usuario.cpf = cpf_edit

            usuario.nome_completo = request.form.get('nome') or request.form.get('nome_completo') or usuario.nome_completo
            
            # Padroniza e-mail com @transultransporte.com.br
            email_edit = request.form.get('email')
            if email_edit:
                usuario.email = Usuario.sanitizar_email(email_edit)
            
            tel_input = request.form.get('telefone') or request.form.get('telefone_principal')
            if tel_input:
                usuario.telefone_principal = Usuario.sanitizar_telefone(tel_input)

            usuario.cargo = request.form.get('cargo')
            usuario.setor_id = request.form.get('setor_id')
            
            role_form = request.form.get('role')
            role_map = {'operador': 'colaborador', 'coordenador': 'lider', 'gestor': 'diretor'}
            usuario.role = role_map.get(role_form, role_form)

            usuario.ativo = True if request.form.get('ativo') in ['1', 'true', 'on', True] else False

            setores_secundarios_ids = request.form.getlist('setores_secundarios')
            usuario.setores_secundarios = []
            for sid in setores_secundarios_ids:
                s_obj = Setor.query.get(int(sid))
                if s_obj and s_obj.id != int(usuario.setor_id):
                    usuario.setores_secundarios.append(s_obj)

            nova_senha = request.form.get('nova_senha')
            if nova_senha and nova_senha.strip():
                usuario.set_password(nova_senha.strip())
                flash(f'Senha de {usuario.username} atualizada com sucesso.', 'info')

            db.session.commit()
            flash(f'Perfil de {usuario.nome_completo} atualizado com sucesso.', 'success')
            return redirect(url_for('admin.listar_usuarios'))

        except IntegrityError:
            db.session.rollback()
            flash('Erro de conflito: E-mail, CPF ou Nome de Usuário já utilizado.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar colaborador: {str(e)}', 'danger')

    setores = Setor.query.all()
    return render_template('admin/form_usuario.html', usuario=usuario, setores=setores, CalculoBI=CalculoBI)

@admin_bp.route('/usuario/excluir/<int:id>', methods=['POST'])
def excluir_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('Não é permitido excluir a sua própria conta ativa.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))

    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuário excluído do sistema.', 'info')
    except:
        db.session.rollback()
        flash('Não foi possível excluir: Existem lançamentos de produção vinculados a este perfil.', 'danger')

    return redirect(url_for('admin.listar_usuarios'))

@admin_bp.route('/usuarios/excluir-massa', methods=['POST'])
def excluir_massa_usuarios():
    ids = request.form.getlist('usuario_ids')
    if not ids:
        flash('Nenhum usuário selecionado para exclusão.', 'warning')
        return redirect(url_for('admin.listar_usuarios'))
    
    try:
        remv_count = 0
        for uid in ids:
            user = Usuario.query.get(int(uid))
            if user and user.id != current_user.id:
                db.session.delete(user)
                remv_count += 1
        db.session.commit()
        flash(f'{remv_count} usuário(s) excluído(s) em lote.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuários em massa: {str(e)}', 'danger')
    return redirect(url_for('admin.listar_usuarios'))