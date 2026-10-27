from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from negocio import ErroNegocio, ErroValidacao
from negocio.autenticacao import ServicoAutenticacao
from rotas.acesso import destino_seguro, usuario_logado

bp = Blueprint("autenticacao", __name__)
servico = ServicoAutenticacao()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if usuario_logado():
        return redirect(url_for("inicio.inicio"))

    email = ""
    if request.method == "POST":
        email = request.form.get("email", "")
        try:
            usuario = servico.entrar(email, request.form.get("senha", ""))
        except ErroNegocio as erro:
            flash(str(erro), "erro")
        else:
            session.clear()
            session["usuario"] = usuario
            session.permanent = True
            return redirect(destino_seguro(request.args.get("proximo")))

    return render_template("login.html", email=email)


@bp.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("autenticacao.login"))


@bp.route("/minha-senha", methods=["GET", "POST"])
def minha_senha():
    erros = {}
    if request.method == "POST":
        try:
            servico.trocar_senha(
                usuario_logado()["id_usuario"],
                request.form.get("senha_atual"),
                request.form.get("nova_senha"),
                request.form.get("confirmacao_senha"),
            )
        except ErroValidacao as erro:
            erros = erro.erros
            flash(str(erro), "erro")
        else:
            flash("Senha alterada.", "sucesso")
            return redirect(url_for("inicio.inicio"))

    return render_template("minha-senha.html", erros=erros)
