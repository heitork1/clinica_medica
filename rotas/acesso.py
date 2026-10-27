from functools import wraps

from flask import abort, redirect, request, session, url_for

# Áreas do sistema e perfis que podem acessá-las (seção 6 do plano).
# É a única fonte dessa regra: usada pelas rotas e pelo menu em base.html.
TODOS = ("ADMIN", "RECEPCAO", "MEDICO")

ACESSO = {
    "inicio": TODOS,
    "agenda": TODOS,                          # MEDICO vê só as próprias consultas
    "agendar": ("ADMIN", "RECEPCAO"),         # marcar consulta e mudar status
    "pacientes": TODOS,                       # ver lista e ficha
    "pacientes_editar": ("ADMIN", "RECEPCAO"),
    "pacientes_excluir": ("ADMIN",),
    "prontuario": ("ADMIN", "MEDICO"),        # sintomas, diagnóstico e prescrição
    "medicos": ("ADMIN", "RECEPCAO"),         # ver lista
    "medicos_editar": ("ADMIN",),
    "financeiro": ("ADMIN", "RECEPCAO"),      # conta e pagamentos
    "pagamentos_excluir": ("ADMIN",),         # estornar pagamento lançado por engano
    "cadastros": ("ADMIN",),
    "usuarios": ("ADMIN",),
    "relatorios": ("ADMIN",),
}

# rotas que abrem sem login
ROTAS_PUBLICAS = {"autenticacao.login", "inicio.estilo", "static"}


def usuario_logado():
    return session.get("usuario")


def pode(area):
    usuario = usuario_logado()
    return bool(usuario) and usuario["perfil"] in ACESSO[area]


def exige_acesso(area):
    """Decorador de rota: responde 403 se o perfil logado não acessa a área."""
    def decorador(funcao):
        @wraps(funcao)
        def verificar(*args, **kwargs):
            if not pode(area):
                abort(403)
            return funcao(*args, **kwargs)
        return verificar
    return decorador


def exigir_login():
    """Registrado em app.before_request: toda rota exige login, menos as públicas.

    Quem não está logado vai para o login, que depois devolve à página pedida.
    """
    if request.endpoint is None or request.endpoint in ROTAS_PUBLICAS:
        return None
    if usuario_logado():
        return None

    proximo = request.full_path.rstrip("?") if request.method == "GET" else None
    return redirect(url_for("autenticacao.login", proximo=proximo))


def destino_seguro(endereco):
    """Só aceita endereços internos ("/agenda"), nunca outro site ("//site.com")."""
    # "/\site.com" também é tratado como outro site por alguns navegadores
    if endereco and endereco.startswith("/") and not endereco.startswith(("//", "/\\")):
        return endereco
    return url_for("inicio.inicio")
