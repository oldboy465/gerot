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
    # Autorrelacionamento para Hierarquia (Pai/Filho)
    hierarquia_pai_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True)
    
    # Vinculação com a Tabela de Usuários (Responsáveis)
    # Nota: Usamos strings para evitar import circular com o modelo Usuario
    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    substituto_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Classificação do Setor
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
    
    # Jornada e Turno
    turno_operacao = db.Column(db.String(50)) # Diurno, Noturno, 24h, Flexível
    escala_trabalho = db.Column(db.String(50)) # 5x2, 6x1, 12x36, etc.

    # --- RELACIONAMENTOS SQLALCHEMY ---
    
    # Sub-setores (Filhos)
    sub_setores = db.relationship(
        'Setor', 
        backref=db.backref('pai', remote_side=[id]),
        lazy='dynamic'
    )
    
    # Usuários Alocados (Equipe)
    # O backref 'setor_pertencente' permite acessar user.setor_pertencente
    usuarios = db.relationship(
        'Usuario', 
        backref='setor_pertencente', 
        lazy='dynamic', 
        foreign_keys='Usuario.setor_id'
    )
    
    # Atividades vinculadas ao Setor (Catálogo de Serviços)
    atividades = db.relationship('AtividadePadrao', backref='setor_dono', lazy='dynamic')
    
    # Histórico de Lançamentos (Snapshot para BI)
    lancamentos = db.relationship('Lancamento', backref='setor_snapshot', lazy='dynamic')

    # --- MÉTODOS DE SUPORTE ---

    def __repr__(self):
        return f'<Setor {self.sigla} - {self.nome}>'

    def to_dict(self):
        """Converte o objeto para dicionário (Útil para APIs de BI e Dashboards)"""
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
        """
        Retorna a árvore genealógica do setor.
        Ex: "Diretoria Logística > Gerência de Transportes > Setor de Pátio"
        """
        if self.pai:
            return f"{self.pai.get_caminho_hierarquico()} > {self.nome}"
        return self.nome

    def verificar_lotacao_critica(self):
        """Retorna True se o setor atingiu o limite de pessoas (Planejamento de RH)"""
        if self.limite_max_colaboradores <= 0:
            return False
        return self.usuarios.count() >= self.limite_max_colaboradores