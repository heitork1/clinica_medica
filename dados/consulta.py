from datetime import datetime, time, timedelta

from psycopg2 import sql

from dados.conexao import conexao_banco

# colunas e junções comuns às consultas com nomes de paciente, médico e sala
SELECT_CONSULTA = """
    SELECT c.id_consulta, c.data_hora_marcado, c.data_hora_realizado, c.status,
           c.sintomas, c.diagnostico, c.prescricao, c.id_conta,
           c.id_paciente, p.nome AS nome_paciente, p.cpf, p.data_nasc,
           c.id_medico, m.nome_medico,
           c.id_sala, s.descricao AS sala
      FROM consulta c
      JOIN paciente p ON p.id_paciente = c.id_paciente
      LEFT JOIN medico m ON m.id_medico = c.id_medico
      LEFT JOIN sala s ON s.id_sala = c.id_sala
"""


class ConsultaDAO:

    def listar_do_dia(self, dia, id_medico=None, status=None):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                SELECT_CONSULTA + """
                 WHERE c.data_hora_marcado >= %(inicio)s AND c.data_hora_marcado < %(fim)s
                   AND (%(id_medico)s IS NULL OR c.id_medico = %(id_medico)s)
                   AND (%(status)s IS NULL OR c.status = %(status)s)
                 ORDER BY c.data_hora_marcado, m.nome_medico
                """,
                {
                    "inicio": datetime.combine(dia, time.min),
                    "fim": datetime.combine(dia, time.min) + timedelta(days=1),
                    "id_medico": id_medico,
                    "status": status,
                },
            )
            return cursor.fetchall()

    def buscar_por_id(self, id_consulta):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(SELECT_CONSULTA + " WHERE c.id_consulta = %s", (id_consulta,))
            return cursor.fetchone()

    def horarios_marcados(self, id_medico, dia):
        """Início das consultas não canceladas do médico no dia."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT data_hora_marcado FROM consulta
                 WHERE id_medico = %s AND status IS DISTINCT FROM 'CANCELADA'
                   AND data_hora_marcado >= %s AND data_hora_marcado < %s
                """,
                (id_medico, datetime.combine(dia, time.min), datetime.combine(dia, time.min) + timedelta(days=1)),
            )
            return [linha["data_hora_marcado"] for linha in cursor.fetchall()]

    def existe_conflito(self, coluna, valor, data_hora, duracao, ignorar_id=None):
        """Há consulta não cancelada com o mesmo médico, sala ou paciente (coluna) que se
        sobreponha ao intervalo [data_hora, data_hora + duracao)?"""
        consulta = sql.SQL(
            """
            SELECT 1 FROM consulta
             WHERE {coluna} = %(valor)s
               AND status IS DISTINCT FROM 'CANCELADA'
               AND data_hora_marcado > %(inicio)s AND data_hora_marcado < %(fim)s
               AND id_consulta IS DISTINCT FROM %(ignorar_id)s
             LIMIT 1
            """
        ).format(coluna=sql.Identifier(coluna))
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta, {
                "valor": valor,
                "inicio": data_hora - duracao,
                "fim": data_hora + duracao,
                "ignorar_id": ignorar_id,
            })
            return cursor.fetchone() is not None

    def inserir(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala)
                VALUES (%(data_hora_marcado)s, 'AGENDADA', %(id_paciente)s, %(id_medico)s, %(id_sala)s)
                RETURNING id_consulta
                """,
                dados,
            )
            return cursor.fetchone()["id_consulta"]

    def atualizar_status(self, id_consulta, status):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("UPDATE consulta SET status = %s WHERE id_consulta = %s", (status, id_consulta))

    def procedimentos(self, id_consulta):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT cp.id_procedimento, p.descricao, cp.quantidade, cp.valor_unitario,
                       cp.quantidade * cp.valor_unitario AS subtotal
                  FROM consulta_procedimento cp
                  JOIN procedimento p ON p.id_procedimento = cp.id_procedimento
                 WHERE cp.id_consulta = %s
                 ORDER BY p.descricao
                """,
                (id_consulta,),
            )
            return cursor.fetchall()

    def buscar_conta(self, id_conta):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT * FROM conta WHERE id_conta = %s", (id_conta,))
            return cursor.fetchone()

    def registrar_atendimento(self, id_consulta, atendimento, procedimentos, valor_consulta):
        """Grava o atendimento, os procedimentos e a conta em uma única transação.

        procedimentos: lista de {"id_procedimento", "quantidade"}; o valor unitário
        vem do cadastro do procedimento.
        Se um gatilho do banco já tiver criado a conta ao mudar o status para
        REALIZADA, a conta existente é só atualizada.
        Devolve a conta (com valor_total).
        """
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                UPDATE consulta
                   SET data_hora_realizado = %(data_hora_realizado)s, sintomas = %(sintomas)s,
                       diagnostico = %(diagnostico)s, prescricao = %(prescricao)s, status = 'REALIZADA'
                 WHERE id_consulta = %(id_consulta)s
                """,
                {**atendimento, "id_consulta": id_consulta},
            )

            cursor.execute("DELETE FROM consulta_procedimento WHERE id_consulta = %s", (id_consulta,))
            for item in procedimentos:
                cursor.execute(
                    """
                    INSERT INTO consulta_procedimento (id_consulta, id_procedimento, quantidade, valor_unitario)
                    SELECT %s, id_procedimento, %s, valor FROM procedimento WHERE id_procedimento = %s
                    """,
                    (id_consulta, item["quantidade"], item["id_procedimento"]),
                )

            cursor.execute(
                """
                SELECT COALESCE(sum(quantidade * valor_unitario), 0) AS total
                  FROM consulta_procedimento WHERE id_consulta = %s
                """,
                (id_consulta,),
            )
            valor_procedimentos = cursor.fetchone()["total"]

            cursor.execute("SELECT id_conta FROM consulta WHERE id_consulta = %s", (id_consulta,))
            id_conta = cursor.fetchone()["id_conta"]
            if id_conta:
                cursor.execute(
                    "UPDATE conta SET valor_procedimento = %s, valor_consulta = %s WHERE id_conta = %s",
                    (valor_procedimentos, valor_consulta, id_conta),
                )
            else:
                cursor.execute(
                    "INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (%s, %s) RETURNING id_conta",
                    (valor_procedimentos, valor_consulta),
                )
                id_conta = cursor.fetchone()["id_conta"]
                cursor.execute("UPDATE consulta SET id_conta = %s WHERE id_consulta = %s", (id_conta, id_consulta))

            cursor.execute("SELECT * FROM conta WHERE id_conta = %s", (id_conta,))
            return cursor.fetchone()
