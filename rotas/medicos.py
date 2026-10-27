from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from negocio import ErroNegocio, ErroValidacao
from negocio.medicos import DIAS_SEMANA, ServicoMedicos
from rotas.acesso import exige_acesso

bp = Blueprint("medicos", __name__, url_prefix="/medicos")
servico = ServicoMedicos()


@bp.route("/")
@exige_acesso("medicos")
def lista():
    id_especialidade = request.args.get("id_especialidade", type=int)
    return render_template("medicos/lista.html", medicos=servico.listar(id_especialidade),
                           especialidades=servico.especialidades(), id_especialidade=id_especialidade,
                           menu_ativo="medicos")


@bp.route("/novo", methods=["GET", "POST"])
@exige_acesso("medicos_editar")
def novo():
    return formulario(None)


@bp.route("/<int:id_medico>/editar", methods=["GET", "POST"])
@exige_acesso("medicos_editar")
def editar(id_medico):
    return formulario(servico.buscar(id_medico) or abort(404))


def formulario(medico):
    id_medico = medico["id_medico"] if medico else None
    dados = medico or {"telefones": [], "especialidades": [], "horarios": []}
    erros = {}

    if request.method == "POST":
        dados = servico.ler_formulario(request.form)
        try:
            servico.salvar(dados, id_medico)
        except ErroValidacao as erro:
            erros = erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash(f"Médico {dados['nome_medico']} {'atualizado' if medico else 'cadastrado'}.", "sucesso")
            return redirect(url_for("medicos.lista"))

    return render_template("medicos/formulario.html", dados=dados, erros=erros, medico=medico,
                           especialidades=servico.especialidades(), dias_semana=DIAS_SEMANA,
                           menu_ativo="medicos")


@bp.route("/<int:id_medico>/excluir", methods=["POST"])
@exige_acesso("medicos_editar")
def excluir(id_medico):
    try:
        medico = servico.excluir(id_medico)
    except ErroNegocio as erro:
        flash(str(erro), "erro")
    else:
        flash(f"Médico {medico['nome_medico']} excluído.", "sucesso")
    return redirect(url_for("medicos.lista"))
