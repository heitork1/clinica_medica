"""Consultas de resumo para a tela de relatórios. Todas recebem um período [inicio, fim)."""
from dados.conexao import conexao_banco


class RelatorioDAO:

    def consultas_por_medico(self, inicio, fim):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.nome_medico,
                       count(c.id_consulta) AS total,
                       count(c.id_consulta) FILTER (WHERE c.status = 'REALIZADA') AS realizadas,
                       count(c.id_consulta) FILTER (WHERE c.status IN ('AGENDADA', 'CONFIRMADA')) AS pendentes,
                       count(c.id_consulta) FILTER (WHERE c.status = 'CANCELADA') AS canceladas,
                       count(c.id_consulta) FILTER (WHERE c.status = 'FALTOU') AS faltas
                  FROM medico m
                  LEFT JOIN consulta c ON c.id_medico = m.id_medico
                                      AND c.data_hora_marcado >= %(inicio)s AND c.data_hora_marcado < %(fim)s
                 GROUP BY m.id_medico, m.nome_medico
                 ORDER BY total DESC, m.nome_medico
                """,
                {"inicio": inicio, "fim": fim},
            )
            return cursor.fetchall()

    def faturamento(self, inicio, fim):
        """Contas das consultas realizadas no período, com o que já foi recebido delas."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*) AS consultas,
                       COALESCE(sum(ct.valor_consulta), 0) AS valor_consultas,
                       COALESCE(sum(ct.valor_procedimento), 0) AS valor_procedimentos,
                       COALESCE(sum(ct.valor_total), 0) AS faturado,
                       COALESCE(sum(pagos.total), 0) AS recebido
                  FROM consulta c
                  JOIN conta ct ON ct.id_conta = c.id_conta
                  LEFT JOIN (SELECT id_conta, sum(COALESCE(valor_pago, 0) + COALESCE(valor_convenio, 0)) AS total
                               FROM pagamento GROUP BY id_conta) pagos ON pagos.id_conta = ct.id_conta
                 WHERE c.status = 'REALIZADA'
                   AND c.data_hora_marcado >= %(inicio)s AND c.data_hora_marcado < %(fim)s
                """,
                {"inicio": inicio, "fim": fim},
            )
            return cursor.fetchone()

    def recebimentos(self, inicio, fim):
        """Pagamentos com data no período, separados por forma (parte do paciente) e convênio."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(sum(valor_pago) FILTER (WHERE forma_pagamento = 'DINHEIRO'), 0) AS dinheiro,
                       COALESCE(sum(valor_pago) FILTER (WHERE forma_pagamento = 'CARTAO'), 0) AS cartao,
                       COALESCE(sum(valor_pago) FILTER (WHERE forma_pagamento = 'PIX'), 0) AS pix,
                       COALESCE(sum(valor_convenio), 0) AS convenio,
                       COALESCE(sum(COALESCE(valor_pago, 0) + COALESCE(valor_convenio, 0)), 0) AS total,
                       count(*) AS quantidade
                  FROM pagamento
                 WHERE data_pagamento >= %(inicio)s AND data_pagamento < %(fim)s
                """,
                {"inicio": inicio, "fim": fim},
            )
            return cursor.fetchone()

    def honorarios(self, inicio, fim):
        """Parte de cada médico no valor das consultas realizadas (percentual_honorario)."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.nome_medico, m.percentual_honorario,
                       count(c.id_consulta) AS consultas,
                       COALESCE(sum(ct.valor_consulta), 0) AS valor_consultas,
                       round(COALESCE(sum(ct.valor_consulta), 0) * m.percentual_honorario / 100, 2) AS honorario
                  FROM medico m
                  LEFT JOIN consulta c ON c.id_medico = m.id_medico AND c.status = 'REALIZADA'
                                      AND c.data_hora_marcado >= %(inicio)s AND c.data_hora_marcado < %(fim)s
                  LEFT JOIN conta ct ON ct.id_conta = c.id_conta
                 GROUP BY m.id_medico, m.nome_medico, m.percentual_honorario
                 ORDER BY honorario DESC, m.nome_medico
                """,
                {"inicio": inicio, "fim": fim},
            )
            return cursor.fetchall()
