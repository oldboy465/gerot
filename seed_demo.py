import os
import random
from datetime import datetime, timedelta
from app import create_app, db
from app.models.usuario import Usuario
from app.models.setor import Setor
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.lancamento import Lancamento
from app.services.calculo_bi import CalculoBI

app = create_app(os.getenv('FLASK_ENV') or 'default')

SENHA_PADRAO = '123456'
DATA_INICIO = datetime(2026, 1, 1)
DATA_FIM = datetime(2026, 5, 5)

SETORES_GERAIS = [
    {"nome": "Tecnologia da Informação", "sigla": "TI", "codigo": "SET-TI", "missao": "Garantir a infraestrutura tecnológica."},
    {"nome": "Recursos Humanos", "sigla": "RH", "codigo": "SET-RH", "missao": "Gestão de talentos e folha de pagamento."},
    {"nome": "Departamento Financeiro", "sigla": "FIN", "codigo": "SET-FIN", "missao": "Controle de fluxo de caixa e faturamento."},
    {"nome": "Logística e Operações", "sigla": "LOG", "codigo": "SET-LOG", "missao": "Gestão de frota e distribuição."},
    {"nome": "Atendimento ao Cliente", "sigla": "SAC", "codigo": "SET-SAC", "missao": "Suporte e satisfação do cliente."}
]

ATIVIDADES_POR_SETOR = {
    "TI": [("Suporte Nível 1", 30, "minutos"), ("Manutenção de Servidores", 2, "horas"), ("Desenvolvimento de Feature", 4, "horas"), ("Backup de Dados", 1, "horas")],
    "RH": [("Fechamento de Folha", 1, "dias"), ("Entrevista de Candidato", 45, "minutos"), ("Integração de Novo Colaborador", 4, "horas"), ("Avaliação de Desempenho", 2, "horas")],
    "FIN": [("Conciliação Bancária", 2, "horas"), ("Pagamento de Fornecedores", 3, "horas"), ("Emissão de Notas Fiscais", 15, "minutos"), ("Auditoria de Contas", 2, "dias")],
    "LOG": [("Roteirização de Frota", 2, "horas"), ("Conferência de Carga", 1, "horas"), ("Manutenção Preventiva", 4, "horas"), ("Inventário de Estoque", 1, "dias")],
    "SAC": [("Atendimento Telefônico", 15, "minutos"), ("Resolução de Ticket", 30, "minutos"), ("Pesquisa de Satisfação", 10, "minutos"), ("Reunião de Alinhamento", 1, "horas")]
}

def gerar_cpf_fake():
    return f"{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(10,99)}"

