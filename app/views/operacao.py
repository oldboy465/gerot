import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.atividade import AtividadePadrao, TarefaPadrao
from app.models.lancamento import Lancamento
from app.models.anexo import AnexoLancamento
from app.services.calculo_bi import CalculoBI

operacao_bp = Blueprint('operacao', __name__)

def arquivo_permitido(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@operacao_bp.route('/painel')
@login_required
def painel():
    """
    Dashboard Operacional (Inbox de Apontamento).
    Acessível por Colaboradores e Líderes para lançamento e acompanhamento diário.
    """
    if current_user.is_coordenador:
        setores_ids = current_user.todos_setores_ids
        atividades = AtividadePadrao.query.filter(
            AtividadePadrao.setor_id.in_(setores_ids)
        ).order_by(AtividadePadrao.titulo.asc()).all()
    else:
        atividades = AtividadePadrao.query.filter(
            AtividadePadrao.setor_id == current_user.setor_id,
            db.or_(
                AtividadePadrao.responsavel_id == None,
                AtividadePadrao.responsavel_id == current_user.id
            )
        ).order_by(AtividadePadrao.titulo.asc()).all()

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
    Suporta upload de múltiplos arquivos comprobatórios (PDF, PNG, JPG, JPEG)
    e computa a duração em dias e horas úteis (8h às 18h de seg a sex).
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
            flash('Erro: A Data/Hora Fim deve ser superior ao Início.', 'danger')
            return redirect(url_for('operacao.painel'))

        atividade = AtividadePadrao.query.get(atividade_id)
        if not atividade:
            flash('Atividade não localizada no catálogo.', 'danger')
            return redirect(url_for('operacao.painel'))

        observacao_final = f"[{cronologia.upper()}] {observacao_texto}".strip()

        # Instanciação do lançamento com data de competência
        lancamento = Lancamento(
            usuario_id=current_user.id,
            setor_id=atividade.setor_id if (current_user.is_coordenador and atividade.setor_id in current_user.todos_setores_ids) else current_user.setor_id,
            atividade_id=atividade.id,
            tarefa_id=int(tarefa_id) if tarefa_id else None,
            data_hora_inicio=dt_inicio,
            data_hora_fim=dt_fim,
            observacoes=observacao_final,
            data_programada=dt_inicio.date(),
            data_registro=datetime.utcnow()
        )

        # Cálculo da duração útil e eficiência de acordo com os dias/horas úteis
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

        db.session.add(lancamento)
        db.session.flush()

        # Processamento de Múltiplos Arquivos de Evidência
        arquivos = request.files.getlist('arquivos_evidencia') or request.files.getlist('arquivo_evidencia')
        arquivos_salvos_count = 0

        for file in arquivos:
            if file and file.filename != '':
                if not arquivo_permitido(file.filename):
                    flash(f'Extensão inválida para o arquivo {file.filename}. Envie apenas PDF, PNG ou JPG.', 'warning')
                    continue

                nome_original = secure_filename(file.filename)
                ext = nome_original.rsplit('.', 1)[1].lower() if '.' in nome_original else ''
                filename_salvo = f"evid_{lancamento.id}_{uuid.uuid4().hex[:8]}.{ext}"

                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_salvo)
                file.save(upload_path)
                tamanho = os.path.getsize(upload_path) if os.path.exists(upload_path) else 0

                novo_anexo = AnexoLancamento(
                    lancamento_id=lancamento.id,
                    arquivo_salvo=filename_salvo,
                    nome_original=nome_original,
                    extensao=ext,
                    tamanho_bytes=tamanho
                )
                db.session.add(novo_anexo)

                # Mantém espelho retroativo no primeiro anexo para compatibilidade
                if arquivos_salvos_count == 0:
                    lancamento.arquivo_evidencia = filename_salvo
                    lancamento.nome_original_arquivo = nome_original

                arquivos_salvos_count += 1

        # Atualiza o status da atividade caso tenha sido concluída
        if atividade.status_sla == 'Não Iniciado':
            atividade.status_sla = 'Em Andamento'

        db.session.commit()
        msg_anexo = f" com {arquivos_salvos_count} documento(s) anexado(s)" if arquivos_salvos_count > 0 else ""
        flash(f'Apontamento de produção registrado com sucesso{msg_anexo}!', 'success')

    except ValueError:
        flash('Formato de data e hora inválido.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro técnico ao gravar lançamento: {str(e)}', 'danger')

    return redirect(url_for('operacao.painel'))

@operacao_bp.route('/tarefa/registrar', methods=['POST'])
@login_required
def cadastrar_micro_tarefa():
    """Permite ao Colaborador ou Líder cadastrar uma nova micro-tarefa."""
    atividade_id = request.form.get('atividade_id')
    descricao = request.form.get('descricao')

    if not atividade_id or not descricao:
        flash('Preencha a descrição da nova micro-tarefa.', 'warning')
        return redirect(url_for('operacao.painel'))

    try:
        atividade = AtividadePadrao.query.get(atividade_id)
        if not atividade:
            flash('Atividade não localizada.', 'danger')
            return redirect(url_for('operacao.painel'))

        if current_user.is_coordenador and atividade.setor_id not in current_user.todos_setores_ids:
            flash('Acesso negado para vincular etapas neste setor.', 'danger')
            return redirect(url_for('operacao.painel'))
        elif not current_user.is_coordenador and atividade.setor_id != current_user.setor_id:
            flash('Acesso restrito ao seu próprio setor.', 'danger')
            return redirect(url_for('operacao.painel'))

        nova_t = TarefaPadrao(
            atividade_id=atividade_id,
            descricao=descricao.strip().upper(),
            criado_por_id=current_user.id,
            impacto_percentual=0.0
        )

        db.session.add(nova_t)
        db.session.commit()
        flash(f'Micro-tarefa associada com sucesso a: {atividade.titulo}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar etapa: {str(e)}', 'danger')

    return redirect(url_for('operacao.painel'))

@operacao_bp.route('/historico')
@login_required
def historico():
    """Visualização do histórico do usuário com lista paginada e contagem de anexos."""
    page = request.args.get('page', 1, type=int)

    pagination = Lancamento.query.filter_by(usuario_id=current_user.id)\
        .order_by(Lancamento.data_hora_inicio.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    return render_template('operador/historico.html', pagination=pagination, CalculoBI=CalculoBI)

@operacao_bp.route('/evidencia/download/<filename>')
@login_required
def baixar_evidencia(filename):
    """Permite visualizar/baixar qualquer documento de evidência anexado."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=False)