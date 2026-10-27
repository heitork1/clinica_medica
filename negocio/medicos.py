from decimal import Decimal

import psycopg2
from psycopg2 import errorcodes

from dados.cadastros import EspecialidadeDAO
from dados.medico import MedicoDAO
from negocio import ErroNegocio, ErroValidacao, converter_decimal, erro_do_banco
from negocio.validacao import converter_hora, formatar_telefone

# valor gravado em horario.dia_semana -> (nome, abreviação), na ordem da semana
DIAS_SEMANA = {
    "SEGUNDA": ("Segunda-feira", "Seg"),
    "TERCA": ("Terça-feira", "Ter"),
    "QUARTA": ("Quarta-feira", "Qua"),
    "QUINTA": ("Quinta-feira", "Qui"),
    "SEXTA": ("Sexta-feira", "Sex"),
    "SABADO": ("Sábado", "Sáb"),
    "DOMINGO": ("Domingo", "Dom"),
}
ORDEM_DIAS = list(DIAS_SEMANA)


def no_dia(dia):
    """'SEGUNDA' -> 'na segunda-feira', 'SABADO' -> 'no sábado' (para as mensagens)."""
    artigo = "no" if dia in ("SABADO", "DOMINGO") else "na"
    return f"{artigo} {DIAS_SEMANA[dia][0].lower()}"


def ordenar_horarios(horarios):
    return sorted(horarios, key=lambda h: (ORDEM_DIAS.index(h["dia_semana"]) if h["dia_semana"] in ORDEM_DIAS
                                           else len(ORDEM_DIAS), str(h["hora_inicio"])))


class ServicoMedicos:

    def __init__(self):
        self.medico_dao = MedicoDAO()
        self.especialidade_dao = EspecialidadeDAO()

    def listar(self, id_especialidade=None):
        medicos = self.medico_dao.listar(id_especialidade)
        for medico in medicos:
            dias = [d for d in ORDEM_DIAS if d in (medico["dias"] or [])]
            medico["dias_abreviados"] = ", ".join(DIAS_SEMANA[d][1] for d in dias)
        return medicos

    def buscar(self, id_medico):
        medico = self.medico_dao.buscar_por_id(id_medico)
        if medico:
            medico["horarios"] = ordenar_horarios(medico["horarios"])
        return medico

    def especialidades(self):
        return self.especialidade_dao.listar()

    def ler_formulario(self, formulario):
        """Monta o médico a partir do formulário, no mesmo formato de buscar()."""
        horarios = []
        for dia, inicio, fim in zip(formulario.getlist("dia_semana"),
                                    formulario.getlist("hora_inicio"),
                                    formulario.getlist("hora_fim")):
            if dia or inicio or fim:
                horarios.append({"dia_semana": dia, "hora_inicio": inicio, "hora_fim": fim})

        return {
            "nome_medico": (formulario.get("nome_medico") or "").strip(),
            "crm": (formulario.get("crm") or "").strip().upper(),
            "percentual_honorario": (formulario.get("percentual_honorario") or "").strip(),
            "telefones": [t.strip() for t in formulario.getlist("telefone") if t.strip()],
            "especialidades": [e for e in formulario.getlist("especialidades") if e],
            "horarios": horarios,
        }

    def salvar(self, dados, id_medico=None):
        medico, telefones, especialidades, horarios = self._validar(dados)
        try:
            if id_medico:
                self.medico_dao.atualizar(id_medico, medico, telefones, especialidades, horarios)
                return id_medico
            return self.medico_dao.inserir(medico, telefones, especialidades, horarios)
        except psycopg2.Error as erro:
            if erro.pgcode == errorcodes.UNIQUE_VIOLATION and "crm" in (erro.diag.constraint_name or ""):
                raise ErroValidacao({"crm": "Já existe um médico com este CRM."})
            raise erro_do_banco(erro)

    def excluir(self, id_medico):
        medico = self.medico_dao.buscar_por_id(id_medico)
        if not medico:
            raise ErroNegocio("Médico não encontrado.")
        try:
            self.medico_dao.excluir(id_medico)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro, {
                errorcodes.FOREIGN_KEY_VIOLATION:
                    f"Não é possível excluir {medico['nome_medico']}: há consultas ou um usuário do sistema "
                    "ligados a este médico.",
            })
        return medico

    def _validar(self, dados):
        erros = {}

        if not dados["nome_medico"]:
            erros["nome_medico"] = "Informe o nome completo."
        elif len(dados["nome_medico"]) > 100:
            erros["nome_medico"] = "Use no máximo 100 caracteres."

        if not dados["crm"]:
            erros["crm"] = "Informe o CRM."
        elif len(dados["crm"]) > 30:
            erros["crm"] = "Use no máximo 30 caracteres."

        percentual = None
        try:
            percentual = converter_decimal(dados["percentual_honorario"])
        except ValueError:
            erros["percentual_honorario"] = "Informe um número, por exemplo 40 ou 37,5."
        else:
            if percentual is None:
                erros["percentual_honorario"] = "Informe o percentual."
            elif not Decimal(0) <= percentual <= Decimal(100):
                erros["percentual_honorario"] = "O percentual deve ficar entre 0 e 100."

        telefones = []
        for numero in dados["telefones"]:
            formatado = formatar_telefone(numero)
            if not formatado:
                erros["telefones"] = f"O telefone {numero} está incompleto. Use DDD e número."
            elif formatado not in telefones:
                telefones.append(formatado)

        existentes = {e["id_especialidade"] for e in self.especialidade_dao.listar()}
        especialidades = []
        for valor in dados["especialidades"]:
            try:
                id_especialidade = int(valor)
            except ValueError:
                continue
            if id_especialidade in existentes and id_especialidade not in especialidades:
                especialidades.append(id_especialidade)
        if not especialidades:
            erros["especialidades"] = "Marque pelo menos uma especialidade."

        horarios = self._validar_horarios(dados["horarios"], erros)

        if erros:
            raise ErroValidacao(erros)

        medico = {"nome_medico": dados["nome_medico"], "crm": dados["crm"], "percentual_honorario": percentual}
        return medico, telefones, especialidades, horarios

    def _validar_horarios(self, linhas, erros):
        horarios = []
        for linha in linhas:
            if linha["dia_semana"] not in DIAS_SEMANA:
                erros["horarios"] = "Escolha o dia da semana em todas as faixas de horário."
                continue
            try:
                inicio = converter_hora(linha["hora_inicio"])
                fim = converter_hora(linha["hora_fim"])
            except ValueError:
                erros["horarios"] = "Horário inválido."
                continue
            if not inicio or not fim:
                erros["horarios"] = "Informe início e fim em todas as faixas de horário."
                continue
            if inicio >= fim:
                erros["horarios"] = f"Uma faixa {no_dia(linha['dia_semana'])} termina antes de começar."
                continue
            horarios.append({"dia_semana": linha["dia_semana"], "hora_inicio": inicio, "hora_fim": fim})

        # faixas do mesmo dia não podem se sobrepor (08:00–12:00 e 11:00–14:00, por exemplo)
        horarios = ordenar_horarios(horarios)
        for anterior, atual in zip(horarios, horarios[1:]):
            if anterior["dia_semana"] == atual["dia_semana"] and atual["hora_inicio"] < anterior["hora_fim"]:
                erros["horarios"] = f"Há faixas de horário sobrepostas {no_dia(atual['dia_semana'])}."
        return horarios
