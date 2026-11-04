# Guia Didático de Arquitetura e Roteiro de Apresentação

Este documento serve como referência rápida para você estudar, entender e apresentar o projeto para a banca / professor das disciplinas de **Banco de Dados II** e **Análise e Desenvolvimento de Interfaces Web**.

---

## 1. Como o projeto cumpre os requisitos do professor

| Requisito do Professor | Onde está no projeto | Como explicar |
|---|---|---|
| **Linguagem Orientada a Objetos** | Python 3 | O sistema utiliza classes com atributos, métodos e encapsulamento em todas as camadas (`PacienteService`, `PacienteDAO`, etc.). |
| **Arquitetura em Três Camadas** | `rotas/` (Apresentação)<br>`negocio/` (Negócio)<br>`dados/` (Dados) | Cada camada possui uma responsabilidade única e isolada: a Apresentação nunca acessa o banco diretamente, e o Banco nunca renderiza telas. |
| **Inserção e Consulta** | Todas as telas de cadastro e listagem | Operações de `INSERT` e `SELECT` executadas com segurança via parâmetros `%s` contra SQL Injection. |
| **Gatilhos e Funções (Etapa 3 de BD)** | `banco/funcoes-gatilhos.sql` | 4 gatilhos que garantem integridade referencial, conflito de horários e regras financeiras no PostgreSQL. |

---

## 2. O Fluxo das 3 Camadas no Código (Exemplo: Paciente)

Se o professor pedir: *"Me mostre como um paciente é cadastrado no sistema do início ao fim"*, siga estes 3 passos:

```
[ NAVEGADOR ]
      │ (1) Envia formulário via POST
      ▼
[ CAMADA 1: APRESENTAÇÃO ]  -> rotas/pacientes.py
      │  Função: novo() / formulario()
      │  A rota extrai os dados do formulário: dados = servico.ler_formulario(request.form)
      │  E delega para a camada de negócio: servico.salvar(dados)
      ▼
[ CAMADA 2: NEGÓCIO ]       -> negocio/pacientes.py
      │  Classe: ServicoPacientes
      │  Método: salvar() -> chama _validar()
      │  Valida se o CPF é válido, se o nome foi preenchido e se o e-mail é válido.
      │  Chama a camada de dados: self.paciente_dao.inserir(paciente, telefones, planos)
      ▼
[ CAMADA 3: DADOS ]         -> dados/paciente.py
      │  Classe: PacienteDAO
      │  Método: inserir()
      │  Abre a transação com conexao_banco() e executa o SQL puro:
      │  INSERT INTO paciente (nome, cpf, ...) VALUES (%s, %s, ...) RETURNING id_paciente
      ▼
[ BANCO DE DADOS ]          -> PostgreSQL grava os dados e garante integridade
```

---

## 3. Os 4 Gatilhos de Banco de Dados (`banco/funcoes-gatilhos.sql`)

| # | Nome do Gatilho | Tabela | Tipo | Explicação Simples |
|---|---|---|---|---|
| **1** | `trg_valida_conflito_agenda` | `consulta` | `BEFORE INSERT OR UPDATE` | Impede que o mesmo **médico** ou a mesma **sala** tenham duas consultas marcadas no mesmo dia e horário. |
| **2** | `trg_valida_horario_medico` | `consulta` | `BEFORE INSERT OR UPDATE` | Impede que uma consulta seja marcada em um dia ou horário em que o médico **não atende** (compara com `horario_medico`). |
| **3** | `trg_atualiza_valor_procedimento_conta` | `consulta_procedimento` | `AFTER INSERT OR UPDATE OR DELETE` | Sempre que um procedimento é adicionado ou removido, calcula `quantidade * valor` e atualiza automaticamente o campo `valor_procedimento` da tabela `conta`. |
| **4** | `trg_valida_pagamento` | `pagamento` | `BEFORE INSERT OR UPDATE` | Impede valores negativos e bloqueia pagamentos que, somados aos anteriores, **ultrapassem o valor total da conta**. |

---

## 4. Roteiro Passo a Passo para Apresentação Prática

Siga esta sequência durante a demonstração para o professor:

### Passo 1: Autenticação e Perfis (Segurança)
1. Acesse o sistema e mostre a tela de login.
2. Explique que o sistema possui 3 perfis de acesso:
   * **Administrador (`ADMIN`):** acesso a tudo.
   * **Recepção (`RECEPCAO`):** pacientes, agenda e cobrança.
   * **Médico (`MEDICO`):** vê apenas as próprias consultas e preenche prontuário.
3. Entre com o usuário administrador.

