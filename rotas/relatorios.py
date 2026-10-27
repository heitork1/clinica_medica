from flask import Blueprint, flash, render_template, request

from negocio import ErroNegocio
from negocio.relatorios import ServicoRelatorios, periodos_rapidos
from rotas.acesso import exige_acesso

bp = Blueprint("relatorios", __name__)
servico = ServicoRelatorios()


@bp.route("/relatorios")
@exige_acesso("relatorios")
def resumo():
    try:
        inicio, fim = servico.ler_periodo(request.args.get("inicio"), request.args.get("fim"))
    except ErroNegocio as erro:
        flash(str(erro), "erro")
        inicio, fim = servico.ler_periodo(None, None)

    return render_template("relatorios.html", inicio=inicio, fim=fim, periodos=periodos_rapidos(),
                           menu_ativo="relatorios", **servico.gerar(inicio, fim))
