from werkzeug.security import check_password_hash, generate_password_hash

from dados.usuario import UsuarioDAO
from negocio import ErroNegocio, ErroValidacao

PERFIS = {
    "ADMIN": "Administrador",
    "RECEPCAO": "Recepção",
    "MEDICO": "Médico",
}

TAMANHO_MINIMO_SENHA = 6


def validar_nova_senha(senha, confirmacao, erros, campo="senha", campo_confirmacao="confirmacao_senha"):
    """Confere tamanho e confirmação; os problemas vão para o dicionário `erros`."""
    if len(senha or "") < TAMANHO_MINIMO_SENHA:
        erros[campo] = f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
    elif senha != confirmacao:
        erros[campo_confirmacao] = "As senhas não conferem."


def dados_da_sessao(usuario):
    """O que fica guardado na sessão do Flask enquanto o usuário está logado."""
    return {
        "id_usuario": usuario["id_usuario"],
        "nome": usuario["nome"],
        "perfil": usuario["perfil"],
        "id_medico": usuario["id_medico"],
    }


class ServicoAutenticacao:

    def __init__(self):
        self.usuario_dao = UsuarioDAO()

    def entrar(self, email, senha):
        """Confere as credenciais e devolve os dados para a sessão."""
        usuario = self.usuario_dao.buscar_para_login((email or "").strip())

        # mesma mensagem para e-mail inexistente e senha errada
        if not usuario or not check_password_hash(usuario["senha_hash"], senha or ""):
            raise ErroNegocio("E-mail ou senha incorretos.")
        if not usuario["ativo"]:
            raise ErroNegocio("Este usuário está desativado. Procure o administrador do sistema.")

        return dados_da_sessao(usuario)

    def trocar_senha(self, id_usuario, senha_atual, nova_senha, confirmacao):
        erros = {}
        senha_hash = self.usuario_dao.buscar_senha_hash(id_usuario)
        if not senha_hash or not check_password_hash(senha_hash, senha_atual or ""):
            erros["senha_atual"] = "Senha atual incorreta."
        validar_nova_senha(nova_senha, confirmacao, erros, campo="nova_senha")
        if erros:
            raise ErroValidacao(erros)

        self.usuario_dao.alterar_senha(id_usuario, generate_password_hash(nova_senha))
