from dados.conexao import conexao_banco

# A coluna se chama "e-mail" no script atual (item 2 da seção 5.2 do plano).
# Se for renomeada para email, basta trocar esta constante.
COLUNA_EMAIL = '"e-mail"'

# Comparação sem acentos e sem diferenciar maiúsculas, sem depender da extensão unaccent
COM_ACENTO = "áàãâäéèêëíìîïóòõôöúùûüçñ"
SEM_ACENTO = "aaaaaeeeeiiiiooooouuuucn"


def sem_acento(texto):
    return (texto or "").lower().translate(str.maketrans(COM_ACENTO, SEM_ACENTO))


class PacienteDAO:

    def listar(self, busca="", digitos_cpf="", limite=20, deslocamento=0):
        """Pacientes que combinam com a busca (nome ou CPF), com o total para a paginação."""
        filtro = """
            WHERE %(busca)s = ''
               OR translate(lower(p.nome), %(com_acento)s, %(sem_acento)s) LIKE %(padrao_nome)s
               OR (%(digitos)s <> '' AND regexp_replace(p.cpf, '[^0-9]', '', 'g') LIKE %(padrao_cpf)s)
        """
        parametros = {
            "busca": busca,
            "com_acento": COM_ACENTO,
            "sem_acento": SEM_ACENTO,
            "padrao_nome": f"%{sem_acento(busca)}%",
            "digitos": digitos_cpf,
            "padrao_cpf": f"%{digitos_cpf}%",
            "limite": limite,
            "deslocamento": deslocamento,
        }
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(f"SELECT count(*) AS total FROM paciente p {filtro}", parametros)
            total = cursor.fetchone()["total"]
            cursor.execute(
                f"""
                SELECT p.id_paciente, p.nome, p.cpf, p.data_nasc,
                       (SELECT t.numero_telefone FROM telefone_paciente t
                         WHERE t.id_paciente = p.id_paciente ORDER BY t.id_telefone LIMIT 1) AS telefone,
                       (SELECT string_agg(c.nome, ', ' ORDER BY c.nome)
                          FROM plano_convenio pc JOIN convenio c ON c.id_convenio = pc.id_convenio
                         WHERE pc.id_paciente = p.id_paciente) AS convenios
                  FROM paciente p
                  {filtro}
                 ORDER BY p.nome
                 LIMIT %(limite)s OFFSET %(deslocamento)s
                """,
                parametros,
            )
            return cursor.fetchall(), total

    def listar_para_selecao(self):
        """Todos os pacientes (id, nome, CPF), para listas de escolha."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_paciente, nome, cpf FROM paciente ORDER BY nome")
            return cursor.fetchall()

    def buscar_por_id(self, id_paciente):
        """Paciente com as listas de telefones e convênios."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id_paciente, nome, data_nasc, cpf, rg, sexo, endereco, {COLUNA_EMAIL} AS email
                  FROM paciente WHERE id_paciente = %s
                """,
                (id_paciente,),
            )
            paciente = cursor.fetchone()
            if not paciente:
                return None

            cursor.execute(
                "SELECT numero_telefone FROM telefone_paciente WHERE id_paciente = %s ORDER BY id_telefone",
                (id_paciente,),
            )
            paciente["telefones"] = [linha["numero_telefone"] for linha in cursor.fetchall()]

            cursor.execute(
                """
                SELECT pc.id_convenio, c.nome AS nome_convenio, pc.numero_carteirinha, pc.validade, pc.tipo_plano
                  FROM plano_convenio pc JOIN convenio c ON c.id_convenio = pc.id_convenio
                 WHERE pc.id_paciente = %s
                 ORDER BY c.nome
                """,
                (id_paciente,),
            )
            paciente["convenios"] = cursor.fetchall()
            return paciente

    def listar_consultas(self, id_paciente):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id_consulta, c.data_hora_marcado, c.data_hora_realizado, c.status,
                       c.sintomas, c.diagnostico, c.prescricao, c.id_medico,
                       m.nome_medico, s.descricao AS sala
                  FROM consulta c
                  LEFT JOIN medico m ON m.id_medico = c.id_medico
                  LEFT JOIN sala s ON s.id_sala = c.id_sala
                 WHERE c.id_paciente = %s
                 ORDER BY c.data_hora_marcado DESC NULLS LAST
                """,
                (id_paciente,),
            )
            return cursor.fetchall()

    def cpf_em_uso(self, cpf, ignorar_id=None):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM paciente WHERE cpf = %s AND id_paciente IS DISTINCT FROM %s",
                (cpf, ignorar_id),
            )
            return cursor.fetchone() is not None

    def inserir(self, paciente, telefones, convenios):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO paciente (nome, data_nasc, cpf, rg, sexo, endereco, {COLUNA_EMAIL})
                VALUES (%(nome)s, %(data_nasc)s, %(cpf)s, %(rg)s, %(sexo)s, %(endereco)s, %(email)s)
                RETURNING id_paciente
                """,
                paciente,
            )
            id_paciente = cursor.fetchone()["id_paciente"]
            self._gravar_listas(cursor, id_paciente, telefones, convenios)
            return id_paciente

    def atualizar(self, id_paciente, paciente, telefones, convenios):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE paciente
                   SET nome = %(nome)s, data_nasc = %(data_nasc)s, cpf = %(cpf)s, rg = %(rg)s,
                       sexo = %(sexo)s, endereco = %(endereco)s, {COLUNA_EMAIL} = %(email)s
                 WHERE id_paciente = %(id_paciente)s
                """,
                {**paciente, "id_paciente": id_paciente},
            )
            # telefones e convênios são regravados por inteiro, na mesma transação
            cursor.execute("DELETE FROM telefone_paciente WHERE id_paciente = %s", (id_paciente,))
            cursor.execute("DELETE FROM plano_convenio WHERE id_paciente = %s", (id_paciente,))
            self._gravar_listas(cursor, id_paciente, telefones, convenios)

    def excluir(self, id_paciente):
        """Exclui o paciente com telefones e convênios. Falha (FK) se houver consultas."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("DELETE FROM telefone_paciente WHERE id_paciente = %s", (id_paciente,))
            cursor.execute("DELETE FROM plano_convenio WHERE id_paciente = %s", (id_paciente,))
            cursor.execute("DELETE FROM paciente WHERE id_paciente = %s", (id_paciente,))
            return cursor.rowcount > 0

    def _gravar_listas(self, cursor, id_paciente, telefones, convenios):
        for numero in telefones:
            cursor.execute(
                "INSERT INTO telefone_paciente (numero_telefone, id_paciente) VALUES (%s, %s)",
                (numero, id_paciente),
            )
        for plano in convenios:
            cursor.execute(
                """
                INSERT INTO plano_convenio (id_paciente, id_convenio, numero_carteirinha, validade, tipo_plano)
                VALUES (%(id_paciente)s, %(id_convenio)s, %(numero_carteirinha)s, %(validade)s, %(tipo_plano)s)
                """,
                {**plano, "id_paciente": id_paciente},
            )
