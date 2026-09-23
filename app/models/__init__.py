"""
Módulo de Inicialização dos Modelos do GEROT.
Centraliza a importação de todas as entidades do banco de dados para garantir
o carregamento adequado das migrações do Alembic/Flask-Migrate e do db.create_all().
"""

from app.models.setor import Setor
from app.models.usuario import Usuario, usuario_setores_secundarios
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.lancamento import Lancamento
from app.models.anexo import AnexoLancamento

__all__ = [
    'Setor',
    'Usuario',
    'usuario_setores_secundarios',
    'AtividadePadrao',
    'TarefaPadrao',
    'Lancamento',
    'AnexoLancamento'
]