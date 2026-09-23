import os
from datetime import datetime
from app import create_app, db
from app.models.usuario import Usuario
from app.models.setor import Setor
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.lancamento import Lancamento
from app.models.anexo import AnexoLancamento

app = create_app(os.getenv('FLASK_ENV') or 'default')

def setup_inicial():
    """
    Inicializa o banco de dados e cria os registros mestres essenciais.
    Atualizado para a padronização de e-mails @transultransporte.com.br
    e os novos papéis (admin, diretor, lider, colaborador).
    """
    with app.app_context():
        db.create_all()

        nome_root = "Administração e Planejamento Estratégico"
        setor_root = Setor.query.filter(
            (Setor.sigla == 'ROOT') | (Setor.nome == nome_root)
        ).first()

        if not setor_root:
            setor_root = Setor(
                nome=nome_root,
                sigla="ROOT",
                codigo_interno="ADM-000",
                tipo_setor="Estratégico",
                natureza_atuacao="Apoio",
                missao_setor="Gerir a infraestrutura técnica, governança e rotinas do sistema GEROT.",
                descricao_atividades="Manutenção do banco de dados, gestão de acessos, auditoria e inteligência operacional.",
                nivel_repetitividade="Baixa",
                nivel_complexidade="Alta",
                limite_max_colaboradores=99,
                turno_operacao="24 Horas",
                escala_trabalho="Flexível",
                ativo=True
            )
            db.session.add(setor_root)
        else:
            setor_root.nome = nome_root
            setor_root.sigla = "ROOT"
            setor_root.ativo = True

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f">>> [AVISO] Falha na sincronização do setor ROOT: {e}")
            setor_root = Setor.query.filter_by(sigla='ROOT').first() or Setor.query.filter_by(nome=nome_root).first()

        # Busca pelo admin considerando e-mail institucional homologado ou legado
        email_admin_padrao = "admin@transultransporte.com.br"
        admin_user = Usuario.query.filter(
            (Usuario.username == 'admin') | 
            (Usuario.email == email_admin_padrao) | 
            (Usuario.email == 'admin@transul.com.br')
        ).first()

        if not admin_user:
            admin_user = Usuario(
                username='admin',
                email=email_admin_padrao,
                nome_completo='ADMINISTRADOR DO SISTEMA',
                cpf='000.000.000-00',
                role='admin',
                ativo=True,
                setor_id=setor_root.id if setor_root else 1,
                cargo='Diretor de Tecnologia e Processos',
                funcao='Administração Global',
                telefone_principal='(98) 99999-9999',
                status_cadastro='completo',
                data_admissao=datetime.utcnow().date()
            )
            admin_user.set_password('admin')
            db.session.add(admin_user)
        else:
            admin_user.username = 'admin'
            admin_user.email = email_admin_padrao
            admin_user.set_password('admin')
            admin_user.role = 'admin'
            admin_user.ativo = True
            if setor_root:
                admin_user.setor_id = setor_root.id
            admin_user.status_cadastro = 'completo'

        try:
            db.session.commit()
            if setor_root and not setor_root.responsavel_id:
                setor_root.responsavel_id = admin_user.id
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f">>> [AVISO] Erro ao vincular responsável ao setor raiz: {e}")

if __name__ == '__main__':
    setup_inicial()
    app.run(host='0.0.0.0', port=5000, debug=True)