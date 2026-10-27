from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2

from config import Config
from dados.cadastros import ProcedimentoDAO
from dados.consulta import ConsultaDAO
from dados.financeiro import FinanceiroDAO
from dados.paciente import PacienteDAO
from negocio import ErroNegocio, ErroValidacao, converter_moeda, erro_do_banco

# status em que o atendimento pode ser registrado (REALIZADA permite corrigir)
STATUS_ATENDIMENTO = ("AGENDADA", "CONFIRMADA", "REALIZADA")
QUANTIDADE_MAXIMA = 99


class ServicoAtendimento:

    def __init__(self):
        self.consulta_dao = ConsultaDAO()
        self.procedimento_dao = ProcedimentoDAO()
        self.paciente_dao = PacienteDAO()
        self.financeiro_dao = FinanceiroDAO()

    def buscar(self, id_consulta):
        """Consulta com paciente (e convênios), procedimentos e conta."""
        consulta = self.consulta_dao.buscar_por_id(id_consulta)
        if not consulta:
            return None
        paciente = self.paciente_dao.buscar_por_id(consulta["id_paciente"])
        consulta["convenios"] = paciente["convenios"] if paciente else []
        consulta["procedimentos"] = self.consulta_dao.procedimentos(id_consulta)
        consulta["conta"] = self.consulta_dao.buscar_conta(consulta["id_conta"]) if consulta["id_conta"] else None
        # com pagamento registrado, mudar procedimentos ou valores desalinharia a conta já paga
        consulta["pago"] = bool(consulta["id_conta"]) and self.financeiro_dao.tem_pagamento(consulta["id_conta"])
        return consulta

    def procedimentos_disponiveis(self):
        return self.procedimento_dao.listar()

    def eh_medico_da_consulta(self, consulta, usuario):
        return usuario["perfil"] == "MEDICO" and usuario["id_medico"] == consulta["id_medico"]

    def pode_registrar(self, consulta, usuario):
        """Só o médico da consulta registra o atendimento (seção 6 do plano), e só
        enquanto a conta não tiver pagamento."""
        return (
            self.eh_medico_da_consulta(consulta, usuario)
            and consulta["status"] in STATUS_ATENDIMENTO
            and not consulta.get("pago")
        )

    def pode_ver(self, consulta, usuario):
        """O médico da consulta e o administrador veem atendimentos realizados."""
        if self.pode_registrar(consulta, usuario):
            return True
        realizada = consulta["status"] == "REALIZADA"
        return realizada and (usuario["perfil"] == "ADMIN" or self.eh_medico_da_consulta(consulta, usuario))

    def valor_padrao(self, consulta):
        """Valor que aparece no campo: o da conta, se já existe, ou o padrão do .env."""
        if consulta.get("conta") and consulta["conta"]["valor_consulta"] is not None:
            return consulta["conta"]["valor_consulta"]
        return Decimal(Config.VALOR_CONSULTA_PADRAO)

    def ler_formulario(self, formulario):
        """Monta o atendimento a partir do formulário (é o que volta à tela se houver erro)."""
        procedimentos = []
        for id_procedimento, quantidade in zip(formulario.getlist("id_procedimento"),
                                               formulario.getlist("quantidade")):
            if id_procedimento or quantidade.strip():
                procedimentos.append({"id_procedimento": id_procedimento, "quantidade": quantidade.strip()})
        return {
            "data_hora_realizado": formulario.get("data_hora_realizado") or "",
            "sintomas": (formulario.get("sintomas") or "").strip(),
            "diagnostico": (formulario.get("diagnostico") or "").strip(),
            "prescricao": (formulario.get("prescricao") or "").strip(),
            "valor_consulta": (formulario.get("valor_consulta") or "").strip(),
            "procedimentos": procedimentos,
        }

    def registrar(self, consulta, dados, usuario):
        """Grava o atendimento, marca a consulta como REALIZADA e gera (ou atualiza) a conta."""
        if consulta.get("pago"):
            raise ErroNegocio("A conta desta consulta já tem pagamento: o atendimento não pode mais ser alterado.")
        if not self.pode_registrar(consulta, usuario):
            raise ErroNegocio("Só o médico da consulta pode registrar este atendimento.")

        atendimento, procedimentos, valor_consulta = self._validar(consulta, dados)
        try:
            return self.consulta_dao.registrar_atendimento(consulta["id_consulta"], atendimento,
                                                           procedimentos, valor_consulta)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro)

    def _validar(self, consulta, dados):
        erros = {}

        realizado = None
        try:
            realizado = datetime.fromisoformat(dados["data_hora_realizado"]) if dados["data_hora_realizado"] else None
        except ValueError:
            pass
        if not realizado:
            erros["data_hora_realizado"] = "Informe a data e a hora do atendimento."
        elif realizado > datetime.now() + timedelta(minutes=5):
            erros["data_hora_realizado"] = "O atendimento não pode ser registrado com data futura."
        elif consulta["data_hora_marcado"] and realizado.date() < consulta["data_hora_marcado"].date():
            erros["data_hora_realizado"] = "O atendimento não pode ser anterior ao dia da consulta."

        if not dados["diagnostico"]:
            erros["diagnostico"] = "Informe o diagnóstico."

        valor_consulta = None
        try:
            valor_consulta = converter_moeda(dados["valor_consulta"])
        except ValueError:
            pass
        if valor_consulta is None or not Decimal(0) <= valor_consulta <= Decimal("99999999.99"):
            erros["valor_consulta"] = "Informe o valor da consulta."

        existentes = {p["id_procedimento"] for p in self.procedimento_dao.listar()}
        procedimentos, usados = [], set()
        for item in dados["procedimentos"]:
            try:
                id_procedimento = int(item["id_procedimento"])
                quantidade = int(item["quantidade"] or 1)
            except ValueError:
                erros["procedimentos"] = "Escolha o procedimento e a quantidade em todas as linhas."
                continue
            if id_procedimento not in existentes:
                erros["procedimentos"] = "Procedimento não encontrado."
            elif id_procedimento in usados:
                erros["procedimentos"] = "O mesmo procedimento aparece duas vezes. Use a quantidade."
            elif not 1 <= quantidade <= QUANTIDADE_MAXIMA:
                erros["procedimentos"] = f"A quantidade deve ficar entre 1 e {QUANTIDADE_MAXIMA}."
            else:
                usados.add(id_procedimento)
                procedimentos.append({"id_procedimento": id_procedimento, "quantidade": quantidade})

        if erros:
            raise ErroValidacao(erros)

        atendimento = {
            "data_hora_realizado": realizado.replace(second=0, microsecond=0),
            "sintomas": dados["sintomas"] or None,
            "diagnostico": dados["diagnostico"],
            "prescricao": dados["prescricao"] or None,
        }
        return atendimento, procedimentos, valor_consulta
