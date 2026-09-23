from datetime import datetime, time, timedelta

class CalculoBI:
    """
    Serviço de Inteligência de Negócios (Business Intelligence).
    Centraliza as regras matemáticas de produtividade e cálculo de tempo útil.
    
    Regra de Horas e Dias Úteis:
      - Segunda a sexta-feira.
      - Janela de atendimento/operação: 08:00 às 18:00 (janela de 10 horas).
      - Jornada útil líquida computada por dia de trabalho: 8 horas úteis (480 minutos).
      - Finais de semana (sábado e domingo) e horários fora da grade não contam como tempo útil.
    """

    META_EFICIENCIA_PADRAO = 100.0
    HORA_INICIO_UTIL = time(8, 0)
    HORA_FIM_UTIL = time(18, 0)
    MAX_MINUTOS_UTEIS_DIA = 480  # 8 horas líquidas diárias

    @staticmethod
    def calcular_minutos_uteis_intervalo(dt_inicio, dt_fim):
        """
        Calcula os minutos úteis transcorridos entre dt_inicio e dt_fim.
        Considera apenas de segunda a sexta, na faixa das 08:00 às 18:00,
        limitando o cômputo a no máximo 480 minutos (8h líquidas) por dia útil.
        """
        if not dt_inicio or not dt_fim or dt_fim <= dt_inicio:
            return 0

        total_minutos_uteis = 0
        dia_corrente = dt_inicio.date()
        data_fim_limite = dt_fim.date()

        while dia_corrente <= data_fim_limite:
            # 0 = Segunda, 4 = Sexta, 5 = Sábado, 6 = Domingo
            if dia_corrente.weekday() < 5:
                janela_inicio_dia = datetime.combine(dia_corrente, CalculoBI.HORA_INICIO_UTIL)
                janela_fim_dia = datetime.combine(dia_corrente, CalculoBI.HORA_FIM_UTIL)

                # Ponto de início e fim efetivos dentro da janela útil do dia
                inicio_efetivo = max(dt_inicio, janela_inicio_dia)
                fim_efetivo = min(dt_fim, janela_fim_dia)

                if fim_efetivo > inicio_efetivo:
                    minutos_brutos_dia = int((fim_efetivo - inicio_efetivo).total_seconds() / 60)
                    # Aplica a trava da jornada diária líquida de 8 horas (480 minutos)
                    minutos_liquidos_dia = min(minutos_brutos_dia, CalculoBI.MAX_MINUTOS_UTEIS_DIA)
                    total_minutos_uteis += minutos_liquidos_dia

            dia_corrente += timedelta(days=1)

        return total_minutos_uteis

    @staticmethod
    def calcular_eficiencia(tempo_meta_minutos, tempo_realizado_minutos):
        """
        Calcula a eficiência percentual: (Tempo Meta / Tempo Realizado Útil) * 100.
        Se realizado for 0 ou nulo, retorna 0.0.
        Se a meta for 0, considera 100% de eficiência.
        """
        if not tempo_realizado_minutos or tempo_realizado_minutos <= 0:
            return 0.0

        if not tempo_meta_minutos or tempo_meta_minutos <= 0:
            return 100.0

        eficiencia = (float(tempo_meta_minutos) / float(tempo_realizado_minutos)) * 100.0
        return round(eficiencia, 2)

    @staticmethod
    def classificar_performance(eficiencia):
        """Classifica a performance com badges Bootstrap/Tailwind."""
        if eficiencia is None:
            return 'secondary', 'Sem Dados'
        if eficiencia >= 150:
            return 'success', 'Alta Performance'
        elif 90 <= eficiencia < 150:
            return 'primary', 'Dentro da Meta'
        elif 70 <= eficiencia < 90:
            return 'warning', 'Atenção'
        else:
            return 'danger', 'Crítico'

    @staticmethod
    def formatar_minutos(minutos):
        """Converte minutos inteiros para formato legível de horas e minutos (ex: 8h 30m)."""
        if not minutos or minutos <= 0:
            return "0m"

        horas = minutos // 60
        restante_minutos = minutos % 60

        if horas > 0:
            return f"{CalculoBI.formatar_numero_br(horas, 0)}h {restante_minutos}m"
        else:
            return f"{restante_minutos}m"

    @staticmethod
    def verificar_prazo(data_realizada, data_limite):
        """Verifica cumprimento de prazos ou SLA."""
        if not data_limite:
            return True
        return data_realizada <= data_limite

    @staticmethod
    def formatar_numero_br(valor, casas_decimais=2):
        """
        Formata números para o padrão brasileiro:
        Separador de milhar = ponto (.)
        Separador decimal = vírgula (,)
        """
        if valor is None:
            valor = 0.0
        try:
            val_float = float(valor)
            if casas_decimais == 0:
                return f"{int(round(val_float)):,}".replace(',', '.')
            parts = f"{val_float:.{casas_decimais}f}".split('.')
            int_part = f"{int(parts[0]):,}".replace(',', '.')
            dec_part = parts[1]
            return f"{int_part},{dec_part}"
        except Exception:
            return str(valor)

    @staticmethod
    def formatar_porcentagem_br(valor, casas_decimais=1):
        """Formata percentuais no padrão brasileiro (ex: 105,4%)."""
        num_str = CalculoBI.formatar_numero_br(valor, casas_decimais)
        return f"{num_str}%"