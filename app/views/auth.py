from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime
from app import db
from app.models.usuario import Usuario
from app.models.setor import Setor

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Tela de Acesso.
    Processa as credenciais e redireciona conforme o perfil (Role) em cascata.
    """
    if current_user.is_authenticated:
        return redirect_dest(current_user)

    if request.method == 'POST':
        username_input = request.form.get('username')
        password_input = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # Busca por Username OU Email (Flexibilidade mantida)
        user = Usuario.query.filter(
            (Usuario.username == username_input) | (Usuario.email == username_input)
        ).first()

        # Validação de Credenciais
        if user is None or not user.check_password(password_input):
            flash('Login ou senha inválidos. Verifique suas credenciais e tente novamente.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Validação de Status (Aprovação Pendente ou Bloqueio)
        if not user.ativo:
            flash('Sua conta está inativa ou aguardando aprovação. Contate o RH ou seu Gestor.', 'warning')
            return redirect(url_for('auth.login'))

        # Sucesso: Loga o usuário
        login_user(user, remember=remember)
        
        # Atualiza data do último login
        user.ultimo_login = datetime.utcnow()
        db.session.commit()
        
        # Redirecionamento Seguro
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            return redirect_dest(user)
        
        return redirect(next_page)

    return render_template('auth/login.html')

@auth_bp.route('/registrar', methods=['GET', 'POST'])
def registrar():
    """
    Solicitação de Cadastro Completo (RH + Acesso).
    Regra em cascata: Admin/Gestor (Tudo) > Coordenador (Seu Setor) > Operador (Bloqueado)
    """
    # Operadores não podem acessar a tela de registro
    if current_user.is_authenticated and current_user.is_operador:
        flash('Acesso negado. Apenas coordenadores ou gestores podem realizar cadastros.', 'danger')
        return redirect(url_for('operacao.painel'))

    # Aplicação da regra de cascata na listagem de setores
    if current_user.is_authenticated and current_user.is_coordenador:
        # Coordenadores só podem registrar pessoas no próprio setor
        setores = Setor.query.filter_by(id=current_user.setor_id).all()
    else:
        # Admins, Gestores ou usuários não logados (auto-cadastro) veem todos os setores ativos
        setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()

    if request.method == 'POST':
        # --- 1. DADOS DE ACESSO ---
        nome = request.form.get('nome').upper()
        email = request.form.get('email').lower()
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')
        confirmacao = request.form.get('confirmacao_senha')
        setor_id = request.form.get('setor_id')

        # --- 2. IDENTIFICAÇÃO BÁSICA ---
        rg_numero = request.form.get('rg_numero')
        rg_orgao = request.form.get('rg_orgao')
        rg_uf = request.form.get('rg_uf')
        sexo = request.form.get('sexo')
        estado_civil = request.form.get('estado_civil')
        
        # --- 3. CONTATO E ENDEREÇO ---
        telefone = request.form.get('telefone')
        cep = request.form.get('cep')
        logradouro = request.form.get('logradouro')
        numero_end = request.form.get('numero_endereco')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        uf_end = request.form.get('uf_endereco')

        # --- 4. DADOS TRABALHISTAS ---
        matricula = request.form.get('matricula')
        cargo = request.form.get('cargo')
        funcao = request.form.get('funcao')
        tipo_vinculo = request.form.get('tipo_vinculo')
        
        # Captura de Datas (Tratamento de erro robusto)
        data_nasc_str = request.form.get('data_nascimento')
        data_adm_str = request.form.get('data_admissao')
        
        try:
            dt_nascimento = datetime.strptime(data_nasc_str, '%Y-%m-%d').date() if data_nasc_str else None
            dt_admissao = datetime.strptime(data_adm_str, '%Y-%m-%d').date() if data_adm_str else None
        except ValueError:
            flash('Formato de data inválido. Use o calendário para selecionar.', 'danger')
            return redirect(url_for('auth.registrar'))

        # --- VALIDAÇÕES ---
        if not setor_id:
            flash('O Setor é obrigatório.', 'danger')
            return redirect(url_for('auth.registrar'))

        # Proteção extra: Garantir que coordenador não burle o HTML e envie ID de outro setor
        if current_user.is_authenticated and current_user.is_coordenador:
            if int(setor_id) != current_user.setor_id:
                flash('Tentativa de fraude bloqueada. Você só pode cadastrar no seu setor.', 'danger')
                return redirect(url_for('auth.registrar'))

        if senha and senha != confirmacao:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('auth.registrar'))

        # Verifica duplicidade crítica
        if Usuario.query.filter((Usuario.email == email) | (Usuario.cpf == cpf)).first():
            flash('E-mail ou CPF já cadastrado no sistema.', 'danger')
            return redirect(url_for('auth.registrar'))

        # --- CRIAÇÃO DO OBJETO ---
        username_gerado = email.split('@')[0]
        
        novo_user = Usuario(
            nome_completo=nome,
            email=email,
            username=username_gerado,
            cpf=cpf,
            setor_id=setor_id,
            role='operador', # Default seguro
            ativo=False,     # Nasce inativo
            
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
            
            cadastrado_por_id=current_user.id if current_user.is_authenticated else None,
            data_cadastro=datetime.utcnow()
        )
        
        if senha:
            novo_user.set_password(senha)
        
        novo_user.verificar_status_cadastro()

        try:
            db.session.add(novo_user)
            db.session.commit()
            
            msg = 'Cadastro realizado com sucesso!'
            if novo_user.status_cadastro == 'incompleto':
                msg += ' Alguns dados de RH ficaram em branco e deverão ser preenchidos depois.'
            
            flash(msg, 'success')
            
            if current_user.is_authenticated and (current_user.is_admin or current_user.is_gestor):
                return redirect(url_for('admin.listar_usuarios'))
            elif current_user.is_authenticated and current_user.is_coordenador:
                return redirect(url_for('gestao.equipe'))
            else:
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar no banco de dados: {str(e)}', 'danger')

    return render_template('auth/registro.html', setores=setores)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com segurança.', 'info')
    return redirect(url_for('auth.login'))

def redirect_dest(user):
    """Roteamento pós-login em cascata."""
    if user.is_admin:
        return redirect(url_for('admin.dashboard'))
    elif user.is_gestor:
        return redirect(url_for('admin.dashboard')) # Gestor também acessa visão global
    elif user.is_coordenador:
        return redirect(url_for('gestao.dashboard'))
    else:
        return redirect(url_for('operacao.painel'))