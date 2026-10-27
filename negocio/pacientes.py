from datetime import date

import psycopg2
from psycopg2 import errorcodes

from dados.cadastros import ConvenioDAO
from dados.paciente import PacienteDAO
from negocio import ErroNegocio, ErroValidacao, erro_do_banco
from negocio.validacao import (EMAIL_VALIDO, converter_data, cpf_valido, formatar_cpf, formatar_telefone,
                               somente_digitos)

SEXOS = ["Feminino", "Masculino", "Outro"]
POR_PAGINA = 20


class ServicoPacientes:

    def __init__(self):
        self.paciente_dao = PacienteDAO()
        self.convenio_dao = ConvenioDAO()

    def listar(self, busca="", pagina=1):
        """Devolve (pacientes da página, total encontrado, total de páginas, página mostrada)."""
        busca = (busca or "").strip()
        digitos = somente_digitos(busca)
        # só busca por CPF quando o texto digitado é praticamente só número
        if len(digitos) < 3 or len(digitos) < len(busca.replace(".", "").replace("-", "")):
            digitos = ""

        pagina = max(pagina, 1)
        pacientes, total = self.paciente_dao.listar(busca, digitos, POR_PAGINA, (pagina - 1) * POR_PAGINA)
        paginas = max((total + POR_PAGINA - 1) // POR_PAGINA, 1)
        if pagina > paginas:
            # endereço com página que não existe mais (ex.: depois de exclusões): mostra a última
            pagina = paginas
            pacientes, total = self.paciente_dao.listar(busca, digitos, POR_PAGINA, (pagina - 1) * POR_PAGINA)
        return pacientes, total, paginas, pagina

    def buscar(self, id_paciente):
        paciente = self.paciente_dao.buscar_por_id(id_paciente)
        if paciente:
            hoje = date.today()
            for plano in paciente["convenios"]:
                plano["vencido"] = bool(plano["validade"] and plano["validade"] < hoje)
        return paciente

    def consultas(self, id_paciente):
        return self.paciente_dao.listar_consultas(id_paciente)

    def convenios_disponiveis(self):
        return self.convenio_dao.listar()

    def ler_formulario(self, formulario):
        """Monta o paciente a partir do formulário, no mesmo formato de buscar().

        É o que volta para a tela quando há erro, para não perder o que foi digitado.
        """
        planos = []
        for id_convenio, carteirinha, validade, tipo in zip(
            formulario.getlist("id_convenio"),
            formulario.getlist("numero_carteirinha"),
            formulario.getlist("validade"),
            formulario.getlist("tipo_plano"),
        ):
            # linha totalmente vazia é ignorada (o usuário clicou em adicionar e não preencheu)
            if id_convenio or carteirinha.strip() or validade or tipo.strip():
                planos.append({
                    "id_convenio": id_convenio,
                    "numero_carteirinha": carteirinha.strip(),
                    "validade": validade,
                    "tipo_plano": tipo.strip(),
                })

        return {
            "nome": (formulario.get("nome") or "").strip(),
            "cpf": (formulario.get("cpf") or "").strip(),
            "rg": (formulario.get("rg") or "").strip(),
            "data_nasc": formulario.get("data_nasc") or "",
            "sexo": formulario.get("sexo") or "",
            "email": (formulario.get("email") or "").strip().lower(),
            "endereco": (formulario.get("endereco") or "").strip(),
            "telefones": [t.strip() for t in formulario.getlist("telefone") if t.strip()],
            "convenios": planos,
        }

    def salvar(self, dados, id_paciente=None):
        """Cria (sem id) ou atualiza. Devolve o id do paciente."""
        paciente, telefones, planos = self._validar(dados, id_paciente)
        try:
            if id_paciente:
                self.paciente_dao.atualizar(id_paciente, paciente, telefones, planos)
                return id_paciente
            return self.paciente_dao.inserir(paciente, telefones, planos)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro)

    def excluir(self, id_paciente):
        paciente = self.paciente_dao.buscar_por_id(id_paciente)
        if not paciente:
            raise ErroNegocio("Paciente não encontrado.")
        try:
            self.paciente_dao.excluir(id_paciente)
        except psycopg2.Error as erro:
            raise erro_do_banco(erro, {
                errorcodes.FOREIGN_KEY_VIOLATION:
                    f"Não é possível excluir {paciente['nome']}: o paciente tem consultas registradas.",
            })
        return paciente

    def _validar(self, dados, id_paciente):
        erros = {}

        if not dados["nome"]:
            erros["nome"] = "Informe o nome completo."
        elif len(dados["nome"]) > 100:
            erros["nome"] = "Use no máximo 100 caracteres."

        cpf = dados["cpf"]
        if not cpf_valido(cpf):
            erros["cpf"] = "Informe um CPF válido."
        else:
            cpf = formatar_cpf(cpf)
            if self.paciente_dao.cpf_em_uso(cpf, id_paciente):
                erros["cpf"] = "Já existe um paciente com este CPF."

        if len(dados["rg"]) > 20:
            erros["rg"] = "Use no máximo 20 caracteres."

        data_nasc = None
        try:
            data_nasc = converter_data(dados["data_nasc"])
        except ValueError:
            erros["data_nasc"] = "Data inválida."
        if data_nasc and not date(1900, 1, 1) <= data_nasc <= date.today():
            erros["data_nasc"] = "A data de nascimento não pode estar no futuro nem antes de 1900."

        if dados["sexo"] and dados["sexo"] not in SEXOS:
            erros["sexo"] = "Escolha uma opção da lista."

        if dados["email"] and (not EMAIL_VALIDO.match(dados["email"]) or len(dados["email"]) > 100):
            erros["email"] = "Informe um e-mail válido."

        if len(dados["endereco"]) > 200:
            erros["endereco"] = "Use no máximo 200 caracteres."

        telefones = []
        for numero in dados["telefones"]:
            formatado = formatar_telefone(numero)
            if not formatado:
                erros["telefones"] = f"O telefone {numero} está incompleto. Use DDD e número."
            elif formatado not in telefones:
                telefones.append(formatado)

        planos = self._validar_planos(dados["convenios"], erros)

        if erros:
            raise ErroValidacao(erros)

        paciente = {
            "nome": dados["nome"],
            "cpf": cpf,
            "rg": dados["rg"] or None,
            "data_nasc": data_nasc,
            "sexo": dados["sexo"] or None,
            "email": dados["email"] or None,
            "endereco": dados["endereco"] or None,
        }
        return paciente, telefones, planos

    def _validar_planos(self, planos, erros):
        existentes = {c["id_convenio"] for c in self.convenio_dao.listar()}
        validados, usados = [], set()

        for plano in planos:
            try:
                id_convenio = int(plano["id_convenio"])
            except (TypeError, ValueError):
                erros["convenios"] = "Escolha o convênio em todas as linhas preenchidas."
                continue
            if id_convenio not in existentes:
                erros["convenios"] = "Convênio não encontrado."
                continue
            if id_convenio in usados:
                erros["convenios"] = "O mesmo convênio aparece mais de uma vez."
                continue
            if not plano["numero_carteirinha"]:
                erros["convenios"] = "Informe o número da carteirinha de cada convênio."
                continue
            if len(plano["numero_carteirinha"]) > 50 or len(plano["tipo_plano"]) > 50:
                erros["convenios"] = "Carteirinha e tipo de plano aceitam no máximo 50 caracteres."
                continue
            try:
                validade = converter_data(plano["validade"])
            except ValueError:
                erros["convenios"] = "Validade da carteirinha inválida."
                continue

            usados.add(id_convenio)
            validados.append({
                "id_convenio": id_convenio,
                "numero_carteirinha": plano["numero_carteirinha"],
                "validade": validade,
                "tipo_plano": plano["tipo_plano"] or None,
            })
        return validados
