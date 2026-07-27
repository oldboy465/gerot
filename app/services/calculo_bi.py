class CalculoBI:
    """
    Serviço de Inteligência de Negócios (Business Intelligence).
    Centraliza todas as regras matemáticas de produtividade e conversão de tempo.
    """

    META_EFICIENCIA_PADRAO = 100.0

    @staticmethod
    def calcular_eficiencia(tempo_meta_minutos, tempo_realizado_minutos):
        if not tempo_realizado_minutos or tempo_realizado_minutos <= 0:
            return 0.0

        if not tempo_meta_minutos or tempo_meta_minutos <= 0:
            return 100.0

        eficiencia = (tempo_meta_minutos / tempo_realizado_minutos) * 100
        return round(eficiencia, 2)

    @staticmethod
    def classificar_performance(eficiencia):
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
        if not minutos:
            return "0m"

        horas = minutos // 60
        restante_minutos = minutos % 60

        if horas > 0:
            return f"{CalculoBI.formatar_numero_br(horas, 0)}h {restante_minutos}m"
        else:
            return f"{restante_minutos}m"

    @staticmethod
    def verificar_prazo(data_realizada, data_limite):
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
        """Formata percentuais no padrão BR (ex: 95,5%)"""
        num_str = CalculoBI.formatar_numero_br(valor, casas_decimais)
        return f"{num_str}%"