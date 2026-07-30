from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

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

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    role = db.Column(db.String(20), default='operador', nullable=False)
    ativo = db.Column(db.Boolean, default=False)

    nome_completo = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)

    rg_numero = db.Column(db.String(20))
    rg_orgao_emissor = db.Column(db.String(20))
    rg_uf = db.Column(db.String(2))

    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(20))
    estado_civil = db.Column(db.String(20))

    telefone_principal = db.Column(db.String(20))

    logradouro = db.Column(db.String(150))
    numero_endereco = db.Column(db.String(20))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf_endereco = db.Column(db.String(2))
    cep = db.Column(db.String(10))

    matricula = db.Column(db.String(50), unique=True, nullable=True)
    cargo = db.Column(db.String(100))
    funcao = db.Column(db.String(100))

    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    setores_secundarios = db.relationship(
        'Setor',
        secondary=usuario_setores_secundarios,
        backref=db.backref('coordenadores_secundarios', lazy='dynamic')
    )

    tipo_vinculo = db.Column(db.String(50))
    data_admissao = db.Column(db.Date)

    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)

    status_cadastro = db.Column(db.String(20), default='incompleto')

    cadastrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    cadastrador = db.relationship('Usuario', remote_side=[id], backref='usuarios_cadastrados')

    lancamentos = db.relationship('Lancamento', backref='autor', lazy='dynamic', foreign_keys='Lancamento.usuario_id')

    correcoes_aprovadas = db.relationship('Lancamento', backref='aprovador', lazy='dynamic', foreign_keys='Lancamento.correcao_aprovada_por')

    @staticmethod
    def sanitizar_telefone(telefone_raw):
        """Remove caracteres não numéricos e formata amigavelmente o telefone."""
        if not telefone_raw:
            return ""
        digits = re.sub(r'\D', '', str(telefone_raw))
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        return digits or str(telefone_raw)

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

    def pode_gerenciar_setor(self, target_setor_id):
        """Valida se o usuário tem permissão para gerenciar rotinas do setor especificado."""
        if self.is_gestor:
            return True
        if self.is_coordenador and target_setor_id in self.todos_setores_ids:
            return True
        return False

    def pode_deletar_lancamento(self, lancamento_obj):
        """Operador não pode deletar nada. Coordenador só deleta do seu setor. Gestor deleta tudo."""
        if self.is_operador:
            return False
        if self.is_gestor:
            return True
        if self.is_coordenador and lancamento_obj.setor_id in self.todos_setores_ids:
            return True
        return False

    def __repr__(self):
        return f'<Usuario {self.username} - {self.cargo}>'