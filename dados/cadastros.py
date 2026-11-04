"""Camada de Dados dos cadastros simples: Convênio, Especialidade, Procedimento e Sala.

Cada classe fala direto com UMA tabela, usando SQL puro. Todas têm os mesmos
cinco métodos:
  listar()        -> SELECT de todos os registros
  buscar_por_id() -> SELECT de um registro
  inserir()       -> INSERT
  atualizar()     -> UPDATE
  excluir()       -> DELETE
  existe()        -> já tem outro registro com esse nome? (evita duplicados)

`chave` é o nome da coluna de ID, usado pela tela para montar os links.
Os valores vão sempre como parâmetros (%s), nunca colados no texto do SQL.
"""
from dados.conexao import conexao_banco


class ConvenioDAO:
    chave = "id_convenio"

    def listar(self):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_convenio, nome FROM convenio ORDER BY nome")
            return cursor.fetchall()

    def buscar_por_id(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_convenio, nome FROM convenio WHERE id_convenio = %s", (id_registro,))
            return cursor.fetchone()

    def inserir(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("INSERT INTO convenio (nome) VALUES (%(nome)s) RETURNING id_convenio", dados)
            return cursor.fetchone()["id_convenio"]

    def atualizar(self, id_registro, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE convenio SET nome = %(nome)s WHERE id_convenio = %(id)s",
                {**dados, "id": id_registro},
            )

    def excluir(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("DELETE FROM convenio WHERE id_convenio = %s", (id_registro,))

    def existe(self, nome, ignorar_id=None):
        """ignorar_id: na edição, o próprio registro não conta como duplicado."""
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM convenio WHERE lower(nome) = lower(%s) AND id_convenio IS DISTINCT FROM %s",
                (nome, ignorar_id),
            )
            return cursor.fetchone() is not None


class EspecialidadeDAO:
    chave = "id_especialidade"

    def listar(self):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_especialidade, nome_especialidade FROM especialidade ORDER BY nome_especialidade")
            return cursor.fetchall()

    def buscar_por_id(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id_especialidade, nome_especialidade FROM especialidade WHERE id_especialidade = %s",
                (id_registro,),
            )
            return cursor.fetchone()

    def inserir(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO especialidade (nome_especialidade) VALUES (%(nome_especialidade)s) RETURNING id_especialidade",
                dados,
            )
            return cursor.fetchone()["id_especialidade"]

    def atualizar(self, id_registro, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE especialidade SET nome_especialidade = %(nome_especialidade)s WHERE id_especialidade = %(id)s",
                {**dados, "id": id_registro},
            )

    def excluir(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("DELETE FROM especialidade WHERE id_especialidade = %s", (id_registro,))

    def existe(self, nome, ignorar_id=None):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM especialidade WHERE lower(nome_especialidade) = lower(%s) AND id_especialidade IS DISTINCT FROM %s",
                (nome, ignorar_id),
            )
            return cursor.fetchone() is not None


class ProcedimentoDAO:
    chave = "id_procedimento"

    def listar(self):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_procedimento, descricao, valor FROM procedimento ORDER BY descricao")
            return cursor.fetchall()

    def buscar_por_id(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id_procedimento, descricao, valor FROM procedimento WHERE id_procedimento = %s",
                (id_registro,),
            )
            return cursor.fetchone()

    def inserir(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO procedimento (descricao, valor) VALUES (%(descricao)s, %(valor)s) RETURNING id_procedimento",
                dados,
            )
            return cursor.fetchone()["id_procedimento"]

    def atualizar(self, id_registro, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE procedimento SET descricao = %(descricao)s, valor = %(valor)s WHERE id_procedimento = %(id)s",
                {**dados, "id": id_registro},
            )

    def excluir(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("DELETE FROM procedimento WHERE id_procedimento = %s", (id_registro,))

    def existe(self, descricao, ignorar_id=None):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM procedimento WHERE lower(descricao) = lower(%s) AND id_procedimento IS DISTINCT FROM %s",
                (descricao, ignorar_id),
            )
            return cursor.fetchone() is not None


class SalaDAO:
    chave = "id_sala"

    def listar(self):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_sala, descricao FROM sala ORDER BY id_sala")
            return cursor.fetchall()

    def buscar_por_id(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_sala, descricao FROM sala WHERE id_sala = %s", (id_registro,))
            return cursor.fetchone()

    def inserir(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("INSERT INTO sala (descricao) VALUES (%(descricao)s) RETURNING id_sala", dados)
            return cursor.fetchone()["id_sala"]

    def atualizar(self, id_registro, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE sala SET descricao = %(descricao)s WHERE id_sala = %(id)s",
                {**dados, "id": id_registro},
            )

    def excluir(self, id_registro):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("DELETE FROM sala WHERE id_sala = %s", (id_registro,))

    def existe(self, descricao, ignorar_id=None):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM sala WHERE lower(descricao) = lower(%s) AND id_sala IS DISTINCT FROM %s",
                (descricao, ignorar_id),
            )
            return cursor.fetchone() is not None
