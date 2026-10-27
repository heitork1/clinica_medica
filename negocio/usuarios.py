import psycopg2
from psycopg2 import errorcodes
from werkzeug.security import generate_password_hash

from dados.medico import MedicoDAO
from dados.usuario import UsuarioDAO
from negocio import ErroNegocio, ErroValidacao, erro_do_banco
from negocio.autenticacao import PERFIS, validar_nova_senha
from negocio.validacao import EMAIL_VALIDO


class ServicoUsuarios:

    def __init__(self):
        self.usuario_dao = UsuarioDAO()
        self.medico_dao = MedicoDAO()

    def listar(self):
        return self.usuario_dao.listar()

    def medicos_para_vinculo(self, id_medico_atual=None):
        """Opções (id, "Nome (CRM ...)") dos médicos sem usuário, mais o já vinculado (na edição)."""
        return [
            (m["id_medico"], f"{m['nome_medico']} (CRM {m['crm']})")
            for m in self.medico_dao.listar_sem_usuario(id_medico_atual)
        ]

    def buscar(self, id_usuario):
        return self.usuario_dao.buscar_por_id(id_usuario)

    def criar(self, formulario):
        dados = self._validar(formulario, novo=True)
        dados["senha_hash"] = generate_password_hash(formulario.get("senha"))
        try:
            return self.usuario_dao.inserir(dados)
        except psycopg2.Error as erro:
            raise self._traduzir(erro)

    def editar(self, id_usuario, formulario, id_usuario_logado):
        atual = self.usuario_dao.buscar_por_id(id_usuario)
        if not atual:
            raise ErroNegocio("Usuário não encontrado.")

        dados = self._validar(formulario, novo=False, atual=atual)
        if id_usuario == id_usuario_logado and atual["perfil"] == "ADMIN" and dados["perfil"] != "ADMIN":
            raise ErroValidacao({"perfil": "Você não pode remover o seu próprio acesso de administrador."})

        try:
            self.usuario_dao.atualizar(id_usuario, dados)
            if formulario.get("senha"):
                self.usuario_dao.alterar_senha(id_usuario, generate_password_hash(formulario["senha"]))
        except psycopg2.Error as erro:
            raise self._traduzir(erro)

    def alternar_ativo(self, id_usuario, id_usuario_logado):
        """Ativa um usuário inativo ou desativa um ativo. Devolve o usuário atualizado."""
        usuario = self.usuario_dao.buscar_por_id(id_usuario)
        if not usuario:
            raise ErroNegocio("Usuário não encontrado.")
        if id_usuario == id_usuario_logado:
            raise ErroNegocio("Você não pode desativar o seu próprio usuário.")

        self.usuario_dao.definir_ativo(id_usuario, not usuario["ativo"])
        usuario["ativo"] = not usuario["ativo"]
        return usuario

    def _validar(self, formulario, novo, atual=None):
        erros = {}
        nome = (formulario.get("nome") or "").strip()
        email = (formulario.get("email") or "").strip().lower()
        perfil = formulario.get("perfil") or ""
        senha = formulario.get("senha") or ""

        if not nome:
            erros["nome"] = "Informe o nome."
        elif len(nome) > 100:
            erros["nome"] = "Use no máximo 100 caracteres."

        if not EMAIL_VALIDO.match(email):
            erros["email"] = "Informe um e-mail válido."
        elif len(email) > 100:
            erros["email"] = "Use no máximo 100 caracteres."

        if perfil not in PERFIS:
            erros["perfil"] = "Escolha um perfil."

        # o perfil Médico precisa do cadastro de médico ao qual o usuário corresponde
        id_medico = None
        if perfil == "MEDICO":
            try:
                id_medico = int(formulario.get("id_medico") or 0) or None
            except ValueError:
                id_medico = None
            if not id_medico:
                erros["id_medico"] = "Escolha o médico vinculado a este usuário."
            elif not self.medico_dao.buscar_por_id(id_medico):
                erros["id_medico"] = "Médico não encontrado."

        # na edição a senha é opcional: em branco mantém a atual
        if novo or senha:
            validar_nova_senha(senha, formulario.get("confirmacao_senha"), erros)

        if erros:
            raise ErroValidacao(erros)
        return {"nome": nome, "email": email, "perfil": perfil, "id_medico": id_medico}

    def _traduzir(self, erro):
        if erro.pgcode == errorcodes.UNIQUE_VIOLATION:
            if "id_medico" in (erro.diag.constraint_name or ""):
                return ErroValidacao({"id_medico": "Este médico já está vinculado a outro usuário."})
            return ErroValidacao({"email": "Já existe um usuário com este e-mail."})
        return erro_do_banco(erro)
