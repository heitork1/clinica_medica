import logging
from decimal import Decimal, InvalidOperation

from psycopg2 import errorcodes

log = logging.getLogger(__name__)


class ErroNegocio(Exception):
    """Erro com mensagem pronta para mostrar ao usuário.

    Os serviços lançam este erro quando uma regra é violada ou quando o banco
    recusa a operação (ex.: mensagem de um gatilho). As rotas capturam e exibem
    a mensagem com flash().
    """


class ErroValidacao(ErroNegocio):
    """Erros de preenchimento, um por campo: {"email": "Informe um e-mail válido."}.

    A rota exibe a mensagem geral com flash() e passa `erros` ao template,
    que marca cada campo com a sua mensagem.
    """

    def __init__(self, erros, mensagem="Corrija os campos destacados."):
        super().__init__(mensagem)
        self.erros = erros


def erro_do_banco(erro, mensagens=None):
    """Converte um psycopg2.Error em ErroNegocio.

    mensagens: textos para códigos SQLSTATE conhecidos, por exemplo
    {errorcodes.FOREIGN_KEY_VIOLATION: "Registro em uso."}.
    Mensagens levantadas por gatilhos (RAISE EXCEPTION) passam direto.
    """
    mensagens = mensagens or {}
    if erro.pgcode in mensagens:
        return ErroNegocio(mensagens[erro.pgcode])
    if erro.pgcode == errorcodes.RAISE_EXCEPTION and erro.diag.message_primary:
        return ErroNegocio(erro.diag.message_primary)

    log.exception("Erro não tratado do banco de dados")
    return ErroNegocio("Não foi possível concluir a operação no banco de dados.")


def formatar_moeda(valor):
    """1234.5 -> 'R$ 1.234,50' (sem depender do locale do sistema operacional)."""
    if valor is None or valor == "":
        return ""
    # formata no padrão americano (1,234.50) e troca os separadores
    texto = f"{Decimal(str(valor)):,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def converter_moeda(texto):
    """'1.234,56' (como vem da máscara) ou '1234.56' -> Decimal('1234.56').

    Devolve None para texto vazio e lança ValueError se não for um número.
    """
    return converter_decimal((texto or "").replace("R$", ""))


def converter_decimal(texto):
    """'40', '12,5', '1.234,56' ou '1234.56' -> Decimal com duas casas.

    Aceita vírgula ou ponto como separador decimal. Devolve None para texto
    vazio e lança ValueError se não for um número.
    """
    texto = (texto or "").strip()
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"valor inválido: {texto}")
    if not valor.is_finite():
        raise ValueError(f"valor inválido: {texto}")
    return valor.quantize(Decimal("0.01"))
