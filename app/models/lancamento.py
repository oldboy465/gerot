from app import db
from datetime import datetime
from app.services.calculo_bi import CalculoBI

class Lancamento(db.Model):
    """
    Registro de Execução (Log de Produção).
    Representa uma unidade de trabalho entregue pelo Colaborador ou Líder.
    Suporta múltiplos anexos comprobatórios via relacionamento 1:N com AnexoLancamento.
    """
    __tablename__ = 'lancamentos'

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)

    atividade_id = db.Column(db.Integer, db.ForeignKey('atividades_padrao.id'), nullable=False)
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefas_padrao.id'), nullable=True)

    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)

    # Duração calculada estritamente dentro da grade útil (segunda a sexta, 8h às 18h, máx 8h líquidas/dia)
    duracao_minutos = db.Column(db.Integer, nullable=False, default=0)

    valor_absoluto = db.Column(db.Float, default=0.0)
    unidade_medida_valor = db.Column(db.String(50))

    eficiencia_percentual = db.Column(db.Float, default=0.0)
    dentro_do_prazo = db.Column(db.Boolean, default=True)

    justificativa = db.Column(db.Text)
    observacoes = db.Column(db.Text)

    # Campos legados mantidos para compatibilidade retroativa
    arquivo_evidencia = db.Column(db.String(255), nullable=True)
    nome_original_arquivo = db.Column(db.String(255), nullable=True)

    # Relacionamento 1:N para suportar múltiplos anexos por lançamento
    anexos = db.relationship(
        'AnexoLancamento',
        backref='lancamento',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    correcao_solicitada = db.Column(db.Boolean, default=False)
    correcao_aprovada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)

    data_programada = db.Column(db.Date, default=datetime.utcnow)

    def calcular_duracao(self):
        """
        Calcula a duração líquida útil do apontamento utilizando o CalculoBI.
        Respeita a regra de 8h úteis diárias (segunda a sexta, das 8h às 18h).
        """
        if self.data_hora_inicio and self.data_hora_fim:
            minutos_uteis = CalculoBI.calcular_minutos_uteis_intervalo(
                self.data_hora_inicio,
                self.data_hora_fim
            )
            self.duracao_minutos = max(1, minutos_uteis)

    @property
    def lista_anexos(self):
        """Retorna todos os anexos associados, unificando registros legados e novos."""
        anexos_rel = list(self.anexos)
        if not anexos_rel and self.arquivo_evidencia:
            class AnexoLegadoAdapter:
                def __init__(self, filename, original):
                    self.id = 0
                    self.arquivo_salvo = filename
                    self.nome_original = original or filename
                    self.tamanho_bytes = 0
                    self.extensao = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            return [AnexoLegadoAdapter(self.arquivo_evidencia, self.nome_original_arquivo)]
        return anexos_rel

    @property
    def total_anexos(self):
        total = self.anexos.count()
        if total == 0 and self.arquivo_evidencia:
            return 1
        return total

    def __repr__(self):
        return f'<Lancamento {self.id} - User {self.usuario_id} - {self.duracao_minutos}min úteis - {self.total_anexos} anexo(s)>'