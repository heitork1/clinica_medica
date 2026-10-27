"""DAOs das tabelas de cadastro simples: convênio, especialidade, procedimento e sala.

As quatro têm o mesmo formato (chave SERIAL e poucas colunas), então dividem a
classe CadastroDAO; cada subclasse só informa a tabela e as colunas.
Os nomes de tabela e coluna entram na SQL com psycopg2.sql.Identifier, que
coloca as aspas corretas; os valores sempre vão como parâmetros (%s).
"""
from psycopg2 import sql

from dados.conexao import conexao_banco


class CadastroDAO:
    tabela = None
    chave = None
    colunas = ()
    ordem = None

    def _campos(self):
        return sql.SQL(", ").join(sql.Identifier(c) for c in (self.chave, *self.colunas))

    def listar(self):
        consulta = sql.SQL("SELECT {campos} FROM {tabela} ORDER BY {ordem}").format(
            campos=self._campos(),
            tabela=sql.Identifier(self.tabela),
            ordem=sql.Identifier(self.ordem),
        )
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta)
            return cursor.fetchall()

    def buscar_por_id(self, id_registro):
        consulta = sql.SQL("SELECT {campos} FROM {tabela} WHERE {chave} = %s").format(
            campos=self._campos(),
            tabela=sql.Identifier(self.tabela),
            chave=sql.Identifier(self.chave),
        )
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta, (id_registro,))
            return cursor.fetchone()

    def inserir(self, dados):
        consulta = sql.SQL("INSERT INTO {tabela} ({colunas}) VALUES ({valores}) RETURNING {chave}").format(
            tabela=sql.Identifier(self.tabela),
            colunas=sql.SQL(", ").join(sql.Identifier(c) for c in self.colunas),
            valores=sql.SQL(", ").join(sql.Placeholder() for _ in self.colunas),
            chave=sql.Identifier(self.chave),
        )
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta, [dados[c] for c in self.colunas])
            return cursor.fetchone()[self.chave]

    def atualizar(self, id_registro, dados):
        consulta = sql.SQL("UPDATE {tabela} SET {atribuicoes} WHERE {chave} = %s").format(
            tabela=sql.Identifier(self.tabela),
            atribuicoes=sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(c)) for c in self.colunas
            ),
            chave=sql.Identifier(self.chave),
        )
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta, [dados[c] for c in self.colunas] + [id_registro])

    def excluir(self, id_registro):
        consulta = sql.SQL("DELETE FROM {tabela} WHERE {chave} = %s").format(
            tabela=sql.Identifier(self.tabela),
            chave=sql.Identifier(self.chave),
        )
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta, (id_registro,))
            return cursor.rowcount > 0

    def existe(self, coluna, valor, ignorar_id=None):
        """Há outro registro com o mesmo valor na coluna (sem diferenciar maiúsculas)?"""
        consulta = sql.SQL(
            "SELECT 1 FROM {tabela} WHERE lower({coluna}) = lower(%s) AND {chave} IS DISTINCT FROM %s"
        ).format(
            tabela=sql.Identifier(self.tabela),
            coluna=sql.Identifier(coluna),
            chave=sql.Identifier(self.chave),
        )
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(consulta, (valor, ignorar_id))
            return cursor.fetchone() is not None


class ConvenioDAO(CadastroDAO):
    tabela = "convenio"
    chave = "id_convenio"
    colunas = ("nome",)
    ordem = "nome"


class EspecialidadeDAO(CadastroDAO):
    tabela = "especialidade"
    chave = "id_especialidade"
    colunas = ("nome_especialidade",)
    ordem = "nome_especialidade"


class ProcedimentoDAO(CadastroDAO):
    tabela = "procedimento"
    chave = "id_procedimento"
    colunas = ("descricao", "valor")
    ordem = "descricao"


class SalaDAO(CadastroDAO):
    tabela = "sala"
    chave = "id_sala"
    colunas = ("descricao",)
    ordem = "id_sala"
