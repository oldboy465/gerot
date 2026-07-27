# 🌳 Projeto Completo (Engine Microsoft)
**Raiz:** `C:/Users/Cliente/gerot`


## 📄 Arquivo: `app\models\setor.py` (85 linhas)

from app import db
from datetime import datetime

class Setor(db.Model):
    """
    Modelo de Setor Avançado (GEROT V1).
    Focado em Planejamento Estratégico, Gestão de Capacidade e Hierarquia Organizacional.
    Integra conceitos de Administração e Engenharia de Software.
    """
    __tablename__ = 'setores'

    # --- 1. IDENTIFICAÇÃO DO SETOR ---
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False, index=True)
    sigla = db.Column(db.String(20), unique=True, nullable=False)
    codigo_interno = db.Column(db.String(50), unique=True, nullable=False) # Centro de Custo/Organograma
    data_criacao_sistema = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    # --- 2. ESTRUTURA ORGANIZACIONAL (HIERARQUIA) ---
    hierarquia_pai_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True)

    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', use_alter=True, name='fk_setor_responsavel'), nullable=True)
    substituto_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', use_alter=True, name='fk_setor_substituto'), nullable=True)

    tipo_setor = db.Column(db.String(30)) # Operacional, Administrativo, Estratégico
    natureza_atuacao = db.Column(db.String(30)) # Direta (Logística) ou Apoio

    # --- 3. FINALIDADE E RESPONSABILIDADES (MISSÃO) ---
    missao_setor = db.Column(db.Text, nullable=True)
    descricao_atividades = db.Column(db.Text, nullable=True) # Processos principais
    nivel_complexidade = db.Column(db.String(20), default='Média') # Baixa, Média, Alta
    nivel_repetitividade = db.Column(db.String(20), default='Média') # Baixa, Média, Alta (Rotina)

    # --- 4. PESSOAS E CAPACIDADE (GESTÃO DE RECURSOS) ---
    limite_max_colaboradores = db.Column(db.Integer, default=0) # 0 = sem limite definido
    cargos_permitidos = db.Column(db.Text) # Lista ou descrição dos cargos vinculados

    turno_operacao = db.Column(db.String(50)) # Diurno, Noturno, 24h, Flexível
    escala_trabalho = db.Column(db.String(50)) # 5x2, 6x1, 12x36, etc.

    # --- RELACIONAMENTOS SQLALCHEMY ---
    sub_setores = db.relationship(
        'Setor',
        backref=db.backref('pai', remote_side=[id]),
        lazy='dynamic'
    )

    usuarios = db.relationship(
        'Usuario',
        backref='setor_pertencente',
        lazy='dynamic',
        foreign_keys='Usuario.setor_id',
        cascade='all, delete-orphan'
    )

    atividades = db.relationship('AtividadePadrao', backref='setor_dono', lazy='dynamic', cascade='all, delete-orphan')
    lancamentos = db.relationship('Lancamento', backref='setor_snapshot', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Setor {self.sigla} - {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'sigla': self.sigla,
            'codigo': self.codigo_interno,
            'hierarquia': self.get_caminho_hierarquico(),
            'tipo': self.tipo_setor,
            'capacidade': {
                'atual': self.usuarios.count(),
                'maxima': self.limite_max_colaboradores
            },
            'complexidade': self.nivel_complexidade
        }

    def get_caminho_hierarquico(self):
        if self.pai:
            return f"{self.pai.get_caminho_hierarquico()} > {self.nome}"
        return self.nome

    def verificar_lotacao_critica(self):
        if self.limite_max_colaboradores <= 0:
            return False
        return self.usuarios.count() >= self.limite_max_colaboradores

---


## 📄 Arquivo: `app\models\usuario.py` (143 linhas)

from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Tabela de associação para permitir que Coordenadores tenham acesso a múltiplos setores
usuario_setores_secundarios = db.Table(
    'usuario_setores_secundarios',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), primary_key=True),
    db.Column('setor_id', db.Integer, db.ForeignKey('setores.id', ondelete='CASCADE'), primary_key=True)
)

