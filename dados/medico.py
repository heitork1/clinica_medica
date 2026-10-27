from dados.conexao import conexao_banco


class MedicoDAO:

    def listar(self, id_especialidade=None):
        """Médicos com especialidades, dias de atendimento e primeiro telefone.

        id_especialidade: se informado, só os médicos que têm essa especialidade.
        """
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.id_medico, m.nome_medico, m.crm, m.percentual_honorario,
                       (SELECT string_agg(e.nome_especialidade, ', ' ORDER BY e.nome_especialidade)
                          FROM medico_especialidade me
                          JOIN especialidade e ON e.id_especialidade = me.id_especialidade
                         WHERE me.id_medico = m.id_medico) AS especialidades,
                       (SELECT array_agg(DISTINCT h.dia_semana)
                          FROM horario_medico hm JOIN horario h ON h.id_horario = hm.id_horario
                         WHERE hm.id_medico = m.id_medico) AS dias,
                       (SELECT t.numero_telefone FROM telefone_medico t
                         WHERE t.id_medico = m.id_medico ORDER BY t.id_telefone LIMIT 1) AS telefone
                  FROM medico m
                 WHERE %(id_especialidade)s IS NULL
                    OR EXISTS (SELECT 1 FROM medico_especialidade me
                                WHERE me.id_medico = m.id_medico AND me.id_especialidade = %(id_especialidade)s)
                 ORDER BY m.nome_medico
                """,
                {"id_especialidade": id_especialidade},
            )
            return cursor.fetchall()

    def buscar_por_id(self, id_medico):
        """Médico com telefones, ids das especialidades e horários de atendimento."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id_medico, nome_medico, crm, percentual_honorario FROM medico WHERE id_medico = %s",
                (id_medico,),
            )
            medico = cursor.fetchone()
            if not medico:
                return None

            cursor.execute(
                "SELECT numero_telefone FROM telefone_medico WHERE id_medico = %s ORDER BY id_telefone",
                (id_medico,),
            )
            medico["telefones"] = [linha["numero_telefone"] for linha in cursor.fetchall()]

            cursor.execute(
                "SELECT id_especialidade FROM medico_especialidade WHERE id_medico = %s",
                (id_medico,),
            )
            medico["especialidades"] = [linha["id_especialidade"] for linha in cursor.fetchall()]

            cursor.execute(
                """
                SELECT h.dia_semana, h.hora_inicio, h.hora_fim
                  FROM horario_medico hm JOIN horario h ON h.id_horario = hm.id_horario
                 WHERE hm.id_medico = %s
                 ORDER BY h.hora_inicio
                """,
                (id_medico,),
            )
            medico["horarios"] = cursor.fetchall()
            return medico

    def listar_para_selecao(self):
        """Médicos com os ids das especialidades, para listas de escolha."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.id_medico, m.nome_medico, m.crm,
                       COALESCE((SELECT array_agg(me.id_especialidade) FROM medico_especialidade me
                                  WHERE me.id_medico = m.id_medico), '{}') AS especialidades
                  FROM medico m
                 ORDER BY m.nome_medico
                """
            )
            return cursor.fetchall()

    def horarios_do_dia(self, id_medico, dia_semana):
        """Faixas de atendimento do médico em um dia da semana ('SEGUNDA' ...)."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT h.hora_inicio, h.hora_fim
                  FROM horario_medico hm JOIN horario h ON h.id_horario = hm.id_horario
                 WHERE hm.id_medico = %s AND h.dia_semana = %s
                 ORDER BY h.hora_inicio
                """,
                (id_medico, dia_semana),
            )
            return cursor.fetchall()

    def listar_sem_usuario(self, id_medico_atual=None):
        """Médicos ainda sem usuário no sistema (mais o atual, na edição de um usuário)."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.id_medico, m.nome_medico, m.crm
                  FROM medico m
                 WHERE m.id_medico = %s
                    OR NOT EXISTS (SELECT 1 FROM usuario u WHERE u.id_medico = m.id_medico)
                 ORDER BY m.nome_medico
                """,
                (id_medico_atual,),
            )
            return cursor.fetchall()

    def inserir(self, medico, telefones, especialidades, horarios):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO medico (nome_medico, crm, percentual_honorario)
                VALUES (%(nome_medico)s, %(crm)s, %(percentual_honorario)s)
                RETURNING id_medico
                """,
                medico,
            )
            id_medico = cursor.fetchone()["id_medico"]
            self._gravar_listas(cursor, id_medico, telefones, especialidades, horarios)
            return id_medico

    def atualizar(self, id_medico, medico, telefones, especialidades, horarios):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                UPDATE medico
                   SET nome_medico = %(nome_medico)s, crm = %(crm)s, percentual_honorario = %(percentual_honorario)s
                 WHERE id_medico = %(id_medico)s
                """,
                {**medico, "id_medico": id_medico},
            )
            self._apagar_listas(cursor, id_medico)
            self._gravar_listas(cursor, id_medico, telefones, especialidades, horarios)

    def excluir(self, id_medico):
        """Exclui o médico com suas listas. Falha (FK) se houver consultas ou usuário vinculado."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            self._apagar_listas(cursor, id_medico)
            cursor.execute("DELETE FROM medico WHERE id_medico = %s", (id_medico,))
            return cursor.rowcount > 0

    def _apagar_listas(self, cursor, id_medico):
        cursor.execute("DELETE FROM telefone_medico WHERE id_medico = %s", (id_medico,))
        cursor.execute("DELETE FROM medico_especialidade WHERE id_medico = %s", (id_medico,))
        cursor.execute("DELETE FROM horario_medico WHERE id_medico = %s", (id_medico,))
        # faixas de horário que não pertencem a mais nenhum médico
        cursor.execute(
            "DELETE FROM horario h WHERE NOT EXISTS (SELECT 1 FROM horario_medico hm WHERE hm.id_horario = h.id_horario)"
        )

    def _gravar_listas(self, cursor, id_medico, telefones, especialidades, horarios):
        for numero in telefones:
            cursor.execute(
                "INSERT INTO telefone_medico (numero_telefone, id_medico) VALUES (%s, %s)",
                (numero, id_medico),
            )
        for id_especialidade in especialidades:
            cursor.execute(
                "INSERT INTO medico_especialidade (id_medico, id_especialidade) VALUES (%s, %s)",
                (id_medico, id_especialidade),
            )
        for horario in horarios:
            # a mesma faixa (dia, início, fim) é compartilhada entre médicos na tabela horario
            cursor.execute(
                """
                SELECT id_horario FROM horario
                 WHERE dia_semana = %(dia_semana)s AND hora_inicio = %(hora_inicio)s AND hora_fim = %(hora_fim)s
                 LIMIT 1
                """,
                horario,
            )
            linha = cursor.fetchone()
            if linha:
                id_horario = linha["id_horario"]
            else:
                cursor.execute(
                    """
                    INSERT INTO horario (dia_semana, hora_inicio, hora_fim)
                    VALUES (%(dia_semana)s, %(hora_inicio)s, %(hora_fim)s)
                    RETURNING id_horario
                    """,
                    horario,
                )
                id_horario = cursor.fetchone()["id_horario"]
            cursor.execute(
                "INSERT INTO horario_medico (id_medico, id_horario) VALUES (%s, %s)",
                (id_medico, id_horario),
            )
