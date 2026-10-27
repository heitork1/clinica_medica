from datetime import date, timedelta

from dados.relatorio import RelatorioDAO
from negocio import ErroNegocio
from negocio.validacao import converter_data


def primeiro_dia_do_mes(dia):
    return dia.replace(day=1)


def periodos_rapidos(hoje=None):
    """Atalhos da tela: (rótulo, início, fim)."""
    hoje = hoje or date.today()
    inicio_mes = primeiro_dia_do_mes(hoje)
    fim_mes_passado = inicio_mes - timedelta(days=1)
    return [
        ("Este mês", inicio_mes, hoje),
        ("Mês passado", primeiro_dia_do_mes(fim_mes_passado), fim_mes_passado),
        ("Últimos 30 dias", hoje - timedelta(days=29), hoje),
    ]


class ServicoRelatorios:

    def __init__(self):
        self.relatorio_dao = RelatorioDAO()

    def ler_periodo(self, texto_inicio, texto_fim):
        """Período da URL; sem datas, o mês atual até hoje. Lança ErroNegocio se for inválido."""
        hoje = date.today()
        try:
            inicio = converter_data(texto_inicio) or primeiro_dia_do_mes(hoje)
            fim = converter_data(texto_fim) or hoje
        except ValueError:
            raise ErroNegocio("Data inválida no período.")
        if inicio > fim:
            raise ErroNegocio("A data inicial do período é depois da data final.")
        return inicio, fim

    def gerar(self, inicio, fim):
        # as consultas usam intervalo meio-aberto: até o fim do último dia
        fim_exclusivo = fim + timedelta(days=1)
        faturamento = self.relatorio_dao.faturamento(inicio, fim_exclusivo)
        faturamento["em_aberto"] = faturamento["faturado"] - faturamento["recebido"]

        consultas = self.relatorio_dao.consultas_por_medico(inicio, fim_exclusivo)
        honorarios = self.relatorio_dao.honorarios(inicio, fim_exclusivo)
        return {
            "faturamento": faturamento,
            "recebimentos": self.relatorio_dao.recebimentos(inicio, fim_exclusivo),
            "consultas_por_medico": consultas,
            "total_consultas": {
                chave: sum(linha[chave] for linha in consultas)
                for chave in ("total", "realizadas", "pendentes", "canceladas", "faltas")
            },
            "honorarios": honorarios,
            "total_honorarios": sum(linha["honorario"] for linha in honorarios),
        }