class Usuario(UserMixin, db.Model):
    """
    Entidade Usuário - Cadastro Completo (RH + Acesso).
    Contém dados de login, identificação pessoal, endereço e vínculo trabalhista.
    """
    __tablename__ = 'usuarios'

    # --- 0. Identificadores de Sistema ---
    id = db.Column(db.Integer, primary_key=True)

    # Credenciais de Acesso (Login)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    # Controle de Acesso (RBAC)
    role = db.Column(db.String(20), default='operador', nullable=False) # admin, gestor, coordenador, operador
    ativo = db.Column(db.Boolean, default=False) # Situação: Ativo/Inativo (Afastado/Desligado)

    # --- 1. Identificação Básica ---
    nome_completo = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)

    rg_numero = db.Column(db.String(20))
    rg_orgao_emissor = db.Column(db.String(20))
    rg_uf = db.Column(db.String(2))

    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(20)) # Ex: Masculino, Feminino, Outro
    estado_civil = db.Column(db.String(20)) # Solteiro, Casado, etc.

    # --- 2. Dados de Contato e Endereço ---
    telefone_principal = db.Column(db.String(20)) # Celular/Whatsapp

    logradouro = db.Column(db.String(150)) # Rua, Av.
    numero_endereco = db.Column(db.String(20))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf_endereco = db.Column(db.String(2))
    cep = db.Column(db.String(10))

    # --- 3. Dados Trabalhistas (RH) ---
    matricula = db.Column(db.String(50), unique=True, nullable=True)
    cargo = db.Column(db.String(100)) # Ex: Analista
    funcao = db.Column(db.String(100)) # Ex: Desenvolver Software (O que faz na prática)

    # Vinculação Hierárquica Principal
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    # Vinculação Secundária (Permite que coordenadores atuem em múltiplos setores)
    setores_secundarios = db.relationship(
        'Setor',
        secondary=usuario_setores_secundarios,
        backref=db.backref('coordenadores_secundarios', lazy='dynamic')
    )

    tipo_vinculo = db.Column(db.String(50)) # CLT, Estágio, Terceirizado, PJ
    data_admissao = db.Column(db.Date)

    # --- 4. Auditoria do Cadastro ---
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)

    status_cadastro = db.Column(db.String(20), default='incompleto') # completo/incompleto

    # Quem cadastrou este usuário? (Auto-relacionamento)
    cadastrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    # --- Relacionamentos ---

    # Quem cadastrou este usuário (o objeto Usuario pai)
    cadastrador = db.relationship('Usuario', remote_side=[id], backref='usuarios_cadastrados')

    # Execuções realizadas por este usuário
    lancamentos = db.relationship('Lancamento', backref='autor', lazy='dynamic', foreign_keys='Lancamento.usuario_id')

    # Correções aprovadas por este usuário (se for coordenador)
    correcoes_aprovadas = db.relationship('Lancamento', backref='aprovador', lazy='dynamic', foreign_keys='Lancamento.correcao_aprovada_por')

    # --- Métodos ---

    def set_password(self, password):
        """Cria o hash seguro da senha."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha bate com o hash."""
        return check_password_hash(self.password_hash, password)

    def verificar_status_cadastro(self):
        """
        Verifica se os campos obrigatórios do RH estão preenchidos
        e atualiza o status_cadastro.
        """
        campos_obrigatorios = [
            self.matricula, self.rg_numero, self.data_nascimento,
            self.telefone_principal, self.logradouro, self.cep,
            self.data_admissao
        ]
        if all(campos_obrigatorios):
            self.status_cadastro = 'completo'
        else:
            self.status_cadastro = 'incompleto'

    @property
    def todos_setores_ids(self):
        """Retorna uma lista com o ID do setor principal e de todos os setores secundários autorizados."""
        ids = [self.setor_id] if self.setor_id else []
        for s in self.setores_secundarios:
            if s.id not in ids:
                ids.append(s.id)
        return ids

    # Helpers de Permissão
    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_gestor(self):
        return self.role in ['admin', 'gestor']

    @property
    def is_coordenador(self):
        return self.role == 'coordenador'

    @property
    def is_operador(self):
        return self.role == 'operador'

    def __repr__(self):
        return f'<Usuario {self.username} - {self.cargo}>'

---


## 📄 Arquivo: `app\templates\admin\form_usuario.html` (257 linhas)

{% extends "base.html" %}
{% block title %}Cadastro de Colaborador | GEROT{% endblock %}
{% block content %}

## Cadastro de Colaborador

Preencha a ficha completa para acesso ao GEROT.

##### Ficha Cadastral

Todos os campos com (\*) são obrigatórios.

RH & Operações

###### Identificação Pessoal

Nome Completo \*

Data de Nascimento \*

Gênero

Selecione...
Masculino
Feminino
Outro

Estado Civil

Solteiro(a)
Casado(a)
Outro

CPF \*

RG \*

Órgão Emissor

UF

{% for uf in ufs %}
{{ uf }}
{% endfor %}

###### Contato e Endereço

E-mail Corporativo \*

Telefone/WhatsApp \*

CEP \*

Digite o CEP para buscar.

Endereço \*

Número \*

Bairro

Cidade

UF \*

{% for uf in ufs %}
{{ uf }}
{% endfor %}

###### Dados Funcionais

Setor de Lotação \*

Selecione...
{% for setor in setores %}
{{ setor.nome }}
{% endfor %}

Matrícula

Cargo \*

Função Real

Vínculo

CLT
Estágio
PJ
Terceirizado

Admissão \*

Setores Secundários (Opcional para Coordenadores)

{% for setor in setores %}
{{ setor.nome }}
{% endfor %}
Segure CTRL para selecionar múltiplos setores adicionais.

Perfil de Acesso

Operador
Coordenador
Gestor
Administrador

###### Segurança

Senha \*

Confirmar Senha \*

