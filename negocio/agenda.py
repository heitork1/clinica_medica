from datetime import date, datetime, timedelta

import psycopg2

from dados.cadastros import EspecialidadeDAO, SalaDAO
from dados.consulta import ConsultaDAO
from dados.medico import MedicoDAO
from dados.paciente import PacienteDAO
from negocio import ErroNegocio, ErroValidacao, erro_do_banco
from negocio.medicos import DIAS_SEMANA, ORDEM_DIAS
from negocio.validacao import converter_data, converter_hora

# Duração de cada consulta (item 9 da seção 5.2 do plano). Os gatilhos do banco usam
# o mesmo valor, em fn_duracao_consulta() (banco/funcoes-gatilhos.sql).
DURACAO_CONSULTA = timedelta(minutes=30)

STATUS = {
    "AGENDADA": "Agendada",
    "CONFIRMADA": "Confirmada",
    "REALIZADA": "Realizada",
    "CANCELADA": "Cancelada",
    "FALTOU": "Faltou",
}

# mudanças de status feitas pela agenda; REALIZADA só pelo atendimento (negocio/atendimento.py)
TRANSICOES = {
    "AGENDADA": ("CONFIRMADA", "CANCELADA", "FALTOU"),
    "CONFIRMADA": ("CANCELADA", "FALTOU"),
}

# texto das mensagens de sucesso: "Consulta de Fulano confirmada."
VERBOS_STATUS = {"CONFIRMADA": "confirmada", "CANCELADA": "cancelada", "FALTOU": "marcada como falta"}


def dia_da_semana(dia):
    """date -> 'SEGUNDA', 'TERCA' ... (mesmos valores de horario.dia_semana)."""
    return ORDEM_DIAS[dia.weekday()]


def descrever_dia(dia):
    """date -> 'Terça-feira, 27/10/2026'."""
    return f"{DIAS_SEMANA[dia_da_semana(dia)][0]}, {dia.strftime('%d/%m/%Y')}"


def proximos_status(consulta, agora=None):
    """Status para os quais a consulta pode ir pela agenda.

    Marcar falta só faz sentido depois do horário marcado.
    """
    agora = agora or datetime.now()
    opcoes = TRANSICOES.get(consulta["status"], ())
    if consulta["data_hora_marcado"] and consulta["data_hora_marcado"] > agora:
        opcoes = tuple(s for s in opcoes if s != "FALTOU")
    return opcoes


class ServicoAgenda:

    def __init__(self):
        self.consulta_dao = ConsultaDAO()
        self.medico_dao = MedicoDAO()
        self.paciente_dao = PacienteDAO()
        self.sala_dao = SalaDAO()
        self.especialidade_dao = EspecialidadeDAO()

    # ------------------------------------------------------------- agenda
    def agenda_do_dia(self, dia, id_medico=None, status=None):
        consultas = self.consulta_dao.listar_do_dia(dia, id_medico, status or None)
        agora = datetime.now()
        for consulta in consultas:
            consulta["proximos_status"] = proximos_status(consulta, agora)
        return consultas

    def medicos(self):
        return self.medico_dao.listar_para_selecao()

    def alterar_status(self, id_consulta, novo_status):
        consulta = self.consulta_dao.buscar_por_id(id_consulta)
        if not consulta:
            raise ErroNegocio("Consulta não encontrada.")
        if novo_status not in proximos_status(consulta):
            atual = STATUS.get(consulta["status"], consulta["status"])
            destino = STATUS.get(novo_status, novo_status)
            raise ErroNegocio(f"Uma consulta {atual.lower()} não pode passar para {destino.lower()}.")
        try:
            self.consulta_dao.atualizar_status(id_consulta, novo_status)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro)
        return consulta

    # --------------------------------------------------------- agendamento
    def opcoes_agendamento(self):
        """Listas para a tela de nova consulta."""
        return {
            "pacientes": self.paciente_dao.listar_para_selecao(),
            "medicos": self.medico_dao.listar_para_selecao(),
            "especialidades": self.especialidade_dao.listar(),
            "salas": self.sala_dao.listar(),
        }

    def horarios_livres(self, id_medico, dia, agora=None):
        """Horários ("08:00", "08:30", ...) em que o médico pode receber uma consulta no dia.

        Parte das faixas de atendimento do médico naquele dia da semana, divide
        pela duração da consulta e tira os horários já ocupados e os que já passaram.
        """
        agora = agora or datetime.now()
        if dia < agora.date():
            return []

        ocupados = self.consulta_dao.horarios_marcados(id_medico, dia)
        livres = []
        for faixa in self.medico_dao.horarios_do_dia(id_medico, dia_da_semana(dia)):
            inicio = datetime.combine(dia, faixa["hora_inicio"])
            fim = datetime.combine(dia, faixa["hora_fim"])
            while inicio + DURACAO_CONSULTA <= fim:
                choca = any(abs(inicio - marcado) < DURACAO_CONSULTA for marcado in ocupados)
                if inicio > agora and not choca:
                    livres.append(inicio.strftime("%H:%M"))
                inicio += DURACAO_CONSULTA
        return livres

    def agendar(self, formulario):
        dados = self._validar_agendamento(formulario)
        try:
            return self.consulta_dao.inserir(dados)
        except psycopg2.Error as erro:
            # conflitos também podem ser recusados por gatilhos do banco (seção 5.3)
            raise erro_do_banco(erro)

    def _validar_agendamento(self, formulario):
        erros = {}

        def ler_id(campo):
            try:
                return int(formulario.get(campo) or 0) or None
            except ValueError:
                return None

        id_paciente, id_medico, id_sala = ler_id("id_paciente"), ler_id("id_medico"), ler_id("id_sala")
        if not id_paciente or not self.paciente_dao.buscar_por_id(id_paciente):
            erros["id_paciente"] = "Escolha o paciente."
        if not id_medico or not self.medico_dao.buscar_por_id(id_medico):
            erros["id_medico"] = "Escolha o médico."
        if not id_sala or not self.sala_dao.buscar_por_id(id_sala):
            erros["id_sala"] = "Escolha a sala."

        dia = hora = None
        try:
            dia = converter_data(formulario.get("data"))
        except ValueError:
            pass
        if not dia:
            erros["data"] = "Informe a data."
        elif dia < date.today():
            erros["data"] = "A data já passou."

        try:
            hora = converter_hora(formulario.get("hora"))
        except ValueError:
            pass
        if not hora:
            erros["hora"] = "Escolha um horário."

        if erros:
            raise ErroValidacao(erros)

        data_hora = datetime.combine(dia, hora)
        if hora.strftime("%H:%M") not in self.horarios_livres(id_medico, dia):
            erros["hora"] = "Esse horário não está livre na agenda do médico. Escolha outro da lista."
        elif self.consulta_dao.existe_conflito("id_sala", id_sala, data_hora, DURACAO_CONSULTA):
            erros["id_sala"] = "A sala já está ocupada nesse horário."
        elif self.consulta_dao.existe_conflito("id_paciente", id_paciente, data_hora, DURACAO_CONSULTA):
            erros["id_paciente"] = "O paciente já tem outra consulta nesse horário."
        if erros:
            raise ErroValidacao(erros)

        return {"data_hora_marcado": data_hora, "id_paciente": id_paciente, "id_medico": id_medico, "id_sala": id_sala}
