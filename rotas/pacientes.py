from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from negocio import ErroNegocio, ErroValidacao
from negocio.pacientes import SEXOS, ServicoPacientes
from rotas.acesso import exige_acesso

bp = Blueprint("pacientes", __name__, url_prefix="/pacientes")
servico = ServicoPacientes()


@bp.route("/")
@exige_acesso("pacientes")
def lista():
    busca = request.args.get("busca", "").strip()
    pagina = request.args.get("pagina", 1, type=int)
    pacientes, total, paginas, pagina = servico.listar(busca, pagina)
    return render_template("pacientes/lista.html", pacientes=pacientes, total=total, busca=busca,
                           pagina=pagina, paginas=paginas, menu_ativo="pacientes")


@bp.route("/<int:id_paciente>")
@exige_acesso("pacientes")
def ficha(id_paciente):
    paciente = servico.buscar(id_paciente) or abort(404)
    return render_template("pacientes/ficha.html", paciente=paciente, consultas=servico.consultas(id_paciente),
                           menu_ativo="pacientes")


@bp.route("/novo", methods=["GET", "POST"])
@exige_acesso("pacientes_editar")
def novo():
    return formulario(None)


@bp.route("/<int:id_paciente>/editar", methods=["GET", "POST"])
@exige_acesso("pacientes_editar")
def editar(id_paciente):
    return formulario(servico.buscar(id_paciente) or abort(404))


def formulario(paciente):
    """Inclusão (paciente=None) e edição usam o mesmo template e o mesmo fluxo."""
    id_paciente = paciente["id_paciente"] if paciente else None
    dados = paciente or {"telefones": [], "convenios": []}
    erros = {}

    if request.method == "POST":
        dados = servico.ler_formulario(request.form)
        try:
            id_paciente = servico.salvar(dados, id_paciente)
        except ErroValidacao as erro:
            erros = erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash(f"Paciente {dados['nome']} {'atualizado' if paciente else 'cadastrado'}.", "sucesso")
            return redirect(url_for("pacientes.ficha", id_paciente=id_paciente))

    return render_template("pacientes/formulario.html", dados=dados, erros=erros, paciente=paciente,
                           convenios=servico.convenios_disponiveis(), opcoes_sexo=[(s, s) for s in SEXOS],
                           hoje=date.today().isoformat(), menu_ativo="pacientes")


@bp.route("/<int:id_paciente>/excluir", methods=["POST"])
@exige_acesso("pacientes_excluir")
def excluir(id_paciente):
    try:
        paciente = servico.excluir(id_paciente)
    except ErroNegocio as erro:
        flash(str(erro), "erro")
        return redirect(url_for("pacientes.ficha", id_paciente=id_paciente))
    flash(f"Paciente {paciente['nome']} excluído.", "sucesso")
    return redirect(url_for("pacientes.lista"))
