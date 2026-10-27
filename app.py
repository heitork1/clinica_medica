from datetime import date, datetime
from decimal import Decimal

import click
from flask import Flask, render_template

from config import Config
from dados.conexao import testar_conexao
from negocio import ErroNegocio, ErroValidacao, formatar_moeda
from negocio.autenticacao import PERFIS
from negocio.usuarios import ServicoUsuarios
from rotas.acesso import exigir_login, pode, usuario_logado
from rotas.autenticacao import bp as autenticacao_bp
from rotas.cadastros import bp as cadastros_bp
from rotas.consultas import bp as consultas_bp
from rotas.inicio import bp as inicio_bp
from rotas.medicos import bp as medicos_bp
from rotas.pacientes import bp as pacientes_bp
from rotas.relatorios import bp as relatorios_bp
from rotas.usuarios import bp as usuarios_bp

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(inicio_bp)
app.register_blueprint(autenticacao_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(cadastros_bp)
app.register_blueprint(pacientes_bp)
app.register_blueprint(medicos_bp)
app.register_blueprint(consultas_bp)
app.register_blueprint(relatorios_bp)

# todas as páginas exigem login, menos as listadas em rotas/acesso.py
app.before_request(exigir_login)


@app.context_processor
def variaveis_dos_templates():
    """Disponíveis em todos os templates: {% if pode("usuarios") %} ..."""
    return {"usuario_logado": usuario_logado(), "pode": pode, "PERFIS": PERFIS}


@app.errorhandler(403)
def acesso_negado(erro):
    return render_template("erros/acesso-negado.html"), 403


@app.errorhandler(404)
def nao_encontrado(erro):
    return render_template("erros/nao-encontrado.html"), 404


# ---------------------------------------------------------------------------
# Filtros de formatação usados nos templates: {{ paciente.data_nasc|data_br }}
# Aceitam tanto objetos date/datetime/time (vindos do banco) quanto texto ISO.
# ---------------------------------------------------------------------------

@app.template_filter("data_br")
def filtro_data_br(valor):
    if not valor:
        return ""
    if isinstance(valor, str):
        valor = date.fromisoformat(valor[:10])
    return valor.strftime("%d/%m/%Y")


@app.template_filter("hora")
def filtro_hora(valor):
    if not valor:
        return ""
    if isinstance(valor, str):
        return valor[:5]
    return valor.strftime("%H:%M")


@app.template_filter("data_hora")
def filtro_data_hora(valor):
    if not valor:
        return ""
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor)
    return valor.strftime("%d/%m/%Y %H:%M")


@app.template_filter("idade")
def filtro_idade(data_nasc):
    """Idade em anos completos na data de hoje."""
    if not data_nasc:
        return ""
    if isinstance(data_nasc, str):
        data_nasc = date.fromisoformat(data_nasc[:10])
    hoje = date.today()
    return hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))


@app.template_filter("decimal_br")
def filtro_decimal_br(valor):
    """Decimal('37.50') -> '37,5'; Decimal('40.00') -> '40'."""
    if valor is None or valor == "":
        return ""
    texto = f"{Decimal(str(valor)):.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


@app.template_filter("moeda")
def filtro_moeda(valor):
    return formatar_moeda(valor)


# ---------------------------------------------------------------------------
# Comandos de terminal: flask testar-banco, flask criar-admin
# ---------------------------------------------------------------------------

@app.cli.command("testar-banco")
def testar_banco():
    """Testa a conexão com o PostgreSQL configurado no .env."""
    try:
        versao = testar_conexao()
    except Exception as erro:
        click.echo(f"Não foi possível conectar ao banco: {erro}")
        raise SystemExit(1)
    click.echo(f"Conexão OK: {versao}")


@app.cli.command("criar-admin")
@click.option("--nome", prompt="Nome")
@click.option("--email", prompt="E-mail")
@click.option("--senha", prompt="Senha", hide_input=True, confirmation_prompt="Repita a senha")
def criar_admin(nome, email, senha):
    """Cria um usuário com perfil ADMIN (usado para o primeiro acesso)."""
    try:
        ServicoUsuarios().criar(
            {"nome": nome, "email": email, "perfil": "ADMIN", "senha": senha, "confirmacao_senha": senha}
        )
    except ErroValidacao as erro:
        for mensagem in erro.erros.values():
            click.echo(f"- {mensagem}")
        raise SystemExit(1)
    except ErroNegocio as erro:
        click.echo(str(erro))
        raise SystemExit(1)
    click.echo(f"Administrador {email} criado.")


if __name__ == "__main__":
    app.run()
