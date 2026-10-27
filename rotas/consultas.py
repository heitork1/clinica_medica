from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from negocio import ErroNegocio, ErroValidacao, formatar_moeda
from negocio.agenda import DURACAO_CONSULTA, STATUS, VERBOS_STATUS, ServicoAgenda, descrever_dia
from negocio.atendimento import ServicoAtendimento
from negocio.financeiro import FORMAS_PAGAMENTO, ServicoFinanceiro
from negocio.validacao import converter_data
from rotas.acesso import destino_seguro, exige_acesso, pode, usuario_logado

bp = Blueprint("consultas", __name__)
agenda_servico = ServicoAgenda()
atendimento_servico = ServicoAtendimento()
financeiro_servico = ServicoFinanceiro()


def ler_dia(texto):
    """Data da URL (?data=2026-10-27); hoje se vier vazia ou inválida."""
    try:
        return converter_data(texto) or date.today()
    except ValueError:
        return date.today()


@bp.route("/agenda")
@exige_acesso("agenda")
def agenda():
    usuario = usuario_logado()
    dia = ler_dia(request.args.get("data"))
    status = request.args.get("status") if request.args.get("status") in STATUS else None

    # o médico vê só a própria agenda, qualquer que seja o filtro na URL
    if usuario["perfil"] == "MEDICO":
        id_medico = usuario["id_medico"]
    else:
        id_medico = request.args.get("id_medico", type=int)

    consultas = agenda_servico.agenda_do_dia(dia, id_medico, status)
    return render_template(
        "consultas/agenda.html",
        consultas=consultas,
        dia=dia,
        titulo_dia=descrever_dia(dia),
        anterior=dia - timedelta(days=1),
        seguinte=dia + timedelta(days=1),
        hoje=date.today(),
        id_medico=id_medico,
        status=status,
        medicos=agenda_servico.medicos(),
        opcoes_status=STATUS,
        menu_ativo="agenda",
    )


