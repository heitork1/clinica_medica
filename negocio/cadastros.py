"""Camada de Negócio: Regras de negócio e validações para Cadastros Simples.

Entidades atendidas: Convênio, Especialidade, Procedimento e Sala.
Esta camada intermedeia a Apresentação (rotas) e os Dados (DAOs):
- Valida campos obrigatórios e tamanhos máximos.
- Converte valores numéricos e monetários.
- Impede registros duplicados (validação de unicidade).
- Impede exclusão de registros que possuam chave estrangeira em uso.
"""

from decimal import Decimal
import psycopg2
from psycopg2 import errorcodes

from dados.cadastros import ConvenioDAO, EspecialidadeDAO, ProcedimentoDAO, SalaDAO
from negocio import ErroNegocio, ErroValidacao, converter_moeda, erro_do_banco

VALOR_MAXIMO = Decimal("99999999.99")  # Limite para campos NUMERIC(10,2)


# ==============================================================================
# Classes de Domínio / Estrutura de Apresentação
# ==============================================================================
class Campo:
    """Representa um campo de dados no formulário e na tabela."""
    def __init__(self, nome, rotulo, tamanho=100, tipo="texto"):
        self.nome = nome          # Nome do campo no form e coluna no banco
        self.rotulo = rotulo      # Rótulo exibido na tela (label / header)
        self.tamanho = tamanho    # Tamanho máximo de caracteres (VARCHAR)
        self.tipo = tipo          # Tipo de dados: 'texto' ou 'moeda'


class Cadastro:
    """Define a configuração de um cadastro simples e sua ligação com o DAO correspondente."""
    def __init__(self, titulo, singular, feminino, dao, campos, unico=None, rotulo_chave=None):
        self.titulo = titulo              # Título no plural (ex: 'Convênios')
        self.singular = singular          # Nome no singular (ex: 'convênio')
        self.feminino = feminino          # True para palavras femininas ('sala')
        self.dao = dao                    # Instância do DAO responsável pelo acesso ao banco
        self.campos = campos              # Lista de objetos Campo
        self.unico = unico                # Nome da coluna que não pode ter duplicidade
        self.rotulo_chave = rotulo_chave  # Rótulo da PK na tabela ('Código', 'Nº')

    @property
    def artigo(self):
        """Retorna 'a' se feminino ou 'o' se masculino."""
        return "a" if self.feminino else "o"

    @property
    def titulo_novo(self):
        """Retorna 'Novo [singular]' ou 'Nova [singular]'."""
        return ("Nova " if self.feminino else "Novo ") + self.singular

    @property
    def titulo_editar(self):
        """Retorna 'Editar [singular]'."""
        return "Editar " + self.singular

    def descrever(self, registro):
        """Retorna a descrição principal do registro para mensagens de feedback."""
        return registro[self.campos[0].nome]


# Dicionário de Cadastros Disponíveis
CADASTROS = {
    "convenios": Cadastro(
        titulo="Convênios",
        singular="convênio",
        feminino=False,
        dao=ConvenioDAO(),
        campos=[Campo("nome", "Nome", tamanho=100)],
        unico="nome",
    ),
    "especialidades": Cadastro(
        titulo="Especialidades",
        singular="especialidade",
        feminino=True,
        dao=EspecialidadeDAO(),
        campos=[Campo("nome_especialidade", "Nome", tamanho=60)],
        unico="nome_especialidade",
    ),
    "procedimentos": Cadastro(
        titulo="Procedimentos",
        singular="procedimento",
        feminino=False,
        dao=ProcedimentoDAO(),
        campos=[
            Campo("descricao", "Descrição", tamanho=200),
            Campo("valor", "Valor (R$)", tipo="moeda"),
        ],
        unico="descricao",
        rotulo_chave="Código",
    ),
    "salas": Cadastro(
        titulo="Salas",
        singular="sala",
        feminino=True,
        dao=SalaDAO(),
        campos=[Campo("descricao", "Descrição", tamanho=100)],
        unico="descricao",
        rotulo_chave="Nº",
    ),
}


