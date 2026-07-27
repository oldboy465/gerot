import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """
    Classe base de configuração.
    Lê as variáveis de ambiente ou define padrões seguros.
    """

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-padrao-insegura-dev'

    dados_dir = os.path.join(basedir, 'dados')
    if not os.path.exists(dados_dir):
        try:
            os.makedirs(dados_dir)
            print(f">>> [CONFIG] Pasta '{dados_dir}' criada com sucesso.")
        except OSError as e:
            print(f">>> [ERRO] Falha ao criar pasta de dados: {e}")

    # Diretório para armazenamento de evidências enviadas pelos operadores[cite: 1]
    upload_dir = os.path.join(basedir, 'app', 'static', 'uploads')
    if not os.path.exists(upload_dir):
        try:
            os.makedirs(upload_dir)
            print(f">>> [CONFIG] Pasta de uploads '{upload_dir}' criada com sucesso.")
        except OSError as e:
            print(f">>> [ERRO] Falha ao criar pasta de uploads: {e}")

    db_path = os.path.join(dados_dir, 'gerot_v1.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 10
    timezone = 'America/Sao_Paulo'

    # Configuração para Upload de Evidências (PDF, PNG, JPG, JPEG de até 5MB)[cite: 1]
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = upload_dir
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}