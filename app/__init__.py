from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config

# Inicialização das Extensões (Globais)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar o sistema GEROT.'
    login_manager.login_message_category = 'warning'

    # --- REGISTRO DE BLUEPRINTS (MÓDULOS) ---
    from app.views.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.views.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.views.gestao import gestao_bp
    app.register_blueprint(gestao_bp, url_prefix='/gestao')

    from app.views.operacao import operacao_bp
    app.register_blueprint(operacao_bp, url_prefix='/operacao')

    from app.views.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Novo: Módulo de Relatórios e Exportação
    from app.views.relatorios import relatorios_bp
    app.register_blueprint(relatorios_bp, url_prefix='/relatorios')

    from flask import redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'operador':
                return redirect(url_for('operacao.painel'))
            elif current_user.role == 'coordenador':
                return redirect(url_for('gestao.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('erros/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('erros/500.html'), 500

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models.usuario import Usuario
    return Usuario.query.get(int(user_id))