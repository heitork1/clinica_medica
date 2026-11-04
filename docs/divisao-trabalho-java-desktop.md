# Divisão do Trabalho: Clínica Médica em Java Desktop (2 programadores)

Este guia mostra como duas pessoas podem construir, do zero, o sistema da clínica em **Java puro com interface desktop (Swing)**, sem frameworks. Os requisitos são os do enunciado de Banco de Dados II: programação orientada a objetos, três camadas, inserção e consulta, e funções e gatilhos em PL/pgSQL.

Nomes usados abaixo: **Dev A** (banco, dados e regras) e **Dev B** (telas e fluxo de uso).

---

## 1. Tecnologias

| Item | Escolha | Motivo |
|---|---|---|
| Linguagem | Java 17 ou superior | Orientada a objetos, pedida no enunciado |
| Interface | **Swing** (já vem no JDK) | Não exige instalar nada. JavaFX também serve, mas precisa de módulo extra |
| Banco | PostgreSQL | Pedido no enunciado (PL/pgSQL) |
| Acesso ao banco | JDBC com o driver `postgresql` | É o "Java raiz": SQL escrito à mão, sem ORM |
| Build | Maven (só para baixar o driver e compilar) | Um `pom.xml` simples |
| Senhas | Hash com BCrypt (biblioteca `jbcrypt`) ou `PBKDF2` do próprio JDK | Nunca guardar senha em texto puro |

---

## 2. O que precisa existir

| Bloco | Conteúdo |
|---|---|
| **Banco** | DDL das tabelas, 4 gatilhos e funções em PL/pgSQL, dados de exemplo |
| **Modelo** | Classes que representam os dados: `Paciente`, `Medico`, `Consulta`, `Conta`, `Pagamento`, `Convenio`, `Especialidade`, `Sala`, `Procedimento`, `Horario`, `Usuario` |
| **Dados (DAO)** | Uma classe `...DAO` por entidade, falando com o banco por JDBC |
| **Negócio** | Validações, horários livres, conflito de agenda, atendimento, conta, pagamento e permissões por perfil |
| **Visão (telas)** | Janela de login, janela principal com menu, telas de cadastro, agenda, atendimento, conta e relatórios |
| **Transversal** | Usuário logado, tratamento de erros, mensagens ao usuário |

---

## 3. Estrutura do projeto

As três camadas do enunciado viram pacotes. A regra é a mesma de qualquer sistema em camadas: **cada pacote só usa o da camada logo abaixo**.

```
clinica-medica/
├── pom.xml
├── banco/
│   ├── 01-criar-tabelas.sql
│   ├── 02-usuario.sql
│   ├── 03-funcoes-gatilhos.sql
│   └── 04-dados-exemplo.sql
└── src/main/java/clinica/
    ├── Principal.java            # main(): abre a tela de login
    ├── modelo/                   # classes de dados (só atributos, getters e setters)
    │   ├── Paciente.java, Medico.java, Consulta.java, Conta.java ...
    │   └── Perfil.java           # enum: ADMIN, RECEPCAO, MEDICO
    ├── dados/                    # camada de dados (DAO)
    │   ├── Conexao.java          # abre a conexão e controla a transação
    │   └── PacienteDAO.java, MedicoDAO.java, ConsultaDAO.java ...
    ├── negocio/                  # camada de negócio
    │   ├── NegocioException.java # erro com mensagem pronta para o usuário
    │   ├── Sessao.java           # guarda o usuário logado
    │   └── PacienteServico.java, AgendaServico.java, FinanceiroServico.java ...
    └── visao/                    # camada de apresentação (Swing)
        ├── TelaLogin.java, TelaPrincipal.java
        ├── PacienteTela.java, MedicoTela.java, AgendaTela.java ...
        └── componentes/          # peças reaproveitadas (campo com máscara, tabela, etc.)
```

Fluxo de uma ação (por exemplo, salvar paciente):

```
PacienteTela  ──▶  PacienteServico  ──▶  PacienteDAO  ──▶  PostgreSQL
 (botão Salvar)    (valida e decide)     (INSERT via JDBC)
```

---

## 4. Fase 0: fazer juntos antes de dividir (1 a 2 dias)

