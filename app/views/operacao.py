import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.lancamento import Lancamento
from app.services.calculo_bi import CalculoBI

operacao_bp = Blueprint('operacao', __name__)

def arquivo_permitido(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@operacao_bp.route('/painel')
@login_required
def painel():
    """
    Dashboard Operacional (Inbox).
    Mostra as atividades disponíveis para o setor ou atribuídas ao usuário.
    Renders app/templates/operador/painel.html
    """
    atividades = AtividadePadrao.query.filter(
        AtividadePadrao.setor_id == current_user.setor_id,
        db.or_(
            AtividadePadrao.responsavel_id == None,
            AtividadePadrao.responsavel_id == current_user.id
        )
    ).all()

    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    historico_hoje = Lancamento.query.filter(
        Lancamento.usuario_id == current_user.id,
        Lancamento.data_hora_inicio >= hoje_inicio
    ).order_by(Lancamento.data_hora_inicio.desc()).all()

    return render_template(
        'operador/painel.html',
        atividades=atividades,
        historico=historico_hoje,
        agora=datetime.now(),
        CalculoBI=CalculoBI
    )

@operacao_bp.route('/lancamento/novo', methods=['POST'])
@login_required
def novo_lancamento():
    """
    Processa o formulário de Apontamento de Produção.
    Suporta diversas cronologias e upload de arquivo de evidência (PDF, PNG, JPG até 5MB).
    """
    atividade_id = request.form.get('atividade_id')
    inicio_str = request.form.get('data_hora_inicio')
    fim_str = request.form.get('data_hora_fim')
    observacao_texto = request.form.get('observacao') or request.form.get('observacoes') or ''
    tarefa_id = request.form.get('tarefa_id')
    cronologia = request.form.get('cronologia', 'Diário')

    if not atividade_id or not inicio_str or not fim_str:
        flash('Todos os campos obrigatórios devem ser preenchidos.', 'danger')
        return redirect(url_for('operacao.painel'))

    try:
        dt_inicio = datetime.strptime(inicio_str, '%Y-%m-%dT%H:%M')
        dt_fim = datetime.strptime(fim_str, '%Y-%m-%dT%H:%M')

        if dt_fim <= dt_inicio:
            flash('Erro: A Data/Hora Fim deve ser maior que o Início.', 'danger')
            return redirect(url_for('operacao.painel'))

        atividade = AtividadePadrao.query.get(atividade_id)
        if not atividade:
            flash('Atividade não encontrada.', 'danger')
            return redirect(url_for('operacao.painel'))

        observacao_final = f"[{cronologia.upper()}] {observacao_texto}".strip()

        # Processamento de Arquivo de Evidência
        filename_salvo = None
        nome_original = None

        if 'arquivo_evidencia' in request.files:
            file = request.files['arquivo_evidencia']
            if file and file.filename != '':
                if not arquivo_permitido(file.filename):
                    flash('Extensão de arquivo não permitida. Envie apenas PDF, PNG, JPG ou JPEG.', 'danger')
                    return redirect(url_for('operacao.painel'))

                nome_original = secure_filename(file.filename)
                ext = nome_original.rsplit('.', 1)[1].lower() if '.' in nome_original else ''
                filename_salvo = f"evidencia_{current_user.id}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}.{ext}"

                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_salvo)
                file.save(upload_path)

        lancamento = Lancamento(
            usuario_id=current_user.id,
            setor_id=current_user.setor_id,
            atividade_id=atividade.id,
            tarefa_id=int(tarefa_id) if tarefa_id else None,
            data_hora_inicio=dt_inicio,
            data_hora_fim=dt_fim,
            observacoes=observacao_final,
            data_programada=dt_inicio.date(),
            arquivo_evidencia=filename_salvo,
            nome_original_arquivo=nome_original
        )

        lancamento.calcular_duracao()

        if atividade.tempo_convertido_minutos > 0:
            efic = CalculoBI.calcular_eficiencia(
                tempo_meta_minutos=atividade.tempo_convertido_minutos,
                tempo_realizado_minutos=lancamento.duracao_minutos
            )
            lancamento.eficiencia_percentual = efic
            lancamento.dentro_do_prazo = lancamento.duracao_minutos <= (atividade.tempo_convertido_minutos * 1.05)
        else:
            lancamento.eficiencia_percentual = 100.0
            lancamento.dentro_do_prazo = True

        cronologias_longas = ['SEMANAL', 'QUINZENAL', 'MENSAL', 'BIMESTRAL', 'TRIMESTRAL', 'QUADRIMESTRAL', 'SEMESTRAL', 'ANUAL']

        if cronologia.upper() not in cronologias_longas:
            conflito = Lancamento.query.filter(
                Lancamento.usuario_id == current_user.id,
                Lancamento.data_hora_inicio < dt_fim,
                Lancamento.data_hora_fim > dt_inicio,
                ~Lancamento.observacoes.ilike('%[SEMANAL]%'),
                ~Lancamento.observacoes.ilike('%[MENSAL]%'),
                ~Lancamento.observacoes.ilike('%[ANUAL]%')
            ).first()

            if conflito:
                flash(f'Atenção: Este horário conflita com a atividade "{conflito.atividade_referencia.titulo}". Lançamento salvo com ressalva.', 'warning')
            else:
                flash('Atividade registrada com sucesso!', 'success')
        else:
            flash(f'Atividade {cronologia.lower()} registrada e contabilizada no período!', 'success')

        db.session.add(lancamento)
        db.session.commit()

    except ValueError:
        flash('Erro no formato da data/hora. Utilize o seletor padrão.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro técnico ao salvar: {str(e)}', 'danger')

    return redirect(url_for('operacao.painel'))

@operacao_bp.route('/tarefa/registrar', methods=['POST'])
@login_required
def cadastrar_micro_tarefa():
    """
    Permite ao Operador cadastrar uma nova micro-tarefa.
    """
    atividade_id = request.form.get('atividade_id')
    descricao = request.form.get('descricao')

    if not atividade_id or not descricao:
        flash('Preencha a descrição da nova tarefa.', 'warning')
        return redirect(url_for('operacao.painel'))

    try:
        atividade = AtividadePadrao.query.get(atividade_id)
        if not atividade or atividade.setor_id != current_user.setor_id:
            flash('Atividade não localizada ou acesso negado.', 'danger')
            return redirect(url_for('operacao.painel'))

        nova_t = TarefaPadrao(
            atividade_id=atividade_id,
            descricao=descricao.upper(),
            criado_por_id=current_user.id,
            impacto_percentual=0.0
        )

        db.session.add(nova_t)
        db.session.commit()
        flash(f'Micro-tarefa vinculada com sucesso a: {atividade.titulo}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar tarefa: {str(e)}', 'danger')

    return redirect(url_for('operacao.painel'))

@operacao_bp.route('/historico')
@login_required
def historico():
    """
    Visualização completa do histórico pessoal paginado a cada 10 registros.
    Renders app/templates/operador/historico.html
    """
    page = request.args.get('page', 1, type=int)

    pagination = Lancamento.query.filter_by(usuario_id=current_user.id)\
        .order_by(Lancamento.data_hora_inicio.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    return render_template('operador/historico.html', pagination=pagination, CalculoBI=CalculoBI)

@operacao_bp.route('/evidencia/download/<filename>')
@login_required
def baixar_evidencia(filename):
    """
    Permite visualizar/baixar o arquivo de evidência anexado ao lançamento.
    """
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=False)