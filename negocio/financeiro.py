from datetime import date
from decimal import Decimal

import psycopg2

from dados.consulta import ConsultaDAO
from dados.financeiro import FinanceiroDAO
from dados.paciente import PacienteDAO
from negocio import ErroNegocio, ErroValidacao, converter_moeda, erro_do_banco, formatar_moeda
from negocio.validacao import converter_data

FORMAS_PAGAMENTO = {"DINHEIRO": "Dinheiro", "CARTAO": "Cartão", "PIX": "PIX"}


def convenios_validos(convenios, dia):
    """Convênios do paciente com carteirinha válida no dia (sem validade conta como válida)."""
    return [c for c in convenios if not c["validade"] or c["validade"] >= dia]


class ServicoFinanceiro:

    def __init__(self):
        self.financeiro_dao = FinanceiroDAO()
        self.consulta_dao = ConsultaDAO()
        self.paciente_dao = PacienteDAO()

    def buscar(self, id_consulta):
        """Consulta realizada com conta, pagamentos, procedimentos e convênios do paciente."""
        consulta = self.consulta_dao.buscar_por_id(id_consulta)
        if not consulta:
            return None
        consulta["conta"] = self.financeiro_dao.buscar_conta(consulta["id_conta"]) if consulta["id_conta"] else None
        consulta["pagamentos"] = self.financeiro_dao.listar_pagamentos(consulta["id_conta"]) if consulta["id_conta"] else []
        consulta["procedimentos"] = self.consulta_dao.procedimentos(id_consulta)
        paciente = self.paciente_dao.buscar_por_id(consulta["id_paciente"])
        consulta["convenios"] = paciente["convenios"] if paciente else []
        consulta["convenios_validos"] = convenios_validos(consulta["convenios"], date.today())
        return consulta

    def contas_em_aberto(self, limite=10):
        return self.financeiro_dao.contas_em_aberto(limite)

    def registrar_pagamento(self, consulta, formulario):
        conta = consulta["conta"]
        if not conta:
            raise ErroNegocio("A consulta ainda não tem conta: ela é gerada ao finalizar o atendimento.")
        if conta["saldo"] <= 0:
            raise ErroNegocio("Esta conta já está quitada.")

        dados = self._validar(consulta, formulario)
        try:
            self.financeiro_dao.inserir_pagamento({**dados, "id_conta": conta["id_conta"]})
        except psycopg2.Error as erro:
            # o gatilho "impedir pagamentos acima do total" (seção 5.3) também cai aqui
            raise erro_do_banco(erro)
        return dados

    def excluir_pagamento(self, consulta, id_pagamento):
        if not consulta["id_conta"] or not self.financeiro_dao.excluir_pagamento(id_pagamento, consulta["id_conta"]):
            raise ErroNegocio("Pagamento não encontrado.")

    def _validar(self, consulta, formulario):
        erros = {}
        saldo = consulta["conta"]["saldo"]

        data_pagamento = None
        try:
            data_pagamento = converter_data(formulario.get("data_pagamento"))
        except ValueError:
            pass
        if not data_pagamento:
            erros["data_pagamento"] = "Informe a data do pagamento."
        elif data_pagamento > date.today():
            erros["data_pagamento"] = "A data do pagamento não pode estar no futuro."
        elif consulta["data_hora_marcado"] and data_pagamento < consulta["data_hora_marcado"].date():
            erros["data_pagamento"] = "O pagamento não pode ser anterior à consulta."

        def ler_valor(campo):
            try:
                return converter_moeda(formulario.get(campo)) or Decimal("0.00")
            except ValueError:
                erros[campo] = "Informe um valor válido."
                return Decimal("0.00")

        possui_convenio = formulario.get("possui_convenio") == "on"
        valor_pago = ler_valor("valor_pago")
        valor_convenio = ler_valor("valor_convenio") if possui_convenio else None

        if possui_convenio:
            if not convenios_validos(consulta["convenios"], data_pagamento or date.today()):
                erros["possui_convenio"] = "O paciente não tem convênio com carteirinha válida nessa data."
            elif not valor_convenio or valor_convenio <= 0:
                erros["valor_convenio"] = "Informe o valor pago pelo convênio."

        if valor_pago < 0:
            erros["valor_pago"] = "O valor não pode ser negativo."

        forma = formulario.get("forma_pagamento") or None
        if valor_pago > 0 and forma not in FORMAS_PAGAMENTO:
            erros["forma_pagamento"] = "Escolha a forma de pagamento."
        if valor_pago == 0:
            forma = None  # sem valor do paciente não há forma de pagamento

        total = valor_pago + (valor_convenio or 0)
        if not erros:
            if total <= 0:
                erros["valor_pago"] = "Informe o valor pago."
            elif total > saldo:
                erros["valor_pago"] = f"O pagamento ({formatar_moeda(total)}) passa do saldo da conta ({formatar_moeda(saldo)})."

        if erros:
            raise ErroValidacao(erros)

        return {
            "data_pagamento": data_pagamento,
            "valor_pago": valor_pago,
            "forma_pagamento": forma,
            "possui_convenio": possui_convenio,
            "valor_convenio": valor_convenio,
        }