def popular_banco():
    with app.app_context():
        print("\n>>> [1/5] INICIANDO CRIAÇÃO DE SETORES...")
        setores_criados = {}
        for s_data in SETORES_GERAIS:
            setor = Setor.query.filter_by(sigla=s_data['sigla']).first()
            if not setor:
                setor = Setor(
                    nome=s_data['nome'],
                    sigla=s_data['sigla'],
                    codigo_interno=s_data['codigo'],
                    tipo_setor="Operacional",
                    natureza_atuacao="Direta",
                    missao_setor=s_data['missao'],
                    nivel_complexidade="Média",
                    nivel_repetitividade="Alta",
                    limite_max_colaboradores=10,
                    turno_operacao="Comercial",
                    escala_trabalho="5x2",
                    ativo=True
                )
                db.session.add(setor)
                db.session.commit()
            setores_criados[s_data['sigla']] = setor
            print(f"  - Setor {s_data['sigla']} pronto.")

        print("\n>>> [2/5] INICIANDO CRIAÇÃO DE EQUIPES (Coordenadores e Operadores)...")
        usuarios_criados = []
        seq_user = 1
        for sigla, setor in setores_criados.items():
            username_coord = f"coordenador{seq_user}"
            coord = Usuario.query.filter_by(username=username_coord).first()
            if not coord:
                coord = Usuario(
                    nome_completo=f"Coordenador {sigla}",
                    email=f"coordenador{seq_user}@transul.com.br",
                    username=username_coord,
                    cpf=gerar_cpf_fake(),
                    role='coordenador',
                    ativo=True,
                    setor_id=setor.id,
                    cargo='Coordenador',
                    funcao='Gestão de Equipe',
                    rg_numero="000000000",
                    data_nascimento=datetime(1985, 5, 20).date(),
                    telefone_principal="(98) 99999-0000",
                    cep="65000-000",
                    logradouro="Rua Principal, 123",
                    bairro="Centro",
                    cidade="São Luís",
                    uf_endereco="MA",
                    data_admissao=datetime(2020, 1, 10).date(),
                    status_cadastro='completo'
                )
                coord.set_password(SENHA_PADRAO)
                db.session.add(coord)
                db.session.commit()

            setor.responsavel_id = coord.id
            db.session.commit()
            seq_user += 1

            for i in range(1, 7):
                username_op = f"operador{seq_user}"
                op = Usuario.query.filter_by(username=username_op).first()
                if not op:
                    op = Usuario(
                        nome_completo=f"Operador {i} {sigla}",
                        email=f"operador{seq_user}@transul.com.br",
                        username=username_op,
                        cpf=gerar_cpf_fake(),
                        role='operador',
                        ativo=True,
                        setor_id=setor.id,
                        cargo='Assistente',
                        funcao='Execução de Rotinas',
                        rg_numero=f"11122233{i}",
                        data_nascimento=datetime(1995, 8, 15).date(),
                        telefone_principal=f"(98) 98888-000{i}",
                        cep="65000-000",
                        logradouro="Av. Principal, 456",
                        bairro="Renascença",
                        cidade="São Luís",
                        uf_endereco="MA",
                        data_admissao=datetime(2024, 3, 1).date(),
                        status_cadastro='completo'
                    )
                    op.set_password(SENHA_PADRAO)
                    db.session.add(op)
                    db.session.commit()
                usuarios_criados.append(op)
                seq_user += 1
            print(f"  - Equipe de {sigla} (1 Coord, 6 Ops) pronta.")

        print("\n>>> [3/5] CRIANDO ATIVIDADES E TAREFAS...")
        atividades_criadas = []
        for sigla, setor in setores_criados.items():
            lista_atividades = ATIVIDADES_POR_SETOR[sigla]
            for titulo, tempo_val, tempo_und in lista_atividades:
                atv = AtividadePadrao.query.filter_by(titulo=titulo, setor_id=setor.id).first()
                if not atv:
                    atv = AtividadePadrao(
                        titulo=titulo,
                        descricao="Procedimento Operacional Padrão executado conforme orientação do setor.",
                        setor_id=setor.id,
                        is_rotineira=True,
                        status_sla=random.choice(["Em Andamento", "Concluído", "Cancelado"]),
                        tempo_estimado_valor=tempo_val,
                        tempo_estimado_unidade=tempo_und
                    )
                    db.session.add(atv)
                    db.session.commit()

                    for t in range(1, 3):
                        tarefa = TarefaPadrao(
                            atividade_id=atv.id,
                            criado_por_id=setor.responsavel_id,
                            descricao=f"Etapa {t} de {titulo}",
                            impacto_percentual=50.0
                        )
                        db.session.add(tarefa)
                    db.session.commit()
                atividades_criadas.append(atv)
            print(f"  - Atividades e Tarefas de {sigla} criadas.")

        print(f"\n>>> [4/5] SIMULANDO LANÇAMENTOS DE PRODUÇÃO ({DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')})...")

        dias_uteis = []
        dia_atual = DATA_INICIO
        while dia_atual <= DATA_FIM:
            if dia_atual.weekday() < 5:
                dias_uteis.append(dia_atual)
            dia_atual += timedelta(days=1)

        total_lancamentos = 0
        for op in usuarios_criados:
            atividades_op = [a for a in atividades_criadas if a.setor_id == op.setor_id]
            if not atividades_op:
                continue

            for dia in dias_uteis:
                qtd_atv_dia = random.randint(2, 4)
                hora_atual = dia.replace(hour=8, minute=random.randint(0, 30))

                for _ in range(qtd_atv_dia):
                    atv_escolhida = random.choice(atividades_op)
                    meta_minutos = atv_escolhida.tempo_convertido_minutos
                    fator_variacao = random.uniform(0.8, 1.3)
                    duracao_real_minutos = max(5, int(meta_minutos * fator_variacao))

                    hora_fim = hora_atual + timedelta(minutes=duracao_real_minutos)

                    if hora_fim.hour >= 12 and hora_atual.hour < 12:
                        hora_atual = hora_atual.replace(hour=13, minute=random.randint(0, 30))
                        hora_fim = hora_atual + timedelta(minutes=duracao_real_minutos)

                    if hora_fim.hour >= 18:
                        break

                    efic = CalculoBI.calcular_eficiencia(meta_minutos, duracao_real_minutos)
                    dentro_prazo = duracao_real_minutos <= (meta_minutos * 1.05)
                    pedir_correcao = random.random() < 0.05

                    lancamento = Lancamento(
                        usuario_id=op.id,
                        setor_id=op.setor_id,
                        atividade_id=atv_escolhida.id,
                        data_hora_inicio=hora_atual,
                        data_hora_fim=hora_fim,
                        duracao_minutos=duracao_real_minutos,
                        eficiencia_percentual=efic,
                        dentro_do_prazo=dentro_prazo,
                        observacoes="Executado conforme POP." if not pedir_correcao else "Solicito verificação de ajuste.",
                        correcao_solicitada=pedir_correcao,
                        data_programada=dia.date()
                    )
                    db.session.add(lancamento)
                    total_lancamentos += 1

                    hora_atual = hora_fim + timedelta(minutes=random.randint(5, 15))

        db.session.commit()
        print(f"  - {total_lancamentos} lançamentos gerados com sucesso!")
        print("\n>>> [5/5] BANCO DE DADOS POPULADO COM SUCESSO!")

