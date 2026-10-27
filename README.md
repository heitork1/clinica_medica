# Sistema de Controle de Clínica Médica

Sistema web para uma clínica médica de pequeno porte: pacientes, médicos, agenda de consultas, prontuário, contas e pagamentos. Trabalho prático integrado das disciplinas de **Banco de Dados II** e **Análise e Desenvolvimento de Interfaces Web**.

O planejamento e o andamento de cada fase estão em [plano-dev.md](plano-dev.md).

## Tecnologias

- Python 3 e Flask
- PostgreSQL (psycopg2)
- HTML, CSS e JavaScript, com Bootstrap 5.3 e Bootstrap Icons via CDN

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `banco/` | script de criação do banco, funções e gatilhos |
| `docs/` | enunciado, DER e modelo lógico |
| `dados/` | camada de dados: conexão e DAOs |
| `negocio/` | regras de negócio |
| `rotas/` | rotas Flask (um blueprint por área) |
| `templates/` | páginas HTML (Jinja) |
| `static/` | CSS, JavaScript e imagens |

## Como rodar

1. Instale o Python 3.11 ou mais novo e o PostgreSQL.

2. Crie e ative um ambiente virtual na pasta do projeto:

   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   # Linux / macOS
   source .venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

4. Crie o banco, as tabelas e os gatilhos (a tabela de usuários fica em um arquivo separado):

   ```bash
   createdb -U postgres clinica_medica
   psql -U postgres -d clinica_medica -f banco/Trabalho1_ClinicaMedica.sql
   psql -U postgres -d clinica_medica -f banco/usuario.sql
   psql -U postgres -d clinica_medica -f banco/funcoes-gatilhos.sql
   ```

5. Copie `.env.exemplo` para `.env` e preencha a senha do PostgreSQL e a `SECRET_KEY`.

6. Teste a conexão e crie o primeiro administrador (o comando pede nome, e-mail e senha):

   ```bash
   flask testar-banco
   flask criar-admin
   ```

7. Suba o servidor e entre com o administrador criado:

   ```bash
   flask run
   ```

   Acesse http://127.0.0.1:5000. Com `FLASK_DEBUG=1` no `.env`, a página http://127.0.0.1:5000/estilo mostra todos os componentes visuais do sistema.

## Criar usuários

Os comandos abaixo rodam na pasta do projeto, com o ambiente virtual ativado e o `.env` preenchido.

### Administrador (pelo terminal)

O comando pergunta o nome, o e-mail e a senha, e pede a senha duas vezes:

```bash
flask criar-admin
```

Para criar sem as perguntas, passe tudo nas opções:

```bash
flask criar-admin --nome "Administrador" --email admin@clinica.com --senha segredo1
```

A senha precisa ter pelo menos 6 caracteres, e o e-mail não pode estar em uso por outro usuário. O comando pode ser repetido para criar mais administradores.

### Recepção e médico (pela interface)

Não há comando de terminal para esses perfis. Um administrador os cria no sistema:

1. Entre com um administrador e abra **Administração → Usuários → Novo usuário**.
2. Preencha nome, e-mail, perfil e senha.
3. No perfil **Médico**, escolha também o cadastro de médico ao qual o usuário corresponde. Por isso, o médico precisa estar cadastrado em **Médicos** antes. Cada médico pode ter apenas um usuário.

Na mesma tela dá para editar um usuário, trocar a senha dele e desativá-lo. Um usuário desativado não consegue entrar.

## Perfis de acesso

| Perfil | Acesso |
|---|---|
| Administrador | tudo, inclusive usuários, cadastros e relatórios |
| Recepção | pacientes, agenda, médicos (consulta) e pagamentos |
| Médico | a própria agenda e o prontuário das próprias consultas |
