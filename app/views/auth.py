from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime
import re
from app import db
from app.models.usuario import Usuario
from app.models.setor import Setor

auth_bp = Blueprint('auth', __name__)

UFS_BRASIL = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
    'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
    'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Tela de Acesso. Processa as credenciais e redireciona conforme o perfil.
    """
    if current_user.is_authenticated:
        return redirect_dest(current_user)

    if request.method == 'POST':
        username_input = request.form.get('username')
        password_input = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = Usuario.query.filter(
            (Usuario.username == username_input) | (Usuario.email == username_input)
        ).first()

        if user is None or not user.check_password(password_input):
            flash('Login ou senha inválidos. Verifique suas credenciais e tente novamente.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.ativo:
            flash('Sua conta está inativa ou aguardando aprovação. Contate o RH ou seu Gestor.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        user.ultimo_login = datetime.utcnow()
        db.session.commit()

        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            return redirect_dest(user)

        return redirect(next_page)

    return render_template('auth/login.html')

@auth_bp.route('/registrar', methods=['GET', 'POST'])
@login_required
def registrar():
    """
    Solicitação de Cadastro Completo com sanitização automática de Telefone,
    suporte a múltiplos setores e lista completa de UFs.
    """
    if current_user.is_operador:
        flash('Acesso negado. Apenas administradores, gestores ou coordenadores podem realizar cadastros.', 'danger')
        return redirect(url_for('operacao.painel'))

    if current_user.is_coordenador and not current_user.is_gestor:
        setores = Setor.query.filter_by(id=current_user.setor_id).all()
    else:
        setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()

    if request.method == 'POST':
        nome = request.form.get('nome', '').upper().strip()
        email = request.form.get('email', '').lower().strip()
        cpf = request.form.get('cpf', '').strip()
        telefone_raw = request.form.get('telefone', '').strip()
        telefone = Usuario.sanitizar_telefone(telefone_raw)
        senha = request.form.get('senha', '')
        confirmacao = request.form.get('confirmacao_senha', '')
        setor_id = request.form.get('setor_id')

        padrao_cpf = r'^\d{3}\.\d{3}\.\d{3}-\d{2}$'
        if not re.match(padrao_cpf, cpf):
            flash('Formato de CPF inválido. Utilize o formato 000.000.000-00.', 'danger')
            return redirect(url_for('auth.registrar'))

        if not telefone or len(re.sub(r'\D', '', telefone_raw)) < 8:
            flash('Informe um número de telefone válido com pelo menos 8 dígitos.', 'danger')
            return redirect(url_for('auth.registrar'))

        rg_numero = request.form.get('rg_numero')
        rg_orgao = request.form.get('rg_orgao')
        rg_uf = request.form.get('rg_uf')
        sexo = request.form.get('sexo')
        estado_civil = request.form.get('estado_civil')

        cep = request.form.get('cep')
        logradouro = request.form.get('logradouro')
        numero_end = request.form.get('numero_endereco')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        uf_end = request.form.get('uf_endereco')

        matricula = request.form.get('matricula')
        cargo = request.form.get('cargo')
        funcao = request.form.get('funcao')
        tipo_vinculo = request.form.get('tipo_vinculo')
        role_atribuida = request.form.get('role', 'operador')

        data_nasc_str = request.form.get('data_nascimento')
        data_adm_str = request.form.get('data_admissao')

        try:
            dt_nascimento = datetime.strptime(data_nasc_str, '%Y-%m-%d').date() if data_nasc_str else None
            dt_admissao = datetime.strptime(data_adm_str, '%Y-%m-%d').date() if data_adm_str else None
        except ValueError:
            flash('Formato de data inválido.', 'danger')
            return redirect(url_for('auth.registrar'))

        if not setor_id:
            flash('O Setor é obrigatório.', 'danger')
            return redirect(url_for('auth.registrar'))

        if current_user.is_coordenador and not current_user.is_gestor:
            if int(setor_id) not in current_user.todos_setores_ids:
                flash('Tentativa de alocação bloqueada. Você só pode cadastrar no(s) seu(s) setor(es).', 'danger')
                return redirect(url_for('auth.registrar'))

        if senha and senha != confirmacao:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('auth.registrar'))

        if Usuario.query.filter((Usuario.email == email) | (Usuario.cpf == cpf)).first():
            flash('E-mail ou CPF já cadastrado no sistema.', 'danger')
            return redirect(url_for('auth.registrar'))

        username_gerado = email.split('@')[0]
        base_username = username_gerado
        counter = 1
        while Usuario.query.filter_by(username=username_gerado).first():
            username_gerado = f"{base_username}{counter}"
            counter += 1

        novo_user = Usuario(
            nome_completo=nome,
            email=email,
            username=username_gerado,
            cpf=cpf,
            setor_id=setor_id,
            role=role_atribuida,
            ativo=True,
            rg_numero=rg_numero,
            rg_orgao_emissor=rg_orgao,
            rg_uf=rg_uf,
            data_nascimento=dt_nascimento,
            sexo=sexo,
            estado_civil=estado_civil,
            telefone_principal=telefone,
            cep=cep,
            logradouro=logradouro,
            numero_endereco=numero_end,
            bairro=bairro,
            cidade=cidade,
            uf_endereco=uf_end,
            matricula=matricula,
            cargo=cargo,
            funcao=funcao,
            tipo_vinculo=tipo_vinculo,
            data_admissao=dt_admissao,
            cadastrado_por_id=current_user.id,
            data_cadastro=datetime.utcnow()
        )

        if senha:
            novo_user.set_password(senha)
        else:
            novo_user.set_password('123456')

        setores_sec_ids = request.form.getlist('setores_secundarios')
        for sid in setores_sec_ids:
            s_obj = Setor.query.get(int(sid))
            if s_obj and s_obj.id != int(setor_id):
                novo_user.setores_secundarios.append(s_obj)

        novo_user.verificar_status_cadastro()

        try:
            db.session.add(novo_user)
            db.session.commit()
            flash(f'Colaborador {nome} cadastrado com sucesso! Usuário padrão: {username_gerado} / Senha: 123456', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar no banco de dados: {str(e)}', 'danger')

    return render_template('auth/registro.html', setores=setores, ufs=UFS_BRASIL)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com segurança.', 'info')
    return redirect(url_for('auth.login'))

def redirect_dest(user):
    if user.is_admin or user.is_gestor:
        return redirect(url_for('gestao.dashboard'))
    elif user.is_coordenador:
        return redirect(url_for('gestao.dashboard'))
    else:
        return redirect(url_for('operacao.painel'))