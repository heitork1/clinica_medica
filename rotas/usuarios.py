from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from negocio import ErroNegocio, ErroValidacao
from negocio.usuarios import ServicoUsuarios
from rotas.acesso import pode, usuario_logado

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")
servico = ServicoUsuarios()


@bp.before_request
def verificar_acesso():
    if not pode("usuarios"):
        abort(403)


@bp.route("/")
def lista():
    return render_template("usuarios/lista.html", usuarios=servico.listar(), menu_ativo="usuarios")


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    dados, erros = {}, {}
    if request.method == "POST":
        try:
            servico.criar(request.form)
        except ErroValidacao as erro:
            dados, erros = request.form, erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            dados = request.form
            flash(str(erro), "erro")
        else:
            flash(f"Usuário {request.form['nome'].strip()} cadastrado.", "sucesso")
            return redirect(url_for("usuarios.lista"))

    return render_template("usuarios/formulario.html", dados=dados, erros=erros, novo=True,
                           medicos=servico.medicos_para_vinculo(), menu_ativo="usuarios")


@bp.route("/<int:id_usuario>/editar", methods=["GET", "POST"])
def editar(id_usuario):
    usuario = servico.buscar(id_usuario) or abort(404)
    dados, erros = usuario, {}

    if request.method == "POST":
        logado = usuario_logado()
        try:
            servico.editar(id_usuario, request.form, logado["id_usuario"])
        except ErroValidacao as erro:
            dados, erros = request.form, erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            dados = request.form
            flash(str(erro), "erro")
        else:
            if id_usuario == logado["id_usuario"]:
                # mantém o nome mostrado no menu em dia
                session["usuario"] = {**logado, "nome": request.form["nome"].strip()}
            flash("Usuário atualizado.", "sucesso")
            return redirect(url_for("usuarios.lista"))

    return render_template("usuarios/formulario.html", dados=dados, erros=erros, novo=False, usuario=usuario,
                           medicos=servico.medicos_para_vinculo(usuario["id_medico"]), menu_ativo="usuarios")


@bp.route("/<int:id_usuario>/alternar-ativo", methods=["POST"])
def alternar_ativo(id_usuario):
    try:
        usuario = servico.alternar_ativo(id_usuario, usuario_logado()["id_usuario"])
    except ErroNegocio as erro:
        flash(str(erro), "erro")
    else:
        situacao = "reativado" if usuario["ativo"] else "desativado"
        flash(f"Usuário {usuario['nome']} {situacao}.", "sucesso")
    return redirect(url_for("usuarios.lista"))
