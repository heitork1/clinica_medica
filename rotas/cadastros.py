from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from negocio import ErroNegocio, ErroValidacao
from negocio.cadastros import ServicoCadastros
from rotas.acesso import pode

bp = Blueprint("cadastros", __name__, url_prefix="/cadastros")
servico = ServicoCadastros()


@bp.before_request
def verificar_acesso():
    if not pode("cadastros"):
        abort(403)


@bp.route("/<tipo>", methods=["GET", "POST"])
def lista(tipo):
    """Tabela com os registros e, ao lado, o formulário de inclusão ou edição.

    GET  /cadastros/salas            -> formulário vazio (nova sala)
    GET  /cadastros/salas?editar=3   -> formulário com a sala 3
    POST /cadastros/salas            -> grava; o campo oculto "id" indica edição
    """
    cadastro = servico.obter(tipo) or abort(404)
    dados, erros = {}, {}
    id_edicao = request.args.get("editar", type=int)

    if request.method == "POST":
        id_edicao = request.form.get("id", type=int)
        try:
            gravado = servico.salvar(tipo, request.form, id_edicao)
        except ErroValidacao as erro:
            dados, erros = request.form, erro.erros
            flash(str(erro), "erro")
        except ErroNegocio as erro:
            dados = request.form
            flash(str(erro), "erro")
        else:
            acao = "atualizad" if id_edicao else "cadastrad"
            flash(f'{cadastro.singular.capitalize()} "{cadastro.descrever(gravado)}" {acao}{cadastro.artigo}.', "sucesso")
            return redirect(url_for("cadastros.lista", tipo=tipo))
    elif id_edicao:
        dados = servico.buscar(tipo, id_edicao) or abort(404)

    return render_template(
        "cadastros/lista.html",
        tipo=tipo,
        cadastro=cadastro,
        registros=servico.listar(tipo),
        dados=dados,
        erros=erros,
        id_edicao=id_edicao,
        menu_ativo=tipo,
    )


@bp.route("/<tipo>/<int:id_registro>/excluir", methods=["POST"])
def excluir(tipo, id_registro):
    cadastro = servico.obter(tipo) or abort(404)
    try:
        registro = servico.excluir(tipo, id_registro)
    except ErroNegocio as erro:
        flash(str(erro), "erro")
    else:
        flash(f'{cadastro.singular.capitalize()} "{cadastro.descrever(registro)}" excluíd{cadastro.artigo}.', "sucesso")
    return redirect(url_for("cadastros.lista", tipo=tipo))
