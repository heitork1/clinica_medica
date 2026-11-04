# Guia da Estrutura de Arquivos: como ler este projeto

Este guia explica **por que cada pasta existe**, **qual padrão os arquivos de dentro seguem** e **como ler o código sem se perder**. A ideia central: o projeto é repetitivo de propósito. Quem entende **um** módulo (por exemplo, pacientes) entende todos os outros.

---

## 1. A regra que explica quase tudo

Cada assunto do sistema (pacientes, médicos, usuários...) aparece **uma vez em cada camada**, com o mesmo nome:

| Assunto | Rota (Apresentação) | Serviço (Negócio) | DAO (Dados) | Tela (HTML) |
|---|---|---|---|---|
| Pacientes | `rotas/pacientes.py` | `negocio/pacientes.py` | `dados/paciente.py` | `templates/pacientes/` |
| Médicos | `rotas/medicos.py` | `negocio/medicos.py` | `dados/medico.py` | `templates/medicos/` |
| Usuários | `rotas/usuarios.py` | `negocio/usuarios.py` | `dados/usuario.py` | `templates/usuarios/` |
| Cadastros simples | `rotas/cadastros.py` | `negocio/cadastros.py` | `dados/cadastros.py` | `templates/cadastros/` |
| Consultas | `rotas/consultas.py` | `negocio/agenda.py`, `atendimento.py`, `financeiro.py` | `dados/consulta.py`, `financeiro.py` | `templates/consultas/` |
| Relatórios | `rotas/relatorios.py` | `negocio/relatorios.py` | `dados/relatorio.py` | `templates/relatorios.html` |

**Dica para achar qualquer coisa:** se você sabe o assunto, já sabe o nome do arquivo em cada pasta. Só preste atenção a um detalhe: nas rotas e no negócio o nome costuma ser plural (`pacientes.py`), e nos DAOs, singular (`paciente.py`).

---

## 2. O caminho de uma requisição

```
navegador ──▶ rotas/ ──▶ negocio/ ──▶ dados/ ──▶ PostgreSQL
    ▲            │
    └─ HTML ◀────┘  (templates/ + static/)
```

| Camada | Pergunta que ela responde | O que **nunca** faz |
|---|---|---|
| `rotas/` | "Chegou um pedido do navegador. O que eu faço com ele?" | SQL, regras de negócio |
| `negocio/` | "Esses dados são válidos? Posso fazer isso?" | HTML, SQL |
| `dados/` | "Como eu busco ou guardo isso no banco?" | Validar regras, mexer em telas |
| `templates/` | "Como eu mostro isso na tela?" | Acessar o banco |

Cada camada só conversa com a **vizinha**. A rota chama o serviço, o serviço chama o DAO. A rota nunca chama o DAO direto.

---

## 3. Como ler: a receita de 5 passos

Para entender **qualquer** funcionalidade, leia sempre nesta ordem:

1. **`app.py`**: a porta de entrada. Mostra quais módulos de rotas existem (`register_blueprint`).
2. **`rotas/<assunto>.py`**: veja as URLs (`@bp.route`) e o que cada uma faz.
3. **`negocio/<assunto>.py`**: veja as regras e validações que a rota chamou.
4. **`dados/<assunto>.py`**: veja o SQL que o serviço pediu.
5. **`templates/<assunto>/`**: veja a tela que mostra (ou recebe) os dados.

Em cada arquivo, leia **só os nomes dos métodos e a docstring** primeiro (o texto entre `"""` logo abaixo do `def`). Entre nos detalhes só do que precisar.

---

## 4. Pasta por pasta

### 4.1 Raiz do projeto

| Arquivo | Papel |
|---|---|
| `app.py` | Cria o Flask, registra as rotas, define filtros dos templates (como `data_br`) e comandos de terminal (`flask criar-admin`) |
| `config.py` | Lê o arquivo `.env` (banco, senha, chave secreta) |
| `.env` / `.env.exemplo` | Configurações do seu computador. O `.env.exemplo` é o modelo |
| `requirements.txt` | Bibliotecas Python a instalar (`pip install -r requirements.txt`) |
| `plano-dev.md` | Plano de desenvolvimento: decisões e fases |

### 4.2 `rotas/`: Apresentação (Flask)

**Padrão de todo arquivo:**

