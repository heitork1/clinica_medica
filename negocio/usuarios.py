"""Camada de Negócio: Regras de negócio para Usuários do Sistema.

Esta classe gerencia a criação, edição, ativação/desativação e validação de usuários:
- Validação de formato de e-mail e unicidade.
- Garantia de que a senha tenha requisitos mínimos e seja armazenada em HASH seguro.
- Vínculo exclusivo entre usuário com perfil 'MEDICO' e seu cadastro na tabela 'medico'.
- Regra de segurança: impede que um administrador remova seu próprio acesso de ADMIN ou se desative.
"""

import psycopg2
from psycopg2 import errorcodes
from werkzeug.security import generate_password_hash

from dados.medico import MedicoDAO
from dados.usuario import UsuarioDAO
from negocio import ErroNegocio, ErroValidacao, erro_do_banco
from negocio.autenticacao import PERFIS, validar_nova_senha
from negocio.validacao import EMAIL_VALIDO


class ServicoUsuarios:
    """Coordena as regras de negócio e permissões de usuários."""

    def __init__(self):
        # Acesso aos objetos de dados (Camada de Dados / DAOs)
        self.usuario_dao = UsuarioDAO()
        self.medico_dao = MedicoDAO()

    def listar(self):
        """Retorna todos os usuários ordenados por status ativo e nome."""
        return self.usuario_dao.listar()

    def buscar(self, id_usuario):
        """Busca um usuário pelo seu ID."""
        return self.usuario_dao.buscar_por_id(id_usuario)

    def medicos_para_vinculo(self, id_medico_atual=None):
        """Retorna opções de médicos que ainda não têm usuário no sistema.

        Formato: lista de tuplas (id_medico, 'Nome (CRM 1234/UF)').
        Na edição, inclui também o médico já vinculado ao usuário atual.
        """
        return [
            (m["id_medico"], f"{m['nome_medico']} (CRM {m['crm']})")
            for m in self.medico_dao.listar_sem_usuario(id_medico_atual)
        ]

    def criar(self, formulario):
        """Cadastra um novo usuário no sistema aplicando as regras de negócio."""
        # 1. Valida os campos enviados pelo formulário
        dados = self._validar(formulario, novo=True)

        # 2. Gera o hash seguro da senha (nunca grava senha em texto puro no banco)
        dados["senha_hash"] = generate_password_hash(formulario.get("senha"))

        # 3. Persiste no banco através do DAO
        try:
            return self.usuario_dao.inserir(dados)
        except psycopg2.Error as erro:
            raise self._traduzir_erro_banco(erro)

    def editar(self, id_usuario, formulario, id_usuario_logado):
        """Atualiza os dados de um usuário existente."""
        atual = self.usuario_dao.buscar_por_id(id_usuario)
        if not atual:
            raise ErroNegocio("Usuário não encontrado.")

        # Valida as alterações
        dados = self._validar(formulario, novo=False, atual=atual)

        # Regra de negócio: não permite o admin tirar o próprio perfil de administrador
        if id_usuario == id_usuario_logado and atual["perfil"] == "ADMIN" and dados["perfil"] != "ADMIN":
            raise ErroValidacao({"perfil": "Você não pode remover o seu próprio acesso de administrador."})

        try:
            # Atualiza os dados cadastrais
            self.usuario_dao.atualizar(id_usuario, dados)

            # Se foi digitada uma nova senha no formulário, atualiza o hash
            if formulario.get("senha"):
                self.usuario_dao.alterar_senha(id_usuario, generate_password_hash(formulario["senha"]))
        except psycopg2.Error as erro:
            raise self._traduzir_erro_banco(erro)

    def alternar_ativo(self, id_usuario, id_usuario_logado):
        """Ativa ou desativa um usuário (impede exclusão física para manter histórico)."""
        usuario = self.usuario_dao.buscar_por_id(id_usuario)
        if not usuario:
            raise ErroNegocio("Usuário não encontrado.")

        # Regra de segurança: impede auto-desativação
        if id_usuario == id_usuario_logado:
            raise ErroNegocio("Você não pode desativar o seu próprio usuário.")

        novo_status = not usuario["ativo"]
        self.usuario_dao.definir_ativo(id_usuario, novo_status)
        usuario["ativo"] = novo_status
        return usuario

    def _validar(self, formulario, novo, atual=None):
        """Validações de campos e regras de preenchimento."""
        erros = {}
        nome = (formulario.get("nome") or "").strip()
        email = (formulario.get("email") or "").strip().lower()
        perfil = formulario.get("perfil") or ""
        senha = formulario.get("senha") or ""

        # Validação do Nome
        if not nome:
            erros["nome"] = "Informe o nome."
        elif len(nome) > 100:
            erros["nome"] = "Use no máximo 100 caracteres."

        # Validação do E-mail
        if not EMAIL_VALIDO.match(email):
            erros["email"] = "Informe um e-mail válido."
        elif len(email) > 100:
            erros["email"] = "Use no máximo 100 caracteres."

        # Validação do Perfil
        if perfil not in PERFIS:
            erros["perfil"] = "Escolha um perfil válido (ADMIN, RECEPCAO ou MEDICO)."

        # Regra de negócio: Perfil 'MEDICO' exige obrigatoriamente um médico vinculado
        id_medico = None
        if perfil == "MEDICO":
            try:
                id_medico = int(formulario.get("id_medico") or 0) or None
            except ValueError:
                id_medico = None

            if not id_medico:
                erros["id_medico"] = "Escolha o médico vinculado a este usuário."
            elif not self.medico_dao.buscar_por_id(id_medico):
                erros["id_medico"] = "Médico não encontrado no cadastro."

        # Validação da Senha (obrigatória no cadastro; opcional na edição)
        if novo or senha:
            validar_nova_senha(senha, formulario.get("confirmacao_senha"), erros)

        if erros:
            raise ErroValidacao(erros)

        return {"nome": nome, "email": email, "perfil": perfil, "id_medico": id_medico}

    def _traduzir_erro_banco(self, erro):
        """Traduz violações de chave única do banco em mensagens amigáveis."""
        if erro.pgcode == errorcodes.UNIQUE_VIOLATION:
            if "id_medico" in (erro.diag.constraint_name or ""):
                return ErroValidacao({"id_medico": "Este médico já está vinculado a outro usuário."})
            return ErroValidacao({"email": "Já existe um usuário cadastrado com este e-mail."})
        return erro_do_banco(erro)