# ==============================================================================
# Camada de Negócio: Serviço de Cadastros
# ==============================================================================
class ServicoCadastros:
    """Coordena as operações de negócio dos cadastros simples."""

    def obter(self, tipo):
        """Obtém as configurações da entidade pelo identificador da URL."""
        return CADASTROS.get(tipo)

    def listar(self, tipo):
        """Lista todos os registros da entidade informada."""
        return CADASTROS[tipo].dao.listar()

    def buscar(self, tipo, id_registro):
        """Busca um registro específico pelo seu ID."""
        return CADASTROS[tipo].dao.buscar_por_id(id_registro)

    def salvar(self, tipo, formulario, id_registro=None):
        """Valida os dados e realiza a inserção ou atualização no banco de dados."""
        cadastro = CADASTROS[tipo]
        dados = self._validar(cadastro, formulario, id_registro)

        try:
            if id_registro:
                # Atualização: verifica se o registro existe antes de alterar
                if not cadastro.dao.buscar_por_id(id_registro):
                    raise ErroNegocio(f"{cadastro.singular.capitalize()} não encontrad{cadastro.artigo}.")
                cadastro.dao.atualizar(id_registro, dados)
            else:
                # Inserção de novo registro
                cadastro.dao.inserir(dados)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro)

        return dados

    def excluir(self, tipo, id_registro):
        """Exclui um registro, tratando restrições de integridade referencial (FK)."""
        cadastro = CADASTROS[tipo]
        registro = cadastro.dao.buscar_por_id(id_registro)

        if not registro:
            raise ErroNegocio(f"{cadastro.singular.capitalize()} não encontrad{cadastro.artigo}.")

        # Mensagem clara caso haja chave estrangeira impedindo a exclusão
        em_uso = (
            f'Não é possível excluir {cadastro.artigo} {cadastro.singular} "{cadastro.descrever(registro)}": '
            f"já existem registros vinculados a ele(a) no sistema."
        )

        try:
            cadastro.dao.excluir(id_registro)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro, {errorcodes.FOREIGN_KEY_VIOLATION: em_uso})

        return registro

    def _validar(self, cadastro, formulario, id_registro):
        """Aplica as regras de validação para os campos enviados no formulário."""
        dados = {}
        erros = {}

        for campo in cadastro.campos:
            texto = (formulario.get(campo.nome) or "").strip()

            if campo.tipo == "moeda":
                # Validação de valor monetário
                try:
                    valor = converter_moeda(texto)
                except ValueError:
                    erros[campo.nome] = "Informe um valor numérico válido."
                    continue

                if valor is None:
                    erros[campo.nome] = "Informe o valor."
                elif valor < 0 or valor > VALOR_MAXIMO:
                    erros[campo.nome] = "Informe um valor entre R$ 0,00 e R$ 99.999.999,99."

                dados[campo.nome] = valor
            else:
                # Validação de texto padrão
                if not texto:
                    erros[campo.nome] = f"Preencha o campo {campo.rotulo.lower()}."
                elif len(texto) > campo.tamanho:
                    erros[campo.nome] = f"Use no máximo {campo.tamanho} caracteres."

                dados[campo.nome] = texto

        # Validação de Unicidade: impede duplicidade de nome ou descrição
        campo_unico = cadastro.unico
        if campo_unico and campo_unico not in erros:
            if cadastro.dao.existe(dados[campo_unico], id_registro):
                erros[campo_unico] = f'Já existe {"uma" if cadastro.feminino else "um"} {cadastro.singular} com o valor "{dados[campo_unico]}".'

        # Se houver qualquer erro de validação, lança exceção com o dicionário de erros
        if erros:
            raise ErroValidacao(erros)

        return dados
