from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app.models.lancamento import Lancamento
from app.models.usuario import Usuario
from app.models.setor import Setor
from app.models.atividade import AtividadePadrao
from app.services.exportacao import ExportacaoService

relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.before_request
@login_required
def check_permission():
    """Garante que operadores comuns não acessem os relatórios corporativos"""
    if current_user.role not in ['admin', 'gestor', 'coordenador']:
        flash('Acesso restrito. Área exclusiva para a gestão.', 'danger')
        return redirect(url_for('operacao.painel'))

@relatorios_bp.route('/gerador', methods=['GET', 'POST'])
def gerador():
    """
    Interface e Motor de Geração de Relatórios.
    Aplica filtros dinâmicos e exporta em Excel, PDF (View) ou WhatsApp.
    """
    # Cascata de Segurança para Popular os Filtros Dropdown
    if current_user.is_admin or current_user.is_gestor:
        setores = Setor.query.order_by(Setor.nome).all()
        usuarios = Usuario.query.order_by(Usuario.nome_completo).all()
    else:
        # Coordenador só vê sua equipe e seu setor
        setores = Setor.query.filter_by(id=current_user.setor_id).all()
        usuarios = Usuario.query.filter_by(setor_id=current_user.setor_id).order_by(Usuario.nome_completo).all()

    # Variável para armazenar texto do WPP caso a ação seja essa
    texto_wpp = None

    if request.method == 'POST':
        acao = request.form.get('acao') or request.form.get('exportar') # 'excel', 'impressao', ou 'whatsapp'

        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        setor_id = request.form.get('setor_id')
        usuario_id = request.form.get('usuario_id')

        query = Lancamento.query

        # Trava de Segurança Final: Coordenador não pode burlar o HTML para buscar outro setor
        if not (current_user.is_admin or current_user.is_gestor):
            query = query.filter(Lancamento.setor_id == current_user.setor_id)
        elif setor_id:
            query = query.filter(Lancamento.setor_id == setor_id)

        # Filtros Dinâmicos de Data
        periodo_str = "Todo o período"
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(Lancamento.data_hora_inicio >= dt_inicio)
                periodo_str = f"A partir de {dt_inicio.strftime('%d/%m/%Y')}"
            except ValueError:
                pass

        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d')
                dt_fim = dt_fim.replace(hour=23, minute=59, second=59) # Cobre o dia inteiro
                query = query.filter(Lancamento.data_hora_fim <= dt_fim)
                periodo_str = f"De {data_inicio} até {dt_fim.strftime('%d/%m/%Y')}" if data_inicio else f"Até {dt_fim.strftime('%d/%m/%Y')}"
            except ValueError:
                pass

        # Filtro de Usuário
        if usuario_id:
            query = query.filter(Lancamento.usuario_id == usuario_id)

        lancamentos = query.order_by(Lancamento.data_hora_inicio.desc()).all()

        if not lancamentos:
            flash('Nenhum dado de produção encontrado para os filtros selecionados.', 'warning')
            return redirect(url_for('relatorios.gerador'))

        # --- ROTAS DE EXPORTAÇÃO BASEADA NA AÇÃO ---

        if acao == 'excel':
            return ExportacaoService.gerar_excel(lancamentos)

        elif acao in ['pdf', 'impressao']:
            # Renderiza um HTML limpo para impressão (Geração de PDF nativa do navegador)
            return render_template('gestao/relatorio_impressao.html', 
                                   lancamentos=lancamentos, 
                                   periodo=periodo_str,
                                   now=datetime.utcnow().strftime('%d/%m/%Y %H:%M'))

        elif acao == 'whatsapp':
            setor_obj = Setor.query.get(setor_id) if setor_id else None
            setor_nome = setor_obj.nome if setor_obj else "Todos"

            user_obj = Usuario.query.get(usuario_id) if usuario_id else None
            usuario_nome = user_obj.nome_completo if user_obj else "Todos"

            texto_wpp = ExportacaoService.gerar_texto_whatsapp(lancamentos, periodo_str, setor_nome, usuario_nome)

    return render_template('gestao/relatorios.html', setores=setores, usuarios=usuarios, texto_wpp=texto_wpp)

@relatorios_bp.route('/ficha/<int:id>')
def ficha_tecnica(id):
    """Renderiza a Ficha Técnica / Procedimento Operacional Padrão (POP)"""
    atividade = AtividadePadrao.query.get_or_404(id)
    now_date = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    return render_template('relatorios/ficha_padrao.html', atividade=atividade, now_date=now_date)