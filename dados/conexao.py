from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from config import Config


def obter_conexao():
    # RealDictCursor faz cada linha voltar como dicionário: {"nome": ..., "cpf": ...}
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )


@contextmanager
def conexao_banco():
    """Abre uma conexão e a fecha no fim do bloco.

    Tudo o que for executado dentro do bloco é uma única transação:
    commit se terminar sem erro, rollback se alguma exceção acontecer.

        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT * FROM paciente WHERE id_paciente = %s", (id_paciente,))
            paciente = cursor.fetchone()
    """
    conexao = obter_conexao()
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def testar_conexao():
    """Devolve a versão do PostgreSQL. Lança exceção se não conseguir conectar."""
    with conexao_banco() as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT version() AS versao")
        return cursor.fetchone()["versao"]
