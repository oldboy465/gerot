import os
import sqlite3
from app import create_app

app = create_app(os.getenv('FLASK_ENV') or 'default')

def upgrade_database():
    """
    Injeta a nova coluna 'cronologia' na tabela 'lancamentos' sem apagar dados.
    Verifica primeiro se a coluna já existe para evitar erros.
    """
    # Determina o caminho do banco a partir da configuração da aplicação
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
    else:
        print(">>> [AVISO] Script otimizado para SQLite. Se estiver usando MySQL/Postgres no Hostgator, use Flask-Migrate.")
        return

    if not os.path.exists(db_path):
        print(f">>> [ERRO] Banco de dados não encontrado em: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verifica se a coluna já existe
        cursor.execute("PRAGMA table_info(lancamentos)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'cronologia' not in columns:
            print(">>> [MIGRAÇÃO] Adicionando coluna 'cronologia' na tabela 'lancamentos'...")
            cursor.execute("ALTER TABLE lancamentos ADD COLUMN cronologia VARCHAR(30) DEFAULT 'Diário'")
            conn.commit()
            print(">>> [SUCESSO] Coluna adicionada com sucesso. O banco de dados foi atualizado!")
        else:
            print(">>> [INFO] A coluna 'cronologia' já existe no banco de dados.")

    except Exception as e:
        print(f">>> [ERRO] Falha ao atualizar o banco: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    with app.app_context():
        upgrade_database()