class CalculoBI:
    """
    Serviço de Inteligência de Negócios (Business Intelligence).
    Centraliza todas as regras matemáticas de produtividade e conversão de tempo.
    """

    @staticmethod
    def calcular_eficiencia(tempo_meta_minutos, tempo_realizado_minutos):
        """
        Calcula a eficiência percentual.
        Fórmula: (Tempo Estimado / Tempo Realizado) * 100
        
        Exemplos:
        - Meta 60m / Real 30m = 200% (Excelente, fez em metade do tempo)
        - Meta 60m / Real 60m = 100% (Na meta)
        - Meta 60m / Real 120m = 50% (Ruim, demorou o dobro)
        """
        if not tempo_realizado_minutos or tempo_realizado_minutos <= 0:
            return 0.0 # Evita divisão por zero
            
        if not tempo_meta_minutos or tempo_meta_minutos <= 0:
            # Se não tem meta definida (tarefa não rotineira), eficiência é neutra (100%)
            return 100.0
            
        eficiencia = (tempo_meta_minutos / tempo_realizado_minutos) * 100
        return round(eficiencia, 2)

    @staticmethod
    def classificar_performance(eficiencia):
        """Retorna uma classe CSS e um rótulo textual baseado na eficiência."""
        if eficiencia >= 150:
            return 'success', 'Alta Performance' # Superou muito a meta
        elif 90 <= eficiencia < 150:
            return 'primary', 'Dentro da Meta'   # Zona ideal
        elif 70 <= eficiencia < 90:
            return 'warning', 'Atenção'          # Pequeno desvio
        else:
            return 'danger', 'Crítico'           # Desvio grave (Gargalo)

    @staticmethod
    def formatar_minutos(minutos):
        """
        Converte minutos brutos em string legível para humanos.
        Ex: 150 min -> "2h 30m"
        """
        if not minutos:
            return "0m"
            
        horas = minutos // 60
        restante_minutos = minutos % 60
        
        if horas > 0:
            return f"{horas}h {restante_minutos}m"
        else:
            return f"{restante_minutos}m"

    @staticmethod
    def verificar_prazo(data_realizada, data_limite):
        """Verifica se a entrega ocorreu dentro do prazo estipulado (SLA de Data)."""
        if not data_limite:
            return True
        return data_realizada <= data_limite