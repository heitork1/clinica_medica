from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from negocio.agenda import ServicoAgenda, descrever_dia
from negocio.financeiro import ServicoFinanceiro
from rotas.acesso import exige_acesso, pode, usuario_logado

bp = Blueprint("inicio", __name__)
agenda_servico = ServicoAgenda()
financeiro_servico = ServicoFinanceiro()


def saudacao(agora):
    if agora.hour < 12:
        return "Bom dia"
    if agora.hour < 18:
        return "Boa tarde"
    return "Boa noite"


@bp.route("/")
@exige_acesso("inicio")
def inicio():
    usuario = usuario_logado()
    agora = datetime.now()
    hoje = date.today()

    # o médico vê a própria agenda; os demais perfis, a da clínica inteira
    id_medico = usuario["id_medico"] if usuario["perfil"] == "MEDICO" else None
    consultas = agenda_servico.agenda_do_dia(hoje, id_medico)
    proxima = next((c for c in consultas
                    if c["status"] in ("AGENDADA", "CONFIRMADA") and c["data_hora_marcado"] >= agora), None)

    return render_template(
        "inicio.html",
        saudacao=saudacao(agora),
        primeiro_nome=usuario["nome"].split()[0],
        titulo_dia=descrever_dia(hoje),
        hoje=hoje,
        consultas=consultas,
        proxima=proxima,
        contas_em_aberto=financeiro_servico.contas_em_aberto(8) if pode("financeiro") else [],
        menu_ativo="inicio",
    )


@bp.route("/estilo", methods=["GET", "POST"])
def estilo():
    """Vitrine dos componentes visuais. Só existe em modo de desenvolvimento."""
    if not current_app.debug:
        abort(404)

    if request.method == "POST":
        if request.form.get("acao") == "excluir":
            flash("Exclusão de demonstração confirmada.", "sucesso")
        else:
            nome = request.form.get("nome") or "sem nome"
            telefones = [t for t in request.form.getlist("telefone") if t]
            flash(f"Formulário recebido: {nome}, {len(telefones)} telefone(s).", "sucesso")
        return redirect(url_for("inicio.estilo"))

    return render_template("estilo.html")
