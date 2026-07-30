from app import db
from datetime import datetime

class Lancamento(db.Model):
    """
    Registro de Execução (Log de Produção).
    Substitui o antigo 'Cronômetro'.
    Representa uma unidade de trabalho entregue pelo operador.
    """
    __tablename__ = 'lancamentos'

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    atividade_id = db.Column(db.Integer, db.ForeignKey('atividades_padrao.id'), nullable=False)
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefas_padrao.id'), nullable=True)

    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)

    duracao_minutos = db.Column(db.Integer, nullable=False, default=0)

    valor_absoluto = db.Column(db.Float, default=0.0)
    unidade_medida_valor = db.Column(db.String(50))

    eficiencia_percentual = db.Column(db.Float, default=0.0)
    dentro_do_prazo = db.Column(db.Boolean, default=True)

    justificativa = db.Column(db.Text)
    observacoes = db.Column(db.Text)

    arquivo_evidencia = db.Column(db.String(255), nullable=True)
    nome_original_arquivo = db.Column(db.String(255), nullable=True)

    correcao_solicitada = db.Column(db.Boolean, default=False)
    correcao_aprovada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)

    data_programada = db.Column(db.Date, default=datetime.utcnow)

    def calcular_duracao(self):
        """Calcula a diferença em minutos entre inicio e fim."""
        if self.data_hora_inicio and self.data_hora_fim:
            delta = self.data_hora_fim - self.data_hora_inicio
            self.duracao_minutos = int(delta.total_seconds() / 60)
            if self.duracao_minutos < 1:
                self.duracao_minutos = 1

    def __repr__(self):
        return f'<Lancamento {self.id} - User {self.usuario_id} - {self.duracao_minutos}min>'