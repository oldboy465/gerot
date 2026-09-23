from app import db
from datetime import datetime

class AnexoLancamento(db.Model):
    """
    Entidade para suportar múltiplos anexos de evidência por lançamento.
    Armazena o nome real do arquivo no disco, nome de upload amigável e metadados.
    """
    __tablename__ = 'anexos_lancamento'

    id = db.Column(db.Integer, primary_key=True)
    lancamento_id = db.Column(db.Integer, db.ForeignKey('lancamentos.id', ondelete='CASCADE'), nullable=False, index=True)

    arquivo_salvo = db.Column(db.String(255), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    extensao = db.Column(db.String(10), nullable=True)
    tamanho_bytes = db.Column(db.Integer, default=0)

    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AnexoLancamento {self.id} - {self.nome_original} ({self.arquivo_salvo})>'