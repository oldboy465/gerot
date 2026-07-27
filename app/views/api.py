from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.lancamento import Lancamento
from app.models.atividade import AtividadePadrao
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)

@api_bp.route('/status')
def status():
    """Health Check simples para monitoramento"""
    return jsonify({
        'status': 'online', 
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@api_bp.route('/stats/usuario')
@api_bp.route('/stats/usuario/semanal')
@login_required
def stats_usuario():
    """
    Retorna a produtividade do usuário com suporte a múltiplas cronologias.
    Padrão: 7 dias (semanal), mas aceita diário, quinzenal, mensal, bimestral, trimestral, quadrimestral, semestral e anual.
    """
    cronologia = request.args.get('cronologia', 'semanal').lower()
    hoje = datetime.now().date()
    
    # Mapeamento de cronologias para timedelta (dias)
    dias_map = {
        'diario': 1, 'semanal': 7, 'quinzenal': 15, 'mensal': 30,
        'bimestral': 60, 'trimestral': 90, 'quadrimestral': 120,
        'semestral': 180, 'anual': 365
    }
    dias_subtrair = dias_map.get(cronologia, 7)
    inicio_periodo = hoje - timedelta(days=dias_subtrair)
    
    # Consulta agrupada por dia
    resultados = db.session.query(
        func.date(Lancamento.data_hora_inicio).label('data'),
        func.sum(Lancamento.duracao_minutos).label('total_minutos')
    ).filter(
        Lancamento.usuario_id == current_user.id,
        Lancamento.data_hora_inicio >= inicio_periodo
    ).group_by(func.date(Lancamento.data_hora_inicio)).all()
    
    dados = []
    for r in resultados:
        dados.append({
            'data': r.data,
            'minutos': r.total_minutos,
            'horas': round(r.total_minutos / 60, 2)
        })
        
    return jsonify({
        'usuario': current_user.username,
        'periodo': cronologia,
        'dados': dados
    })

@api_bp.route('/atividades/buscar')
@login_required
def buscar_atividades():
    """Autocomplete para busca de atividades com regra de cascata"""
    termo = request.args.get('q', '').lower()
    setor_id_req = request.args.get('setor_id', type=int)

    if not termo or len(termo) < 3:
        return jsonify([])
        
    query = AtividadePadrao.query.filter(AtividadePadrao.titulo.ilike(f'%{termo}%'))

    # Regra de Cascata: Admin/Gestor pesquisa global ou por setor específico; demais no próprio setor
    if current_user.is_admin or current_user.is_gestor:
        if setor_id_req:
            query = query.filter(AtividadePadrao.setor_id == setor_id_req)
    else:
        query = query.filter(AtividadePadrao.setor_id == current_user.setor_id)

    atividades = query.limit(10).all()
    
    return jsonify([{
        'id': a.id, 
        'titulo': a.titulo, 
        'meta': f"{a.tempo_estimado_valor} {a.tempo_estimado_unidade}"
    } for a in atividades])