[ ]
Confirmo a veracidade dos dados acima e declaro estar de acordo com as normas internas.

[Cancelar](%7B%7B%20url_for%28%27admin.listar_usuarios%27%29%20%7D%7D)

 Salvar Cadastro

{% endblock %}
{% block scripts %}

{% endblock %}

---


## 📄 Arquivo: `app\views\admin.py` (273 linhas)

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
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
    """Redireciona sempre direto para o dashboard de gestão conforme solicitado."""
    return redirect(url_for('gestao.dashboard'))

@admin_bp.route('/setores')
def listar_setores():
    page = request.args.get('page', 1, type=int)
    setores_pagination = Setor.query.order_by(Setor.nome.asc()).paginate(page=page, per_page=10, error_out=False)
    possiveis_gestores = Usuario.query.filter(Usuario.role.in_(['admin', 'coordenador', 'gestor'])).all()

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
            flash(f'Estrutura do setor {setor.sigla} atualizada com sucesso.', 'success')
            return redirect(url_for('admin.listar_setores'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar setor: {str(e)}', 'danger')

    setores_pai = Setor.query.filter(Setor.id != id).order_by(Setor.nome).all()
    possiveis_gestores = Usuario.query.filter(Usuario.role.in_(['admin', 'coordenador', 'gestor'])).all()

    return render_template('admin/form_setor.html', setor=setor, setores_pai=setores_pai, usuarios=possiveis_gestores, CalculoBI=CalculoBI)

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

@admin_bp.route('/setores/excluir-massa', methods=['POST'])
@login_required
@admin_required
def excluir_massa_setores():
    if not current_user.is_admin and not current_user.is_gestor:
        flash('Acesso restrito a administradores e gestores para exclusão em lote.', 'danger')
        return redirect(url_for('admin.listar_setores'))

    ids = request.form.getlist('setor_ids')
    if not ids:
        flash('Nenhum setor selecionado para exclusão.', 'warning')
        return redirect(url_for('admin.listar_setores'))

    try:
        remv_count = 0
        for sid in ids:
            setor = Setor.query.get(int(sid))
            if setor and setor.sigla != 'ROOT':
                # Remove dependências em cascata ou limpa responsaveis para evitar erro de FK
                setor.responsavel_id = None
                setor.substituto_id = None
                db.session.commit()

                db.session.delete(setor)
                remv_count += 1
        db.session.commit()
        flash(f'{remv_count} setor(es) e suas dependências excluídos com sucesso em lote.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir setores em massa: {str(e)}', 'danger')
    return redirect(url_for('admin.listar_setores'))

@admin_bp.route('/setor/novo', methods=['GET', 'POST'])
def novo_setor():
    if request.method == 'POST':
        sigla_input = request.form.get('sigla').upper() if request.form.get('sigla') else ''
        codigo_input = request.form.get('codigo_interno') or ''

        setor_existente = Setor.query.filter(
            (Setor.sigla == sigla_input) | (Setor.codigo_interno == codigo_input)
        ).first()

        if setor_existente:
            flash(f'Erro: Já existe um setor cadastrado com a sigla {sigla_input} ou código {codigo_input}.', 'danger')
            return redirect(url_for('admin.novo_setor'))

        try:
            lim_max = request.form.get('limite_max_colaboradores') or request.form.get('limite_max') or 0
            novo_setor_obj = Setor(
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
                limite_max_colaboradores=int(lim_max),
                cargos_permitidos=request.form.get('cargos_permitidos'),
                turno_operacao=request.form.get('turno_operacao'),
                escala_trabalho=request.form.get('escala_trabalho')
            )

            db.session.add(novo_setor_obj)
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

@admin_bp.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        try:
            usuario.nome_completo = request.form.get('nome') or request.form.get('nome_completo')
            usuario.email = request.form.get('email')
            usuario.cargo = request.form.get('cargo')
            usuario.setor_id = request.form.get('setor_id')
            usuario.role = request.form.get('role')
            usuario.ativo = True if request.form.get('ativo') in ['1', 'true', 'on', True] else False

            # Processamento de múltiplos setores para coordenadores (se aplicável)
            setores_secundarios_ids = request.form.getlist('setores_secundarios')
            usuario.setores_secundarios = []
            for sid in setores_secundarios_ids:
                s_obj = Setor.query.get(int(sid))
                if s_obj and s_obj.id != int(usuario.setor_id):
                    usuario.setores_secundarios.append(s_obj)

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
    return render_template('admin/form_usuario.html', usuario=usuario, setores=setores, CalculoBI=CalculoBI)

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

@admin_bp.route('/usuarios/excluir-massa', methods=['POST'])
def excluir_massa_usuarios():
    if not current_user.is_admin and not current_user.is_gestor:
        flash('Acesso restrito a administradores e gestores para exclusão em lote.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))

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
        flash(f'{remv_count} usuário(s) excluído(s) com sucesso em lote.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuários em massa: {str(e)}', 'danger')
    return redirect(url_for('admin.listar_usuarios'))

---

