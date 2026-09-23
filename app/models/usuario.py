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
    Nomenclatura de Perfis GEROT:
      - Colaborador (antigo operador)
      - Líder (antigo coordenador)
      - Diretor (antigo gestor)
      - Administrador (admin)
    """
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    # Papéis do sistema: colaborador, lider, diretor, admin
    role = db.Column(db.String(20), default='colaborador', nullable=False)
    ativo = db.Column(db.Boolean, default=False)

    nome_completo = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)

    rg_numero = db.Column(db.String(20))
    rg_orgao_emissor = db.Column(db.String(20))
    rg_uf = db.Column(db.String(2))

    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(20))
    estado_civil = db.Column(db.String(20))

    telefone_principal = db.Column(db.String(30))

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
        """
        Higieniza número de telefone e WhatsApp.
        Aceita formatos variados sem quebrar o fluxo de cadastro.
        """
        if not telefone_raw:
            return ""
        digits = re.sub(r'\D', '', str(telefone_raw))
        if len(digits) == 13 and digits.startswith('55'):
            digits = digits[2:]
        if len(digits) == 12 and digits.startswith('55'):
            digits = digits[2:]

        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        elif len(digits) > 0:
            return digits
        return str(telefone_raw).strip()

    @staticmethod
    def sanitizar_email(email_raw):
        """
        Garante que o e-mail possua o domínio institucional @transultransporte.com.br.
        """
        if not email_raw:
            return ""
        email_clean = str(email_raw).strip().lower()
        if '@' in email_clean:
            usuario_parte = email_clean.split('@')[0].strip()
            return f"{usuario_parte}@transultransporte.com.br"
        return f"{email_clean}@transultransporte.com.br"

    def set_password(self, password):
        """Cria o hash seguro da senha."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha bate com o hash."""
        return check_password_hash(self.password_hash, password)

    def verificar_status_cadastro(self):
        """
        Verifica se os campos essenciais estão preenchidos
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
    def role_label(self):
        """Rótulo legível do perfil para apresentação."""
        mapa = {
            'admin': 'Administrador',
            'diretor': 'Diretor',
            'gestor': 'Diretor',
            'lider': 'Líder',
            'coordenador': 'Líder',
            'colaborador': 'Colaborador',
            'operador': 'Colaborador'
        }
        return mapa.get(self.role.lower(), self.role.title())

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_gestor(self):
        return self.role in ['admin', 'gestor', 'diretor']

    @property
    def is_diretor(self):
        return self.is_gestor

    @property
    def is_coordenador(self):
        return self.role in ['coordenador', 'lider']

    @property
    def is_lider(self):
        return self.is_coordenador

    @property
    def is_operador(self):
        return self.role in ['operador', 'colaborador']

    @property
    def is_colaborador(self):
        return self.is_operador

    def pode_gerenciar_setor(self, target_setor_id):
        """Valida se o usuário tem permissão para gerenciar rotinas do setor especificado."""
        if self.is_gestor:
            return True
        if self.is_coordenador and target_setor_id in self.todos_setores_ids:
            return True
        return False

    def pode_concluir_atividade(self, target_setor_id=None):
        """
        Define permissão de conclusão direta de atividades.
        Colaborador e Líder (do seu setor) podem concluir atividades.
        """
        if self.is_gestor:
            return True
        if self.is_coordenador:
            return target_setor_id in self.todos_setores_ids if target_setor_id else True
        if self.is_operador:
            return target_setor_id == self.setor_id if target_setor_id else True
        return False

    def pode_deletar_lancamento(self, lancamento_obj):
        """Colaborador não pode deletar. Líder deleta apenas do seu setor. Diretor/Admin deleta tudo."""
        if self.is_operador:
            return False
        if self.is_gestor:
            return True
        if self.is_coordenador and lancamento_obj.setor_id in self.todos_setores_ids:
            return True
        return False

    def __repr__(self):
        return f'<Usuario {self.username} - {self.role_label} ({self.cargo})>'