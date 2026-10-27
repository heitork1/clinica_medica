from dados.conexao import conexao_banco

# total já quitado de uma conta: parte do paciente (valor_pago) + parte do convênio
# (item 4 da seção 5.2 do plano: valor_pago é a parte do paciente)
SOMA_PAGA = "COALESCE(sum(COALESCE(pg.valor_pago, 0) + COALESCE(pg.valor_convenio, 0)), 0)"


class FinanceiroDAO:

    def buscar_conta(self, id_conta):
        """Conta com os totais pagos pelo paciente e pelo convênio e o saldo."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT ct.id_conta, ct.valor_consulta, ct.valor_procedimento,
                       COALESCE(ct.valor_total, 0) AS valor_total,
                       COALESCE(sum(pg.valor_pago), 0) AS pago_paciente,
                       COALESCE(sum(pg.valor_convenio), 0) AS pago_convenio,
                       COALESCE(ct.valor_total, 0) - {SOMA_PAGA} AS saldo,
                       count(pg.id_pagamento) AS quantidade_pagamentos
                  FROM conta ct
                  LEFT JOIN pagamento pg ON pg.id_conta = ct.id_conta
                 WHERE ct.id_conta = %s
                 GROUP BY ct.id_conta
                """,
                (id_conta,),
            )
            return cursor.fetchone()

    def listar_pagamentos(self, id_conta):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_pagamento, data_pagamento, valor_pago, forma_pagamento, possui_convenio, valor_convenio,
                       COALESCE(valor_pago, 0) + COALESCE(valor_convenio, 0) AS total
                  FROM pagamento
                 WHERE id_conta = %s
                 ORDER BY data_pagamento, id_pagamento
                """,
                (id_conta,),
            )
            return cursor.fetchall()

    def tem_pagamento(self, id_conta):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pagamento WHERE id_conta = %s LIMIT 1", (id_conta,))
            return cursor.fetchone() is not None

    def inserir_pagamento(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pagamento (data_pagamento, valor_pago, forma_pagamento, possui_convenio, valor_convenio, id_conta)
                VALUES (%(data_pagamento)s, %(valor_pago)s, %(forma_pagamento)s, %(possui_convenio)s,
                        %(valor_convenio)s, %(id_conta)s)
                RETURNING id_pagamento
                """,
                dados,
            )
            return cursor.fetchone()["id_pagamento"]

    def excluir_pagamento(self, id_pagamento, id_conta):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("DELETE FROM pagamento WHERE id_pagamento = %s AND id_conta = %s", (id_pagamento, id_conta))
            return cursor.rowcount > 0

    def contas_em_aberto(self, limite=10):
        """Consultas realizadas cuja conta ainda tem saldo, das mais antigas para as mais novas."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT c.id_consulta, c.data_hora_marcado, p.nome AS nome_paciente,
                       COALESCE(ct.valor_total, 0) - {SOMA_PAGA} AS saldo
                  FROM consulta c
                  JOIN paciente p ON p.id_paciente = c.id_paciente
                  JOIN conta ct ON ct.id_conta = c.id_conta
                  LEFT JOIN pagamento pg ON pg.id_conta = ct.id_conta
                 WHERE c.status = 'REALIZADA'
                 GROUP BY c.id_consulta, p.nome, ct.id_conta
                HAVING COALESCE(ct.valor_total, 0) - {SOMA_PAGA} > 0
                 ORDER BY c.data_hora_marcado
                 LIMIT %s
                """,
                (limite,),
            )
            return cursor.fetchall()
