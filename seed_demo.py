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

# --- CONFIGURAÇÕES DO GERADOR ---
SENHA_PADRAO = 'allspark'
DATA_INICIO = datetime(2026, 1, 1)
DATA_FIM = datetime(2026, 5, 5)

SETORES_DEMO = [
    {"nome": "Tecnologia da Informação", "sigla": "TI", "codigo": "DEMO-TI", "missao": "Garantir a infraestrutura tecnológica."},
    {"nome": "Recursos Humanos", "sigla": "RH", "codigo": "DEMO-RH", "missao": "Gestão de talentos e folha de pagamento."},
    {"nome": "Departamento Financeiro", "sigla": "FIN", "codigo": "DEMO-FIN", "missao": "Controle de fluxo de caixa e faturamento."},
    {"nome": "Logística e Operações", "sigla": "LOG", "codigo": "DEMO-LOG", "missao": "Gestão de frota e distribuição."},
    {"nome": "Atendimento ao Cliente", "sigla": "SAC", "codigo": "DEMO-SAC", "missao": "Suporte e satisfação do cliente."}
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
        print("\n>>> [1/5] INICIANDO CRIAÇÃO DE SETORES [DEMO]...")
        setores_criados = {}
        for s_data in SETORES_DEMO:
            setor = Setor(
                nome=f"[DEMO] {s_data['nome']}",
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
            print(f"  - Setor {s_data['sigla']} criado.")

        print("\n>>> [2/5] INICIANDO CRIAÇÃO DE EQUIPES (Coordenadores e Operadores)...")
        usuarios_criados = []
        for sigla, setor in setores_criados.items():
            # Cria Coordenador
            coord = Usuario(
                nome_completo=f"Coordenador {sigla} [DEMO]",
                email=f"coord.{sigla.lower()}@demo.com.br",
                username=f"coord_{sigla.lower()}",
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
                logradouro="Rua Fictícia, 123",
                bairro="Centro",
                cidade="São Luís",
                uf_endereco="MA",
                data_admissao=datetime(2020, 1, 10).date(),
                status_cadastro='completo'
            )
            coord.set_password(SENHA_PADRAO)
            db.session.add(coord)
            db.session.commit()
            
            # Atualiza responsável do setor
            setor.responsavel_id = coord.id
            db.session.commit()

            # Cria 6 Operadores
            for i in range(1, 7):
                op = Usuario(
                    nome_completo=f"Operador {i} {sigla} [DEMO]",
                    email=f"op{i}.{sigla.lower()}@demo.com.br",
                    username=f"op{i}_{sigla.lower()}",
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
                    logradouro="Av. Fictícia, 456",
                    bairro="Renascença",
                    cidade="São Luís",
                    uf_endereco="MA",
                    data_admissao=datetime(2024, 3, 1).date(),
                    status_cadastro='completo'
                )
                op.set_password(SENHA_PADRAO)
                db.session.add(op)
                usuarios_criados.append(op)
            db.session.commit()
            print(f"  - Equipe de {sigla} (1 Coord, 6 Ops) criada.")

        print("\n>>> [3/5] CRIANDO ATIVIDADES E TAREFAS...")
        atividades_criadas = []
        for sigla, setor in setores_criados.items():
            lista_atividades = ATIVIDADES_POR_SETOR[sigla]
            for titulo, tempo_val, tempo_und in lista_atividades:
                atv = AtividadePadrao(
                    titulo=f"[DEMO] {titulo}",
                    descricao="Atividade gerada automaticamente para demonstração.",
                    setor_id=setor.id,
                    is_rotineira=True,
                    tempo_estimado_valor=tempo_val,
                    tempo_estimado_unidade=tempo_und
                )
                db.session.add(atv)
                db.session.commit()
                atividades_criadas.append(atv)

                # Cria 2 micro-tarefas para cada atividade
                for t in range(1, 3):
                    tarefa = TarefaPadrao(
                        atividade_id=atv.id,
                        criado_por_id=setor.responsavel_id,
                        descricao=f"Etapa {t} de {titulo}",
                        impacto_percentual=50.0
                    )
                    db.session.add(tarefa)
                db.session.commit()
            print(f"  - Atividades e Tarefas de {sigla} criadas.")

        print(f"\n>>> [4/5] SIMULANDO LANÇAMENTOS DE PRODUÇÃO ({DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')})...")
        print("  - Isso pode levar alguns segundos. Por favor, aguarde.")
        
        # Gerador de dias pulando fins de semana
        dias_uteis = []
        dia_atual = DATA_INICIO
        while dia_atual <= DATA_FIM:
            if dia_atual.weekday() < 5:  # 0 a 4 = Segunda a Sexta
                dias_uteis.append(dia_atual)
            dia_atual += timedelta(days=1)

        total_lancamentos = 0
        for op in usuarios_criados:
            # Pega as atividades do setor do operador
            atividades_op = [a for a in atividades_criadas if a.setor_id == op.setor_id]
            
            for dia in dias_uteis:
                # Cada operador faz de 2 a 4 atividades por dia
                qtd_atv_dia = random.randint(2, 4)
                hora_atual = dia.replace(hour=8, minute=random.randint(0, 30)) # Começa o dia entre 08:00 e 08:30
                
                for _ in range(qtd_atv_dia):
                    atv_escolhida = random.choice(atividades_op)
                    
                    # Simula um tempo gasto (entre 80% e 130% da meta para ter variações de eficiência)
                    meta_minutos = atv_escolhida.tempo_convertido_minutos
                    fator_variacao = random.uniform(0.8, 1.3)
                    duracao_real_minutos = max(5, int(meta_minutos * fator_variacao))
                    
                    hora_fim = hora_atual + timedelta(minutes=duracao_real_minutos)
                    
                    # Pausa pro almoço se passar de 12:00
                    if hora_fim.hour >= 12 and hora_atual.hour < 12:
                        hora_atual = hora_atual.replace(hour=13, minute=random.randint(0, 30))
                        hora_fim = hora_atual + timedelta(minutes=duracao_real_minutos)
                    
                    # Não deixa passar das 18h
                    if hora_fim.hour >= 18:
                        break

                    efic = CalculoBI.calcular_eficiencia(meta_minutos, duracao_real_minutos)
                    dentro_prazo = duracao_real_minutos <= (meta_minutos * 1.05)
                    
                    # Adiciona uma anomalia (correção) em 5% dos casos para popular o dashboard do coordenador
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
                        observacoes="[DIÁRIO] Executado conforme POP." if not pedir_correcao else "[DIÁRIO] Erro na execução, solicito ajuste.",
                        correcao_solicitada=pedir_correcao,
                        data_programada=dia.date()
                    )
                    db.session.add(lancamento)
                    total_lancamentos += 1
                    
                    # Próxima atividade começa de 5 a 15 min depois
                    hora_atual = hora_fim + timedelta(minutes=random.randint(5, 15))
                    
        db.session.commit()
        print(f"  - {total_lancamentos} lançamentos gerados com sucesso!")
        print("\n>>> [5/5] BANCO DE DADOS POPULADO COM SUCESSO! APROVEITE A DEMONSTRAÇÃO.")


def limpar_banco():
    with app.app_context():
        print("\n>>> [1/2] LOCALIZANDO DADOS FALSOS [DEMO]...")
        # Localiza setores criados pela Demo
        setores_demo = Setor.query.filter(Setor.codigo_interno.like('DEMO-%')).all()
        
        if not setores_demo:
            print("  - Nenhum dado de demonstração encontrado para limpar.")
            return

        setor_ids = [s.id for s in setores_demo]
        
        print(">>> [2/2] EXCLUINDO DADOS EM CASCATA...")
        try:
            # 1. Apagar Lançamentos
            Lancamento.query.filter(Lancamento.setor_id.in_(setor_ids)).delete(synchronize_session=False)
            
            # 2. Apagar Tarefas
            tarefas_ids = db.session.query(TarefaPadrao.id).join(AtividadePadrao).filter(AtividadePadrao.setor_id.in_(setor_ids)).subquery()
            TarefaPadrao.query.filter(TarefaPadrao.id.in_(tarefas_ids)).delete(synchronize_session=False)
            
            # 3. Apagar Atividades
            AtividadePadrao.query.filter(AtividadePadrao.setor_id.in_(setor_ids)).delete(synchronize_session=False)
            
            # 4. Apagar Usuários
            Usuario.query.filter(Usuario.setor_id.in_(setor_ids)).delete(synchronize_session=False)
            
            # 5. Apagar Setores
            Setor.query.filter(Setor.id.in_(setor_ids)).delete(synchronize_session=False)
            
            db.session.commit()
            print("\n>>> LIMPEZA CONCLUÍDA! Seu sistema voltou ao estado original (Apenas Admin).")
            
        except Exception as e:
            db.session.rollback()
            print(f">>> [ERRO CRÍTICO] Falha ao limpar o banco: {str(e)}")


if __name__ == '__main__':
    print("="*50)
    print(" 🛠️  GEROT V2 - FÁBRICA DE DADOS DE DEMONSTRAÇÃO 🛠️")
    print("="*50)
    print("1 - Popular Banco (Criar 5 Setores, 35 Usuários, Atividades e Lançamentos)")
    print("2 - Limpar Banco (Apagar apenas os dados gerados pela demonstração)")
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