Sem esta fase, um fica esperando o outro. O objetivo é definir o **contrato** entre as duas partes.

1. **Esquema do banco fechado.** Revisem o DDL juntos: tipos, chaves e `CHECK`s (status da consulta, dia da semana, forma de pagamento).
2. **Classes de modelo escritas.** São simples (atributos, construtor vazio, getters e setters). Uma vez escritas, as duas camadas as usam.
3. **Interfaces dos serviços escritas** (só as assinaturas, sem implementação). Exemplo:

```java
public interface PacienteServico {
    List<Paciente> listar(String busca);
    Paciente buscar(int id);
    int salvar(Paciente paciente) throws NegocioException;   // cria ou atualiza
    void excluir(int id) throws NegocioException;
}
```

4. **Padrão de erro:** toda regra violada vira `NegocioException("mensagem para o usuário")`. A tela só captura e mostra em `JOptionPane`. Mensagens de gatilho do banco (`RAISE EXCEPTION`) também viram `NegocioException`.
5. **Repositório Git** e acordo de branches: `main`, `dev-a`, `dev-b`.
6. **Banco de teste igual para os dois**, criado com os scripts da pasta `banco/`.

Com as interfaces prontas, o Dev B já consegue construir as telas usando uma implementação **falsa** (dados fixos em memória) enquanto o Dev A ainda não terminou o banco.

---

## 5. Quem faz o quê

### Dev A: banco, dados e regras (foco de Banco de Dados II)

| Etapa | Tarefas |
|---|---|
| **A1. Banco** | DDL completo, `CHECK`s, `UNIQUE`s, script de dados de exemplo |
| **A2. Conexão** | `Conexao.java`: abrir conexão e executar um bloco em transação (commit se deu certo, rollback se deu erro) |
| **A3. DAOs simples** | Convênio, especialidade, procedimento, sala |
| **A4. DAOs com tabelas filhas** | Paciente (telefones e planos de convênio), médico (telefones, especialidades, horários). Cada gravação é uma única transação |
| **A5. Agenda** | `ConsultaDAO`, cálculo de horários livres, detecção de conflito de médico, sala e paciente |
| **A6. Gatilhos** | Conflito de agenda, horário do médico, recálculo de procedimentos na conta, validação de pagamento |
| **A7. Atendimento e conta** | Registrar sintomas, diagnóstico, prescrição e procedimentos; criar a conta; registrar pagamentos com a parte do convênio e a do paciente |
| **A8. Segurança** | Hash da senha, `LoginServico`, regra de permissão por perfil |
| **A9. Relatórios** | Consultas SQL de resumo (consultas por médico, faturamento, contas em aberto) |

### Dev B: telas e fluxo de uso (foco de interface)

| Etapa | Tarefas |
|---|---|
| **B1. Base visual** | `TelaPrincipal` com menu (`JMenuBar` ou painel lateral), padrão de botões, fontes e cores, janela de mensagens |
| **B2. Login** | `TelaLogin`, uso de `Sessao`, menu que mostra só o que o perfil pode acessar |
| **B3. Componentes reaproveitáveis** | Campo com máscara (`JFormattedTextField` + `MaskFormatter` para CPF, telefone e data), campo de dinheiro, tabela com filtro, botões padrão |
| **B4. Telas de cadastro simples** | Uma tela serve para os 4 cadastros (tabela à esquerda, formulário à direita) |
| **B5. Pacientes e médicos** | Formulários com listas dinâmicas (telefones, convênios, especialidades, horários) e ficha do paciente |
| **B6. Agenda** | Tela de agendar (médico, data, horários livres em `JComboBox`), lista da agenda com filtros, mudança de status |
| **B7. Atendimento** | Tela de prontuário, adicionar procedimentos, total calculado na tela |
| **B8. Conta e pagamento** | Tela da conta, formulário de pagamento (dinheiro, cartão, PIX, convênio), saldo restante |
| **B9. Relatórios** | Tabelas e totais na tela |
| **B10. Validação na tela** | Campo obrigatório, tamanho, formato de e-mail, data válida, mensagens claras |

### Quem valida o quê

