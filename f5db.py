import os
import sqlite3

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'dados', 'gerot_v1.db')

def upgrade_database():
    if not os.path.exists(db_path):
        print(f">>> [ERRO] Banco de dados não encontrado em: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Migrações na tabela lancamentos
        cursor.execute("PRAGMA table_info(lancamentos)")
        columns_lanc = [col[1] for col in cursor.fetchall()]

        colunas_necessarias_lanc = [
            ("arquivo_evidencia", "VARCHAR(255)"),
            ("nome_original_arquivo", "VARCHAR(255)"),
            ("cronologia", "VARCHAR(30) DEFAULT 'Diário'")
        ]

        for col_nome, col_tipo in colunas_necessarias_lanc:
            if col_nome not in columns_lanc:
                print(f">>> [MIGRAÇÃO] Adicionando coluna '{col_nome}' em lancamentos...")
                cursor.execute(f"ALTER TABLE lancamentos ADD COLUMN {col_nome} {col_tipo}")
                print(f">>> [SUCESSO] Coluna '{col_nome}' criada!")

        # 2. Migrações na tabela atividades_padrao (Correção do status_sla)
        cursor.execute("PRAGMA table_info(atividades_padrao)")
        columns_atv = [col[1] for col in cursor.fetchall()]

        if "status_sla" not in columns_atv:
            print(">>> [MIGRAÇÃO] Adicionando coluna 'status_sla' em atividades_padrao...")
            cursor.execute("ALTER TABLE atividades_padrao ADD COLUMN status_sla VARCHAR(30) DEFAULT 'Em Andamento'")
            print(">>> [SUCESSO] Coluna 'status_sla' criada com sucesso!")
        else:
            print(">>> [INFO] Coluna 'status_sla' já existe.")

        conn.commit()
        print(">>> [CONCLUÍDO] Banco de dados atualizado com sucesso!")

    except Exception as e:
        print(f">>> [ERRO CRÍTICO] {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    upgrade_database()