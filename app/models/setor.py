from app import db
from datetime import datetime

class Setor(db.Model):
    __tablename__ = 'setores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False, index=True)
    sigla = db.Column(db.String(20), unique=True, nullable=False)
    codigo_interno = db.Column(db.String(50), unique=True, nullable=False)
    data_criacao_sistema = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    hierarquia_pai_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True)

    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', use_alter=True, name='fk_setor_responsavel'), nullable=True)
    substituto_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', use_alter=True, name='fk_setor_substituto'), nullable=True)

    tipo_setor = db.Column(db.String(30))
    natureza_atuacao = db.Column(db.String(30))

    missao_setor = db.Column(db.Text, nullable=True)
    descricao_atividades = db.Column(db.Text, nullable=True)
    nivel_complexidade = db.Column(db.String(20), default='Média')
    nivel_repetitividade = db.Column(db.String(20), default='Média')

    limite_max_colaboradores = db.Column(db.Integer, default=0)
    cargos_permitidos = db.Column(db.Text)

    turno_operacao = db.Column(db.String(50))
    escala_trabalho = db.Column(db.String(50))

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