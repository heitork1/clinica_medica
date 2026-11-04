# Sistema de Controle de Clínica Médica

Sistema web para uma clínica médica de pequeno porte: pacientes, médicos, agenda de consultas, atendimento com prontuário, contas e pagamentos. Trabalho prático integrado das disciplinas de **Banco de Dados II** e **Análise e Desenvolvimento de Interfaces Web**.

O planejamento e o andamento de cada fase estão em [plano-dev.md](plano-dev.md).

---

## Tecnologias

- **Linguagem:** Python 3 (Orientado a Objetos)
- **Framework Web:** Flask (com Jinja Templates)
- **Banco de Dados:** PostgreSQL (com driver `psycopg2`)
- **Front-end:** HTML5, CSS3, JavaScript e Bootstrap 5.3 via CDN

---

## Arquitetura em Três Camadas (POO)

O projeto segue rigorosamente o padrão arquitetural em **Três Camadas**, com divisão clara de responsabilidades:

```
[ Camada 1: APRESENTAÇÃO ]  -> rotas/ e templates/ (Flask + HTML/Jinja)
       │
       ▼
[ Camada 2: NEGÓCIO ]       -> negocio/ (Classes de serviço, regras e validações)
       │
       ▼
[ Camada 3: DADOS ]         -> dados/ (Classes DAO com SQL puro) e banco/
       │
       ▼
[ BANCO DE DADOS ]          -> PostgreSQL
```

| Camada | Pastas | Responsabilidade |
|---|---|---|
| **1. Apresentação** | `rotas/`, `templates/`, `static/` | Recebe as requisições HTTP, valida os parâmetros de entrada e renderiza as páginas para o usuário. |
| **2. Negócio** | `negocio/` | Classes de serviço (`ServicoPacientes`, `ServicoMedicos`, `ServicoAgenda`, etc.) contendo regras de negócio, validações de dados e permissões. |
| **3. Dados (DAO)** | `dados/`, `banco/` | Classes DAO (`PacienteDAO`, `MedicoDAO`, `ConsultaDAO`, etc.) responsáveis pelo acesso direto ao banco de dados com comandos SQL puros e seguros (`%s`). |

---

## Gatilhos e Funções no Banco (Etapa 3 - Banco de Dados II)

O arquivo [`banco/funcoes-gatilhos.sql`](banco/funcoes-gatilhos.sql) implementa **4 gatilhos essenciais** em PL/pgSQL que garantem a integridade das regras no PostgreSQL:

1. **`trg_valida_conflito_agenda` (Tabela `consulta`):** Impede que um médico ou uma sala tenham duas consultas marcadas no mesmo dia e horário.
2. **`trg_valida_horario_medico` (Tabela `consulta`):** Garante que a consulta seja marcada apenas dentro do expediente e dias de atendimento do médico (`horario_medico`).
3. **`trg_atualiza_valor_procedimento_conta` (Tabela `consulta_procedimento`):** Recalcula automaticamente o total de procedimentos na tabela `conta` sempre que itens são inseridos, alterados ou removidos.
4. **`trg_valida_pagamento` (Tabela `pagamento`):** Impede pagamentos com valores negativos e bloqueia pagamentos que ultrapassem o valor total da conta.

---

## Como rodar o projeto

### 1. Pré-requisitos
* Python 3.11 ou superior instalado
* PostgreSQL instalado e em execução

### 2. Ambiente virtual e dependências
No terminal, na pasta raiz do projeto:

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar no Windows (PowerShell):
venv\Scripts\Activate.ps1

# Ou ativar no Linux / macOS:
source venv/bin/activate

# Instalar as dependências:
pip install -r requirements.txt
```

### 3. Banco de dados
Crie o banco de dados `clinica_medica` e execute os scripts SQL na seguinte ordem:

```bash
createdb -U postgres clinica_medica
psql -U postgres -d clinica_medica -f banco/Trabalho1_ClinicaMedica.sql
psql -U postgres -d clinica_medica -f banco/usuario.sql
psql -U postgres -d clinica_medica -f banco/funcoes-gatilhos.sql
```

### 4. Configuração das variáveis de ambiente
Copie o arquivo `.env.exemplo` para `.env` e configure a senha do PostgreSQL e a `SECRET_KEY`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clinica_medica
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui
SECRET_KEY=chave_secreta_para_sessao
FLASK_DEBUG=1
```

### 5. Testar conexão e criar o primeiro Administrador

```bash
# Testa a conexão com o PostgreSQL:
flask testar-banco

# Cria o usuário ADMIN interativamente (informe nome, e-mail e senha):
flask criar-admin
```

*(Opcional) Criação direta sem perguntas:*
```bash
flask criar-admin --nome "Administrador" --email admin@clinica.com --senha segredo1
```

### 6. Executar o servidor web

```bash
flask run
```

Acesse no navegador: **http://127.0.0.1:5000**

---

## Perfis de Acesso

| Perfil | Acesso no Sistema |
|---|---|
| **Administrador (`ADMIN`)** | Acesso completo: gerencia usuários, médicos, pacientes, agenda, cadastros e relatórios. |
| **Recepção (`RECEPCAO`)** | Acesso operacional: gerencia pacientes, agenda consultas e lança pagamentos. |
| **Médico (`MEDICO`)** | Acesso clínico: visualiza a própria agenda e preenche o prontuário das próprias consultas. |

---

## Roteiro de Demonstração

Para um roteiro detalhado de 7 passos demonstrando todo o fluxo do sistema e o acionamento de cada um dos 4 gatilhos ao vivo para o professor, consulte:
👉 **[docs/roteiro-apresentacao-didatico.md](docs/roteiro-apresentacao-didatico.md)**