### Passo 2: Cadastros Básicos (Camada de Dados e DAO)
1. Mostre o menu **Cadastros** (Salas, Especialidades, Convênios e Procedimentos).
2. Mostre que o código em [`dados/cadastros.py`](file:///c:/github/clinica_medica/dados/cadastros.py) implementa classes DAO com comandos SQL diretos (`SELECT`, `INSERT`, `UPDATE`, `DELETE`).
3. Cadastre uma Especialidade (ex: *Cardiologia*) e um Procedimento (ex: *Eletrocardiograma - R$ 150,00*).

### Passo 3: Cadastro de Médico e Grade Semanal
1. Abra **Médicos ➡️ Novo Médico**.
2. Preencha nome, CRM, percentual de honorários, telefones e marque a especialidade.
3. Adicione uma faixa de horário (ex: *Segunda-feira das 08:00 às 12:00*).
4. Explique que isso alimenta a tabela `horario_medico`, usada pelo **Gatilho 2** para validar agendamentos.

### Passo 4: Cadastro de Paciente
1. Abra **Pacientes ➡️ Novo Paciente**.
2. Mostre a validação de CPF e preenchimento de convênio.
3. Salve e mostre a ficha do paciente com o histórico.

### Passo 5: Agendamento e Teste dos Gatilhos 1 e 2
1. Abra a **Agenda ➡️ Nova Consulta**.
2. Escolha o paciente, o médico e a sala.
3. **Demonstração do Gatilho 2:** Tente agendar em um horário fora do expediente do médico (ex: Terça-feira). Mostre a mensagem de bloqueio vinda do gatilho.
4. Agende no horário correto (Segunda-feira 08:00).
5. **Demonstração do Gatilho 1:** Tente agendar outra consulta para o mesmo médico ou mesma sala na Segunda-feira 08:00. O banco rejeitará por conflito de horário.

### Passo 6: Atendimento Médico e Teste do Gatilho 3
1. Acesse a consulta agendada e clique em **Atender**.
2. Preencha os sintomas, diagnóstico e adicione o procedimento cadastrado.
3. Finalize o atendimento: a consulta passa para `REALIZADA`.
4. Mostre que o **Gatilho 3** calculou automaticamente o valor do procedimento na conta gerada.

### Passo 7: Financeiro e Teste do Gatilho 4
1. Abra a **Conta da Consulta**.
2. Mostre o valor da consulta + procedimentos e o saldo devedor.
3. **Demonstração do Gatilho 4:** Tente lançar um pagamento com valor maior que o saldo da conta (ex: R$ 5.000,00). O gatilho bloqueará a gravação.
4. Lance o pagamento com o valor exato para quitar a conta.

---

## 5. Estrutura de Pastas Resumida

```
clinica_medica/
├── banco/
│   ├── Trabalho1_ClinicaMedica.sql   # DDL: Criação das tabelas
│   ├── usuario.sql                   # DDL: Tabela de usuários e perfis
│   └── funcoes-gatilhos.sql          # Etapa 3: Os 4 gatilhos e funções em PL/pgSQL
├── dados/                            # CAMADA 3: DAOs com comandos SQL puros
│   ├── conexao.py                    # Gerenciador de conexão com o PostgreSQL
│   ├── paciente.py                   # PacienteDAO
│   ├── medico.py                     # MedicoDAO
│   ├── consulta.py                   # ConsultaDAO
│   ├── cadastros.py                  # DAOs de Convênio, Especialidade, Procedimento e Sala
│   ├── financeiro.py                 # FinanceiroDAO (Contas e Pagamentos)
│   └── usuario.py                    # UsuarioDAO
├── negocio/                          # CAMADA 2: Regras de negócio e validações (POO)
│   ├── pacientes.py                  # ServicoPacientes
│   ├── medicos.py                    # ServicoMedicos
│   ├── agenda.py                     # ServicoAgenda
│   ├── cadastros.py                  # ServicoCadastros
│   ├── financeiro.py                 # ServicoFinanceiro
│   └── usuarios.py                   # ServicoUsuarios
├── rotas/                            # CAMADA 1: Controladores Flask
│   ├── pacientes.py                  # Rotas de pacientes
│   ├── medicos.py                    # Rotas de médicos
│   ├── consultas.py                  # Rotas de agenda e atendimento
│   └── cadastros.py                  # Rotas de cadastros simples
└── templates/                        # CAMADA 1: Telas HTML (Jinja)
    ├── pacientes/                    # Telas de paciente
    ├── medicos/                      # Telas de médico
    ├── consultas/                    # Telas de agenda, atendimento e conta
    └── cadastros/                    # Telas de cadastros simples
```

