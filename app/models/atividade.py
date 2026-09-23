from app import db
from datetime import datetime

class AtividadePadrao(db.Model):
    """
    Atividade Macro (Catálogo de Serviços).
    Representa o "O Que Fazer".
    Ex: "Conciliação Bancária", "Carregamento de Caminhão".
    Status padronizados: 'Não Iniciado', 'Em Andamento', 'Concluído', 'Cancelado'.
    Campos de previsão temporal inicial e final incluídos com segurança para o banco.
    """
    __tablename__ = 'atividades_padrao'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    is_rotineira = db.Column(db.Boolean, default=True)
    requer_tarefas = db.Column(db.Boolean, default=False)

    # Status padrão do ciclo de vida da rotina
    status_sla = db.Column(db.String(30), default='Não Iniciado', nullable=False)

    tempo_estimado_valor = db.Column(db.Integer, nullable=False, default=0)
    tempo_estimado_unidade = db.Column(db.String(20), default='minutos', nullable=False)

    tempo_convertido_minutos = db.Column(db.Integer, nullable=False, default=0)

    # Prazos estimados de início e fim definidos pela Liderança/Coordenação (sem quebrar tabelas pré-existentes)
    data_inicio_prevista = db.Column(db.DateTime, nullable=True)
    data_fim_prevista = db.Column(db.DateTime, nullable=True)

    tarefas = db.relationship('TarefaPadrao', backref='atividade_pai', lazy='dynamic', cascade="all, delete-orphan")
    lancamentos = db.relationship('Lancamento', backref='atividade_referencia', lazy='dynamic', cascade="all, delete-orphan")

    responsavel = db.relationship('Usuario', foreign_keys=[responsavel_id], backref='atividades_atribuidas')

    def calcular_minutos_normalizados(self):
        """
        Converte a unidade flexível para minutos úteis padrão GEROT.
        Base de cálculo: Jornada diária útil de 8 horas (480 minutos).
        Semana útil: 5 dias úteis (40 horas = 2.400 minutos).
        Mês útil: 20 dias úteis (160 horas = 9.600 minutos).
        """
        fator = {
            'minutos': 1,
            'horas': 60,
            'dias': 480,
            'semanas': 2400,
            'meses': 9600
        }
        unidade = (self.tempo_estimado_unidade or 'minutos').lower()
        multiplicador = fator.get(unidade, 1)
        valor = self.tempo_estimado_valor or 0
        return valor * multiplicador

    def __init__(self, **kwargs):
        super(AtividadePadrao, self).__init__(**kwargs)
        if self.tempo_estimado_valor and self.tempo_estimado_unidade:
            self.tempo_convertido_minutos = self.calcular_minutos_normalizados()
        if not self.status_sla:
            self.status_sla = 'Não Iniciado'

    def atualizar_tempo(self):
        """Chamar este método sempre que editar o tempo estimado"""
        self.tempo_convertido_minutos = self.calcular_minutos_normalizados()

    def definir_status(self, novo_status):
        """Garante a atribuição dentro dos estados homologados"""
        status_validos = {'Não Iniciado', 'Em Andamento', 'Concluído', 'Cancelado'}
        if novo_status in status_validos:
            self.status_sla = novo_status
        else:
            self.status_sla = 'Em Andamento'

    @property
    def inicio_previsto_formatado(self):
        return self.data_inicio_prevista.strftime('%d/%m/%Y %H:%M') if self.data_inicio_prevista else '--'

    @property
    def fim_previsto_formatado(self):
        return self.data_fim_prevista.strftime('%d/%m/%Y %H:%M') if self.data_fim_prevista else '--'

    @property
    def inicio_previsto_iso(self):
        return self.data_inicio_prevista.strftime('%Y-%m-%dT%H:%M') if self.data_inicio_prevista else ''

    @property
    def fim_previsto_iso(self):
        return self.data_fim_prevista.strftime('%Y-%m-%dT%H:%M') if self.data_fim_prevista else ''

    def __repr__(self):
        return f'<Atividade {self.titulo} ({self.tempo_convertido_minutos} min úteis) - Status: {self.status_sla}>'

class TarefaPadrao(db.Model):
    """
    Sub-atividade / Tarefa (Micro).
    Obrigatória vinculação a uma Atividade Macro.
    Pode ser cadastrada por Diretores, Líderes ou Colaboradores.
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