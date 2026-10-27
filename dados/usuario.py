from dados.conexao import conexao_banco

# colunas devolvidas nas listagens; senha_hash só sai nas consultas de login/senha
COLUNAS = "id_usuario, nome, email, perfil, ativo, id_medico"


class UsuarioDAO:

    def listar(self):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(f"SELECT {COLUNAS} FROM usuario ORDER BY ativo DESC, nome")
            return cursor.fetchall()

    def buscar_por_id(self, id_usuario):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(f"SELECT {COLUNAS} FROM usuario WHERE id_usuario = %s", (id_usuario,))
            return cursor.fetchone()

    def buscar_para_login(self, email):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                f"SELECT {COLUNAS}, senha_hash FROM usuario WHERE lower(email) = lower(%s)",
                (email,),
            )
            return cursor.fetchone()

    def buscar_senha_hash(self, id_usuario):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT senha_hash FROM usuario WHERE id_usuario = %s", (id_usuario,))
            linha = cursor.fetchone()
            return linha["senha_hash"] if linha else None

    def inserir(self, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usuario (nome, email, senha_hash, perfil, id_medico)
                VALUES (%(nome)s, %(email)s, %(senha_hash)s, %(perfil)s, %(id_medico)s)
                RETURNING id_usuario
                """,
                dados,
            )
            return cursor.fetchone()["id_usuario"]

    def atualizar(self, id_usuario, dados):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                UPDATE usuario
                   SET nome = %(nome)s, email = %(email)s, perfil = %(perfil)s, id_medico = %(id_medico)s
                 WHERE id_usuario = %(id_usuario)s
                """,
                {**dados, "id_usuario": id_usuario},
            )

    def alterar_senha(self, id_usuario, senha_hash):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE usuario SET senha_hash = %s WHERE id_usuario = %s",
                (senha_hash, id_usuario),
            )

    def definir_ativo(self, id_usuario, ativo):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE usuario SET ativo = %s WHERE id_usuario = %s",
                (ativo, id_usuario),
            )
