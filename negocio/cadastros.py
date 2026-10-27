from dataclasses import dataclass, field
from decimal import Decimal

import psycopg2
from psycopg2 import errorcodes

from dados.cadastros import ConvenioDAO, EspecialidadeDAO, ProcedimentoDAO, SalaDAO
from negocio import ErroNegocio, ErroValidacao, converter_moeda, erro_do_banco

VALOR_MAXIMO = Decimal("99999999.99")  # limite de NUMERIC(10,2)


@dataclass
class Campo:
    nome: str            # coluna no banco e name do campo no formulário
    rotulo: str
    tamanho: int = 100   # limite do VARCHAR
    tipo: str = "texto"  # "texto" ou "moeda"


@dataclass
class Cadastro:
    titulo: str          # "Convênios"
    singular: str        # "convênio"
    feminino: bool       # para "Nova sala" / "Novo convênio"
    dao: object
    campos: list = field(default_factory=list)
    unico: str = None            # coluna que não pode repetir
    rotulo_chave: str = None     # mostra a chave na tabela ("Código", "Nº")

    @property
    def artigo(self):
        return "a" if self.feminino else "o"

    @property
    def titulo_novo(self):
        return ("Nova " if self.feminino else "Novo ") + self.singular

    @property
    def titulo_editar(self):
        return "Editar " + self.singular

    def descrever(self, registro):
        """Texto que identifica o registro nas mensagens: o primeiro campo."""
        return registro[self.campos[0].nome]


# tipo na URL (/cadastros/<tipo>) -> configuração da tela
CADASTROS = {
    "convenios": Cadastro(
        titulo="Convênios", singular="convênio", feminino=False, dao=ConvenioDAO(),
        campos=[Campo("nome", "Nome", tamanho=100)], unico="nome",
    ),
    "especialidades": Cadastro(
        titulo="Especialidades", singular="especialidade", feminino=True, dao=EspecialidadeDAO(),
        campos=[Campo("nome_especialidade", "Nome", tamanho=60)], unico="nome_especialidade",
    ),
    "procedimentos": Cadastro(
        titulo="Procedimentos", singular="procedimento", feminino=False, dao=ProcedimentoDAO(),
        campos=[Campo("descricao", "Descrição", tamanho=200), Campo("valor", "Valor (R$)", tipo="moeda")],
        unico="descricao", rotulo_chave="Código",
    ),
    "salas": Cadastro(
        titulo="Salas", singular="sala", feminino=True, dao=SalaDAO(),
        campos=[Campo("descricao", "Descrição", tamanho=100)], unico="descricao", rotulo_chave="Nº",
    ),
}


class ServicoCadastros:

    def obter(self, tipo):
        return CADASTROS.get(tipo)

    def listar(self, tipo):
        return CADASTROS[tipo].dao.listar()

    def buscar(self, tipo, id_registro):
        return CADASTROS[tipo].dao.buscar_por_id(id_registro)

    def salvar(self, tipo, formulario, id_registro=None):
        """Cria (sem id) ou atualiza (com id). Devolve os dados gravados."""
        cadastro = CADASTROS[tipo]
        dados = self._validar(cadastro, formulario, id_registro)
        try:
            if id_registro:
                if not cadastro.dao.buscar_por_id(id_registro):
                    raise ErroNegocio(f"{cadastro.singular.capitalize()} não encontrad{cadastro.artigo}.")
                cadastro.dao.atualizar(id_registro, dados)
            else:
                cadastro.dao.inserir(dados)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro)
        return dados

    def excluir(self, tipo, id_registro):
        """Exclui e devolve o registro excluído (para a mensagem de confirmação)."""
        cadastro = CADASTROS[tipo]
        registro = cadastro.dao.buscar_por_id(id_registro)
        if not registro:
            raise ErroNegocio(f"{cadastro.singular.capitalize()} não encontrad{cadastro.artigo}.")

        em_uso = (
            f'Não é possível excluir {cadastro.artigo} {cadastro.singular} "{cadastro.descrever(registro)}": '
            f"há registros que dependem del{cadastro.artigo}."
        )
        try:
            cadastro.dao.excluir(id_registro)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro, {errorcodes.FOREIGN_KEY_VIOLATION: em_uso})
        return registro

    def _validar(self, cadastro, formulario, id_registro):
        dados, erros = {}, {}

        for campo in cadastro.campos:
            texto = (formulario.get(campo.nome) or "").strip()

            if campo.tipo == "moeda":
                try:
                    valor = converter_moeda(texto)
                except ValueError:
                    erros[campo.nome] = "Informe um valor válido."
                    continue
                if valor is None:
                    erros[campo.nome] = "Informe o valor."
                elif valor < 0 or valor > VALOR_MAXIMO:
                    erros[campo.nome] = "Informe um valor entre R$ 0,00 e R$ 99.999.999,99."
                dados[campo.nome] = valor
            else:
                if not texto:
                    erros[campo.nome] = f"Preencha o campo {campo.rotulo.lower()}."
                elif len(texto) > campo.tamanho:
                    erros[campo.nome] = f"Use no máximo {campo.tamanho} caracteres."
                dados[campo.nome] = texto

        unico = cadastro.unico
        if unico and unico not in erros and cadastro.dao.existe(unico, dados[unico], id_registro):
            erros[unico] = f'Já existe {"uma" if cadastro.feminino else "um"} {cadastro.singular} "{dados[unico]}".'

        if erros:
            raise ErroValidacao(erros)
        return dados