@bp.route("/consultas/nova", methods=["GET", "POST"])
@exige_acesso("agendar")
def nova():
    dados = {"id_paciente": request.args.get("id_paciente", ""), "data": date.today().isoformat()}
    erros = {}

    if request.method == "POST":
        dados = request.form
        try:
            agenda_servico.agendar(request.form)
        except ErroValidacao as erro:
            erros = erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash(f"Consulta marcada para {converter_data(request.form['data']).strftime('%d/%m/%Y')} "
                  f"às {request.form['hora']}.", "sucesso")
            return redirect(url_for("consultas.agenda", data=request.form["data"]))

    return render_template("consultas/nova.html", dados=dados, erros=erros, hoje=date.today().isoformat(),
                           duracao_minutos=int(DURACAO_CONSULTA.total_seconds() // 60),
                           menu_ativo="agenda", **agenda_servico.opcoes_agendamento())


@bp.route("/consultas/horarios-livres")
@exige_acesso("agendar")
def horarios_livres():
    """Única rota JSON do sistema: usada por nova-consulta.js."""
    id_medico = request.args.get("id_medico", type=int)
    try:
        dia = converter_data(request.args.get("data"))
    except ValueError:
        dia = None
    if not id_medico or not dia:
        return jsonify({"horarios": [], "aviso": "Escolha o médico e a data."}), 400

    horarios = agenda_servico.horarios_livres(id_medico, dia)
    aviso = None
    if dia < date.today():
        aviso = "A data já passou."
    elif not horarios:
        aviso = "Nenhum horário livre: o médico não atende neste dia ou a agenda está cheia."
    return jsonify({"horarios": horarios, "aviso": aviso})


@bp.route("/consultas/<int:id_consulta>/status", methods=["POST"])
@exige_acesso("agendar")
def alterar_status(id_consulta):
    novo = request.form.get("status")
    try:
        consulta = agenda_servico.alterar_status(id_consulta, novo)
    except ErroNegocio as erro:
        flash(str(erro), "erro")
    else:
        flash(f"Consulta de {consulta['nome_paciente']} {VERBOS_STATUS[novo]}.", "sucesso")
    return redirect(destino_seguro(request.form.get("voltar") or url_for("consultas.agenda")))


@bp.route("/consultas/<int:id_consulta>/conta")
@exige_acesso("financeiro")
def conta(id_consulta):
    return pagina_conta(financeiro_servico.buscar(id_consulta) or abort(404))


def pagina_conta(consulta, dados=None, erros=None):
    """Página da conta; dados e erros vêm preenchidos quando o pagamento foi recusado."""
    if dados is None:
        # sugestão inicial: o saldo todo pelo paciente, ou com convênio se houver carteirinha válida
        saldo = consulta["conta"]["saldo"] if consulta["conta"] else 0
        dados = {
            "data_pagamento": date.today().isoformat(),
            "valor_pago": "%.2f" % saldo,
            "possui_convenio": "on" if consulta["convenios_validos"] else "",
            "valor_convenio": "",
            "forma_pagamento": "",
        }
    return render_template("consultas/conta.html", consulta=consulta, dados=dados, erros=erros or {},
                           formas=FORMAS_PAGAMENTO, hoje=date.today().isoformat(), menu_ativo="agenda")


@bp.route("/consultas/<int:id_consulta>/pagamentos", methods=["POST"])
@exige_acesso("financeiro")
def registrar_pagamento(id_consulta):
    consulta = financeiro_servico.buscar(id_consulta) or abort(404)
    try:
        dados = financeiro_servico.registrar_pagamento(consulta, request.form)
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        return pagina_conta(consulta, dados=request.form, erros=erro.erros)
    except ErroNegocio as erro:
        flash(str(erro), "erro")
        return pagina_conta(consulta, dados=request.form)

    total = dados["valor_pago"] + (dados["valor_convenio"] or 0)
    flash(f"Pagamento de {formatar_moeda(total)} registrado.", "sucesso")
    return redirect(url_for("consultas.conta", id_consulta=id_consulta))


@bp.route("/consultas/<int:id_consulta>/pagamentos/<int:id_pagamento>/excluir", methods=["POST"])
@exige_acesso("pagamentos_excluir")
def excluir_pagamento(id_consulta, id_pagamento):
    consulta = financeiro_servico.buscar(id_consulta) or abort(404)
    try:
        financeiro_servico.excluir_pagamento(consulta, id_pagamento)
    except ErroNegocio as erro:
        flash(str(erro), "erro")
    else:
        flash("Pagamento excluído.", "sucesso")
    return redirect(url_for("consultas.conta", id_consulta=id_consulta))


@bp.route("/consultas/<int:id_consulta>/atendimento", methods=["GET", "POST"])
@exige_acesso("prontuario")
def atendimento(id_consulta):
    usuario = usuario_logado()
    consulta = atendimento_servico.buscar(id_consulta) or abort(404)
    if not atendimento_servico.pode_ver(consulta, usuario):
        abort(403)
    pode_registrar = atendimento_servico.pode_registrar(consulta, usuario)

    erros = {}
    if request.method == "POST":
        if consulta["pago"] and atendimento_servico.eh_medico_da_consulta(consulta, usuario):
            flash("A conta desta consulta já tem pagamento: o atendimento não pode mais ser alterado.", "erro")
            return redirect(url_for("consultas.atendimento", id_consulta=id_consulta))
        if not pode_registrar:
            abort(403)
        dados = atendimento_servico.ler_formulario(request.form)
        try:
            conta = atendimento_servico.registrar(consulta, dados, usuario)
        except ErroValidacao as erro:
            erros = erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash(f"Atendimento de {consulta['nome_paciente']} registrado. "
                  f"Conta gerada: {formatar_moeda(conta['valor_total'])}.", "sucesso")
            return redirect(url_for("consultas.agenda", data=consulta["data_hora_marcado"].date().isoformat()))
    else:
        dados = {
            "data_hora_realizado": (consulta["data_hora_realizado"] or datetime.now()).strftime("%Y-%m-%dT%H:%M"),
            "sintomas": consulta["sintomas"] or "",
            "diagnostico": consulta["diagnostico"] or "",
            "prescricao": consulta["prescricao"] or "",
            "valor_consulta": "%.2f" % atendimento_servico.valor_padrao(consulta),
            "procedimentos": consulta["procedimentos"],
        }

    return render_template("consultas/atendimento.html", consulta=consulta, dados=dados, erros=erros,
                           pode_registrar=pode_registrar,
                           procedimentos=atendimento_servico.procedimentos_disponiveis(),
                           menu_ativo="agenda")