```python
bp = Blueprint("pacientes", __name__, url_prefix="/pacientes")   # 1. agrupa as URLs do assunto
servico = ServicoPacientes()                                      # 2. o serviço que ela usa

@bp.route("/")                          # 3. URL
@exige_acesso("pacientes")              # 4. quem pode entrar (perfil)
def lista():                            # 5. função da rota
    ...
    return render_template("pacientes/lista.html", ...)   # 6. devolve uma página
```

Como ler uma rota:
- **`@bp.route(...)`**: qual URL e quais métodos (`GET` abre a página, `POST` recebe um formulário).
- **`@exige_acesso("...")`**: qual perfil acessa. As áreas estão em `rotas/acesso.py`.
- **`render_template(...)`**: qual HTML mostrar e quais dados enviar a ele.
- **`flash(...)`**: mensagem de aviso na tela (sucesso ou erro).
- **`redirect(url_for(...))`**: depois de gravar, manda o navegador para outra página.

Arquivos especiais:
- `acesso.py`: tabela `ACESSO` com os perfis de cada área, mais `exige_acesso` e `exigir_login`.
- `autenticacao.py`: login, logout, troca de senha.
- `inicio.py`: página inicial.

### 4.3 `negocio/`: regras do sistema

**Padrão de todo arquivo:**

```python
class ServicoPacientes:

    def __init__(self):
        self.paciente_dao = PacienteDAO()      # o serviço guarda os DAOs de que precisa

    def listar(...)           # métodos públicos: a rota chama estes
    def buscar(...)
    def ler_formulario(...)   # transforma o formulário em dicionário
    def salvar(...)           # valida e grava
    def excluir(...)

    def _validar(...)         # método com "_" na frente = uso interno, só a própria classe chama
```

Padrões de nomes (se repetem em quase todos os serviços):

| Método | O que faz |
|---|---|
| `listar` | Devolve vários registros |
| `buscar` | Devolve um registro pelo id |
| `ler_formulario` | Organiza o que veio do `<form>` |
| `salvar` | Cria (sem id) ou atualiza (com id) |
| `excluir` | Apaga, com mensagem amigável se estiver em uso |
| `_validar` | Confere os campos e junta os erros num dicionário |

Erros: o serviço **lança** `ErroValidacao` (um erro por campo) ou `ErroNegocio` (mensagem geral). A rota **captura** esses erros e mostra na tela. Eles estão definidos em `negocio/__init__.py`.

Outros arquivos:
- `validacao.py`: funções soltas reaproveitadas (CPF, telefone, datas).
- `autenticacao.py`: login e hash de senha.

### 4.4 `dados/`: acesso ao banco (DAO)

DAO = *Data Access Object*: uma classe cujo único trabalho é falar com o banco.

**Padrão de todo arquivo:**

```python
from dados.conexao import conexao_banco

class SalaDAO:
    def listar(self):
        with conexao_banco() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT id_sala, descricao FROM sala ORDER BY id_sala")
            return cursor.fetchall()
```

Os quatro passos se repetem em **todo** método:
1. `with conexao_banco() ... as cursor`: abre a conexão (fecha sozinha no fim).
2. `cursor.execute("SQL", parâmetros)`: envia o comando.
3. `fetchone()` ou `fetchall()`: pega o resultado (se for SELECT).
4. `return`.

Nomes comuns: `listar`, `buscar_por_id`, `inserir`, `atualizar`, `excluir`.

Regras que você vai ver sempre:
- Valores vão por parâmetros (`%s` ou `%(nome)s`), nunca colados no texto do SQL (evita SQL injection).
- Cada linha volta como **dicionário** (`linha["nome"]`), por causa do `RealDictCursor`.
- `conexao.py` é o único arquivo que sabe como conectar. Os outros só o importam.

### 4.5 `templates/`: telas (Jinja)

**Estrutura:**
- `base.html`: o esqueleto com menu lateral. Quase toda página herda dele.
- `base-externa.html`: esqueleto sem menu (usado pelo login).
- `macros.html`: "funções de HTML" reaproveitadas (campo de formulário, cabeçalho da página...).
- `partes/`: trechos incluídos em vários lugares (avisos, scripts, estilos).
- Uma pasta por assunto (`pacientes/`, `medicos/`...), geralmente com `lista.html` e `formulario.html`.
- `erros/`: páginas de acesso negado (403) e não encontrado (404).

**Padrão de toda página:**

```html
{% extends "base.html" %}                                       <!-- 1. herda o esqueleto -->
{% from "macros.html" import cabecalho_pagina, campo %}          <!-- 2. traz as macros -->
{% block titulo %}Pacientes{% endblock %}                        <!-- 3. título da aba -->
{% block conteudo %}                                             <!-- 4. miolo da página -->
  {% for p in pacientes %} ... {{ p.nome }} ... {% endfor %}
{% endblock %}
```