def limpar_banco():
    with app.app_context():
        print("\n>>> [1/2] LOCALIZANDO DADOS...")
        setores_alvo = Setor.query.filter(Setor.codigo_interno.like('SET-%')).all()

        if not setores_alvo:
            print("  - Nenhum dado encontrado para limpar.")
            return

        setor_ids = [s.id for s in setores_alvo]

        print(">>> [2/2] EXCLUINDO DADOS EM CASCATA...")
        try:
            Lancamento.query.filter(Lancamento.setor_id.in_(setor_ids)).delete(synchronize_session=False)

            tarefas_ids = db.session.query(TarefaPadrao.id).join(AtividadePadrao).filter(AtividadePadrao.setor_id.in_(setor_ids)).subquery()
            TarefaPadrao.query.filter(TarefaPadrao.id.in_(tarefas_ids)).delete(synchronize_session=False)

            AtividadePadrao.query.filter(AtividadePadrao.setor_id.in_(setor_ids)).delete(synchronize_session=False)

            Usuario.query.filter(Usuario.setor_id.in_(setor_ids)).delete(synchronize_session=False)

            Setor.query.filter(Setor.id.in_(setor_ids)).delete(synchronize_session=False)

            db.session.commit()
            print("\n>>> LIMPEZA CONCLUÍDA!")

        except Exception as e:
            db.session.rollback()
            print(f">>> [ERRO CRÍTICO] Falha ao limpar o banco: {str(e)}")

if __name__ == '__main__':
    print("="*50)
    print(" 🛠️  GEROT V2 - FÁBRICA DE DADOS 🛠️")
    print("="*50)
    print("1 - Popular Banco")
    print("2 - Limpar Banco")
    print("0 - Sair")

    escolha = input("\nDigite a opção desejada: ")

    if escolha == '1':
        popular_banco()
    elif escolha == '2':
        limpar_banco()
    elif escolha == '0':
        print("Encerrando...")
    else:
        print("Opção inválida.")