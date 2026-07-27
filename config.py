import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """
    Classe base de configuração.
    Lê as variáveis de ambiente ou define padrões seguros.
    """
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-padrao-insegura-dev'
    
    # --- CORREÇÃO DO ERRO DE BANCO DE DADOS ---
    # Define o caminho da pasta 'dados'
    dados_dir = os.path.join(basedir, 'dados')
    
    # Cria a pasta 'dados' se ela não existir
    if not os.path.exists(dados_dir):
        try:
            os.makedirs(dados_dir)
            print(f">>> [CONFIG] Pasta '{dados_dir}' criada com sucesso.")
        except OSError as e:
            print(f">>> [ERRO] Falha ao criar pasta de dados: {e}")

    # Banco de Dados
    # Tenta ler do .env, senão usa SQLite local na pasta 'dados'
    db_path = os.path.join(dados_dir, 'gerot_v1.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
    
    # Otimização do SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações de Paginação e Upload
    ITEMS_PER_PAGE = 10
    
    # Configurações de Tempo e Fuso Horário
    timezone = 'America/Sao_Paulo'

    @staticmethod
    def init_app(app):
        """Método padrão para inicialização de configurações"""
        pass

class DevelopmentConfig(Config):
    """Configurações para ambiente de Desenvolvimento (Local)"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configurações para ambiente de Produção"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

# Dicionário para facilitar a seleção do ambiente no __init__.py
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}