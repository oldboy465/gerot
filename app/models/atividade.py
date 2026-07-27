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
    descricao = db.Column(db.Text, nullable=True) # Procedimento Operacional Padrão (POP)

    # Dono da Atividade (Setor)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    # Atribuição Individual (Possibilidade de atribuição a uma pessoa)
    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    # Configurações de Comportamento
    is_rotineira = db.Column(db.Boolean, default=True) # True=Rotina Diária, False=Projeto/Eventual
    requer_tarefas = db.Column(db.Boolean, default=False) # Se True, obriga selecionar uma Sub-tarefa no lançamento

    # Status SLA (Cancelado, Em Andamento, Concluído)
    status_sla = db.Column(db.String(30), default='Em Andamento', nullable=False)

    # --- MOTOR DE TEMPO FLEXÍVEL (SLA) ---
    tempo_estimado_valor = db.Column(db.Integer, nullable=False, default=0)
    # Opções: 'minutos', 'horas', 'dias', 'semanas', 'meses'
    tempo_estimado_unidade = db.Column(db.String(20), default='minutos', nullable=False)

    # Campo Calculado (Persistido para performance de BI)
    # Armazena tudo em MINUTOS para permitir soma e média no banco
    tempo_convertido_minutos = db.Column(db.Integer, nullable=False, default=0)

    # Relacionamentos
    tarefas = db.relationship('TarefaPadrao', backref='atividade_pai', lazy='dynamic', cascade="all, delete-orphan")
    lancamentos = db.relationship('Lancamento', backref='atividade_referencia', lazy='dynamic')

    # Relacionamento com o responsável individual
    responsavel = db.relationship('Usuario', foreign_keys=[responsavel_id], backref='atividades_atribuidas')

    def calcular_minutos_normalizados(self):
        """
        Converte a unidade flexível para minutos padrão GEROT.
        Base: Jornada de 8h úteis (480 min).
        """
        fator = {
            'minutos': 1,
            'horas': 60,
            'dias': 480,       # 8 horas úteis
            'semanas': 2400,   # 5 dias úteis * 480
            'meses': 9600      # 20 dias úteis * 480
        }
        multiplicador = fator.get(self.tempo_estimado_unidade, 1)
        return self.tempo_estimado_valor * multiplicador

    def __init__(self, **kwargs):
        super(AtividadePadrao, self).__init__(**kwargs)
        # Calcula automaticamente ao instanciar
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

    # Regra de Negócio: Obrigatoriamente pertence a uma atividade
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividades_padrao.id'), nullable=False)

    # Rastreabilidade: Quem criou a tarefa (Gestor ou Operador)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    descricao = db.Column(db.String(200), nullable=False)

    # Peso da tarefa dentro da atividade pai (0 a 100%)
    # Útil para calcular progresso parcial se a atividade macro for longa
    impacto_percentual = db.Column(db.Float, default=0.0)

    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    lancamentos = db.relationship('Lancamento', backref='tarefa_referencia', lazy='dynamic')
    criador = db.relationship('Usuario', foreign_keys=[criado_por_id])

    def __repr__(self):
        return f'<Tarefa {self.descricao} ({self.impacto_percentual}%)>'