Como ler: `{{ ... }}` mostra um valor, `{% ... %}` é lógica (`if`, `for`), `{# ... #}` é comentário.

### 4.6 `static/`: o que o navegador baixa direto

- `css/estilo.css`: o visual do sistema, sobre o Bootstrap.
- `img/`: logotipo.
- `js/`: comportamentos da página. Cada arquivo faz uma coisa:

| Arquivo | Faz |
|---|---|
| `comum.js` | Validação, janela de confirmação, evitar envio duplo |
| `mascaras.js` | Máscara de CPF, telefone e moeda |
| `linhas-dinamicas.js` | Botão "adicionar linha" (telefones, convênios, horários) |
| `filtro-tabela.js` | Campo "Filtrar" das tabelas |
| `nova-consulta.js`, `atendimento.js`, `pagamento.js` | Telas específicas |

**Padrão dos JavaScripts:** o HTML marca o elemento com um atributo `data-...`, e o JS procura esses atributos. Exemplo: `<input data-filtro-tabela="#tabela">` ativa o `filtro-tabela.js`. Para saber o que cada atributo faz, leia o **comentário no topo** do arquivo `.js`, que sempre explica.

### 4.7 `banco/`: SQL

Executar **nesta ordem** em um banco novo:

| Ordem | Arquivo | Conteúdo |
|---|---|---|
| 1 | `Trabalho1_ClinicaMedica.sql` | Cria as tabelas |
| 2 | `usuario.sql` | Cria a tabela de login |
| 3 | `funcoes-gatilhos.sql` | Funções e gatilhos em PL/pgSQL (regras no banco) |
| 4 | `dados-exemplo.sql` | Dados para demonstração (opcional) |

### 4.8 `docs/`

PDFs do enunciado, DER e modelo lógico, mais os guias em Markdown (como este).

---

## 5. Exemplo completo: "Excluir paciente"

| Passo | Arquivo | O que acontece |
|---|---|---|
| 1 | `templates/pacientes/ficha.html` | Botão "Excluir" dentro de um `<form method="post">` |
| 2 | `rotas/pacientes.py` | `excluir(id_paciente)` recebe o POST, confere o perfil (`pacientes_excluir`) e chama `servico.excluir(...)` |
| 3 | `negocio/pacientes.py` | `ServicoPacientes.excluir` confere se o paciente existe e chama o DAO. Se o banco recusar por haver consultas, traduz para uma mensagem amigável |
| 4 | `dados/paciente.py` | `PacienteDAO.excluir` executa o `DELETE` |
| 5 | de volta à rota | `flash("... excluído")` e `redirect` para a lista |

Treine: pegue outra ação (por exemplo, "Cadastrar sala") e refaça essa tabela sozinho, seguindo a receita da seção 3.

---

## 6. Perguntas comuns: onde procurar?

| Quero saber... | Olhe em... |
|---|---|
| Qual URL abre determinada tela? | `rotas/<assunto>.py` (`@bp.route`) |
| Quem pode acessar? | `rotas/acesso.py` (`ACESSO`) |
| Por que apareceu essa mensagem de erro? | `negocio/<assunto>.py` (`_validar`) ou `banco/funcoes-gatilhos.sql` (mensagens de gatilho) |
| Qual SQL roda quando faço isso? | `dados/<assunto>.py` |
| Como o campo é desenhado? | `templates/macros.html` |
| De onde vem a máscara do CPF? | `static/js/mascaras.js` |
| Como o menu decide o que mostrar? | `templates/base.html` com `pode("...")` |
| Que regras o banco garante sozinho? | `banco/funcoes-gatilhos.sql` |

---

## 7. Dicas de leitura

- **Comece pelas docstrings.** Quase todo arquivo e método começa com um texto entre `"""` que resume o que faz.
- **`_nome` com sublinhado** = método de uso interno. Pule na primeira leitura.
- **`or abort(404)`** (nas rotas) = "se não encontrou, mostre a página 404".
- **`with ... as ...`** = abre algo e garante que será fechado no fim.
- **`**dados`** = copia os itens de um dicionário para outro.
- **`menu_ativo="pacientes"`** (enviado aos templates) = só destaca o item do menu.
- **Estranhou um nome?** Procure onde ele é definido: o `import` no topo do arquivo diz de qual arquivo ele veio.