- **Dev B** valida o **formato** na tela (campo vazio, tamanho, CPF no formato certo).
- **Dev A** valida de novo **no serviço** tudo o que importa, porque a tela pode ser contornada, e as regras que dependem do banco (CPF duplicado, conflito de horário).
- Regra de ouro: **a tela nunca grava sem passar pelo serviço**, e o serviço nunca mostra janela.

---

## 6. Ordem de trabalho e dependências

| Semana | Dev A | Dev B | Entrega conjunta |
|---|---|---|---|
| 0 | Fase 0 juntos | Fase 0 juntos | Contrato (modelo, interfaces, banco) |
| 1 | A1, A2, A3 | B1, B2, B3 | Login funcionando e menu |
| 2 | A4 | B4, B5 | Cadastros completos |
| 3 | A5, A6 (parcial) | B6 | Agendar consulta |
| 4 | A6, A7 | B7, B8 | Atender e cobrar |
| 5 | A8, A9 | B9, B10 | Relatórios e permissões |
| 6 | Testes e dados de exemplo | Acabamento | Apresentação |

Quem terminar antes ajuda o outro. A semana 3 e a 4 são as mais pesadas para os dois.

---

## 7. Ponto crítico: a transação

Quando um paciente é salvo, o sistema grava o paciente, os telefones e os convênios. Se algo falhar no meio, **nada** pode ficar gravado. Em JDBC isso é:

```java
conexao.setAutoCommit(false);
try {
    // INSERT paciente
    // INSERT telefones
    // INSERT planos
    conexao.commit();
} catch (SQLException e) {
    conexao.rollback();
    throw e;
} finally {
    conexao.close();
}
```

Esse código deve existir **uma única vez**, em `Conexao.java`, e ser reaproveitado por todos os DAOs. O dono dele é o Dev A.

---

## 8. Regras para não se atrapalharem

1. **Arquivos separados:** o Dev A mexe em `dados/`, `negocio/` e `banco/`. O Dev B mexe em `visao/`. Quase não há conflito de merge.
2. **Alteração nos arquivos compartilhados** (`modelo/` e as interfaces dos serviços) só com aviso e acordo, porque quebra o código do outro.
3. **Merge toda semana** na branch `main`, e os dois rodam o fluxo completo: login, agendar, atender, cobrar.
4. **Commits pequenos** com mensagem clara ("Adiciona PacienteDAO", "Tela de agenda com filtro").
5. **Nunca versionar** senhas do banco. Use um arquivo `config.properties` fora do Git, com um `config.exemplo.properties` no repositório.
6. **Uma única classe `Conexao`**, e uma única classe `Sessao` para o usuário logado.

---

## 9. Checklist por pessoa

### Dev A
- [ ] Banco criado com todas as tabelas e `CHECK`s
- [ ] `Conexao` com transação
- [ ] DAOs de todas as entidades
- [ ] Gravações com tabelas filhas em uma transação só
- [ ] Horários livres e conflito de agenda
- [ ] Quatro gatilhos em PL/pgSQL
- [ ] Atendimento, conta e pagamento (convênio e paciente separados)
- [ ] Login com hash de senha e permissões por perfil
- [ ] Relatórios
- [ ] `dados-exemplo.sql` com um usuário de cada perfil

### Dev B
- [ ] Janela principal e menu por perfil
- [ ] Login
- [ ] Componentes: máscara, tabela com filtro, botões padrão
- [ ] Cadastros simples, pacientes e médicos
- [ ] Agenda e agendamento
- [ ] Atendimento e prontuário
- [ ] Conta e pagamento
- [ ] Relatórios
- [ ] Mensagens de erro claras em todas as telas
- [ ] Roteiro de demonstração: login, agendar, atender, cobrar

---

## 10. Dicas para a apresentação

- **Dev A** explica o banco, os gatilhos e a transação. Demonstre um gatilho barrando um erro (consulta em horário ocupado, pagamento acima do total).
- **Dev B** explica as telas e o fluxo de uso. Demonstre um perfil diferente de cada vez (o médico não vê o financeiro).
- Os dois explicam juntos o caminho `Tela → Serviço → DAO → Banco`, usando "salvar paciente" como exemplo.
