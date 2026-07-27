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
    
    # --- Rastreabilidade (Quem e Onde) ---
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Snapshot: Gravamos o setor no momento do lançamento.
    # Se o usuário mudar de setor no futuro, este registro permanece estatisticamente no setor antigo.
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)
    
    # --- O Que Foi Feito ---
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividades_padrao.id'), nullable=False)
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefas_padrao.id'), nullable=True) # Opcional (Micro-tarefa)
    
    # --- Motor de Tempo (Realizado) ---
    # O operador insere manualmente ou o sistema captura o 'agora'
    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)
    
    # Campo Calculado e Persistido (Critical for BI Performance)
    # Diferença entre Fim e Início em minutos
    duracao_minutos = db.Column(db.Integer, nullable=False, default=0)
    
    # --- Dados de Volume (Opcional) ---
    # Ex: Para atividades como "Digitação de Notas", importa quantas notas (valor_absoluto)
    valor_absoluto = db.Column(db.Float, default=0.0)
    unidade_medida_valor = db.Column(db.String(50)) # Ex: "Caixas", "Processos", "Paletes"
    
    # --- Indicadores de Performance (Persistidos) ---
    # Calculados via app.services.calculo_bi antes do commit
    eficiencia_percentual = db.Column(db.Float, default=0.0)
    dentro_do_prazo = db.Column(db.Boolean, default=True) # SLA Flag
    
    # --- Auditoria e Qualidade ---
    justificativa = db.Column(db.Text) # Obrigatório se houver divergência grave ou correção
    observacoes = db.Column(db.Text)   # Notas livres do operador
    
    # Workflow de Correção
    correcao_solicitada = db.Column(db.Boolean, default=False) # Flag se o operador pediu para arrumar
    correcao_aprovada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow) # Log do sistema (timestamp real)
    
    # Data de Competência (Para relatórios: O dia que conta para a meta)
    data_programada = db.Column(db.Date, default=datetime.utcnow)

    def calcular_duracao(self):
        """Calcula a diferença em minutos entre inicio e fim."""
        if self.data_hora_inicio and self.data_hora_fim:
            delta = self.data_hora_fim - self.data_hora_inicio
            # Converte segundos totais para minutos (inteiro)
            self.duracao_minutos = int(delta.total_seconds() / 60)
            # Garante no mínimo 1 minuto para não quebrar divisões
            if self.duracao_minutos < 1:
                self.duracao_minutos = 1

    def __repr__(self):
        return f'<Lancamento {self.id} - User {self.usuario_id} - {self.duracao_minutos}min>'