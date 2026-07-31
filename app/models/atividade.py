from app import db
from datetime import datetime

class AtividadePadrao(db.Model):
    """
    Atividade Macro (Catálogo de Serviços).
    Representa o "O Que Fazer".
    Ex: "Conciliação Bancária", "Carregamento de Caminhão".
    """
    __tablename__ = 'atividades_padrao'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    is_rotineira = db.Column(db.Boolean, default=True)
    requer_tarefas = db.Column(db.Boolean, default=False)

    status_sla = db.Column(db.String(30), default='Em Andamento', nullable=False)

    tempo_estimado_valor = db.Column(db.Integer, nullable=False, default=0)
    tempo_estimado_unidade = db.Column(db.String(20), default='minutos', nullable=False)

    tempo_convertido_minutos = db.Column(db.Integer, nullable=False, default=0)

    tarefas = db.relationship('TarefaPadrao', backref='atividade_pai', lazy='dynamic', cascade="all, delete-orphan")
    lancamentos = db.relationship('Lancamento', backref='atividade_referencia', lazy='dynamic', cascade="all, delete-orphan")

    responsavel = db.relationship('Usuario', foreign_keys=[responsavel_id], backref='atividades_atribuidas')

    def calcular_minutos_normalizados(self):
        """
        Converte a unidade flexível para minutos padrão GEROT.
        Base: Jornada de 8h úteis (480 min).
        """
        fator = {
            'minutos': 1,
            'horas': 60,
            'dias': 480,
            'semanas': 2400,
            'meses': 9600
        }
        multiplicador = fator.get(self.tempo_estimado_unidade, 1)
        return self.tempo_estimado_valor * multiplicador

    def __init__(self, **kwargs):
        super(AtividadePadrao, self).__init__(**kwargs)
        if self.tempo_estimado_valor and self.tempo_estimado_unidade:
            self.tempo_convertido_minutos = self.calcular_minutos_normalizados()

    def atualizar_tempo(self):
        """Chamar este método sempre que editar o tempo estimado"""
        self.tempo_convertido_minutos = self.calcular_minutos_normalizados()

    def __repr__(self):
        return f'<Atividade {self.titulo} ({self.tempo_convertido_minutos} min) - SLA: {self.status_sla}>'

class TarefaPadrao(db.Model):
    """
    Sub-atividade / Tarefa (Micro).
    Obrigatória vinculação a uma Atividade Macro.
    Pode ser cadastrada por Gestores ou Operadores.
    """
    __tablename__ = 'tarefas_padrao'

    id = db.Column(db.Integer, primary_key=True)

    atividade_id = db.Column(db.Integer, db.ForeignKey('atividades_padrao.id'), nullable=False)

    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    descricao = db.Column(db.String(200), nullable=False)

    impacto_percentual = db.Column(db.Float, default=0.0)

    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    lancamentos = db.relationship('Lancamento', backref='tarefa_referencia', lazy='dynamic')
    criador = db.relationship('Usuario', foreign_keys=[criado_por_id])

    def __repr__(self):
        return f'<Tarefa {self.descricao} ({self.impacto_percentual}%)>'