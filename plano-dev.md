# Plano de desenvolvimento — Sistema de Controle de Clínica Médica

Sistema web para uma clínica médica de pequeno porte: pacientes, médicos, agenda de consultas, prontuário, contas e pagamentos. O mesmo sistema atende a duas disciplinas:

- **Banco de Dados II:** projeto conceitual e lógico, DDL em PostgreSQL, funções e gatilhos em PL/pgSQL, camada de acesso a dados;
- **Análise e Desenvolvimento de Interfaces Web:** interface em HTML, CSS e JavaScript, rotas Flask e regras de apresentação.

Documentos de referência, em `docs/`: enunciado (`TEMA 2- SISTEMA DE CONTROLE DE CLÍNICA MÉDICA-1.pdf`), DER (`diagramaP1T1.pdf`) e modelo lógico (`modeloLogico_Clinica.pdf`). Script de criação: `banco/Trabalho1_ClinicaMedica.sql`.

---

## Andamento

| Fase | Descrição | Situação |
|---|---|---|
| 0 | Ajustes no esquema | em andamento [BD]; item 1 da seção 5.2 feito, gatilhos em `banco/funcoes-gatilhos.sql`; a tabela `usuario` já existe em `banco/usuario.sql` |
| 1 | Esqueleto do projeto | concluída |
| 2 | Base visual | concluída |
| 3 | JavaScript comum | concluída |
| 4 | Login e usuários | concluída |
| 5 | Cadastros simples | concluída |
| 6 | Pacientes | concluída |
| 7 | Médicos | concluída |
| 8 | Agenda e agendamento | concluída |
| 9 | Atendimento | concluída |
| 10 | Conta e pagamento | concluída |
| 11 | Início e relatórios | concluída |
| 12 | Acabamento e entrega | pendente |

Cada fase concluída recebe, logo abaixo do seu checklist (seção 8), um **Registro** com o que foi feito, arquivos criados, decisões tomadas e como verificar.

### Testes

Os testes de cada fase rodam contra um PostgreSQL real, criado só para teste com `banco/Trabalho1_ClinicaMedica.sql`, `banco/usuario.sql` e `banco/funcoes-gatilhos.sql`. São três baterias:

| Bateria | Ferramenta | O que cobre | Resultado |
|---|---|---|---|
| Servidor, fases 1–5 | cliente de testes do Flask + PostgreSQL | rotas, login, permissões, validações, gravação no banco, filtros, comandos de terminal | 95 de 95 |
| Navegador, fases 1–5 | Playwright com Google Chrome | digitação, máscaras, validação no navegador, janela de confirmação, menu no celular, rolagem horizontal, erros no console | 28 de 28 |
| Servidor, fases 6–7 | cliente de testes do Flask + PostgreSQL | pacientes e médicos com suas listas, busca, paginação, prontuário por perfil, transações, vínculo usuário–médico | 99 de 99 |
| Navegador, fases 6–7 | Playwright com Google Chrome | cadastro de paciente e médico digitando, linhas dinâmicas, campo que aparece conforme o perfil, telas no celular | 24 de 24 |
| Servidor, fases 8–9 | cliente de testes do Flask + PostgreSQL | horários livres, conflitos de médico, sala e paciente, mudanças de status, permissões, atendimento, conta, gatilhos de exemplo | 77 de 77 |
| Navegador, fases 8–9 | Playwright com Google Chrome | filtro de pacientes e médicos, horários carregados do servidor, cancelamento, totais do atendimento, telas no celular | 23 de 23 |
| Servidor, fases 10–11 | cliente de testes do Flask + PostgreSQL | conta, validações de pagamento, convênio válido ou vencido, pagamentos parciais, exclusão, bloqueio do atendimento pago, gatilho de exemplo, início por perfil, números dos relatórios | 65 de 65 |
| Navegador, fases 10–11 | Playwright com Google Chrome | cálculo automático da parte do paciente, pagamento acima do saldo barrado, campo do convênio que aparece e some, impressão do relatório, telas no celular | 20 de 20 |
| JavaScript | página de testes no Chrome sem interface | funções de máscara, CPF, linhas dinâmicas, filtro, confirmação | 33 de 33 |
| Gatilhos, pela aplicação | cliente de testes do Flask + PostgreSQL com `banco/funcoes-gatilhos.sql` | agendamento e pagamento com a conferência da aplicação contornada, sobreposição de 30 minutos, mudanças de status, grade alterada, atendimento e correção, procedimentos alterados direto no banco | 26 de 26, e 2 lacunas registradas na seção 5.3 |
| Gatilhos, no banco | `psql` e duas conexões simultâneas | roteiro de teste da etapa 3, limites de horário (encostar, fim do turno, meia-noite), status nulo e cancelado, pagamentos por `INSERT` e `UPDATE`, convênio vencido, duas gravações ao mesmo tempo | 41 de 41 |

A cada fase, todas as baterias anteriores rodam de novo, para conferir que nada deixou de funcionar. Os scripts de teste ficam fora do repositório.

---

## 1. Decisões de projeto

| Tema | Decisão |
|---|---|
| Back-end | Python 3 e Flask |
| Banco | PostgreSQL, acessado com psycopg2 |
| Interface | HTML, CSS e JavaScript, com Bootstrap 5.3 e Bootstrap Icons via CDN; sem outras bibliotecas |
| Renderização | no servidor, com templates Jinja; JavaScript para validação, máscaras e interações dentro da página |
| Arquitetura | três camadas: apresentação, negócio e dados (seção 2) |
| Acesso | login com a tabela `usuario` e três perfis: `ADMIN`, `RECEPCAO`, `MEDICO` (seção 6) |
| Senhas | armazenadas como hash com `werkzeug.security`, que já acompanha o Flask |
| Nomenclatura | minúsculas com hífen nos nomes de arquivos; dentro do código, a convenção de cada linguagem (seção 3) |

---

## 2. Arquitetura

### Camadas

| Camada | Pastas | Conteúdo | Disciplina |
|---|---|---|---|
| Apresentação | `rotas/`, `templates/`, `static/` | rotas Flask, HTML, CSS, JavaScript | Interfaces Web |
| Negócio | `negocio/` | validações e regras que não ficam no banco (transições de status, horários livres, permissões) | ambas |
| Dados | `dados/`, `banco/` | DAOs, DDL, funções e gatilhos | Banco de Dados II |

### Fluxo de uma requisição

```
navegador ──GET/POST──▶ rotas/ ──▶ negocio/ ──▶ dados/ ──▶ PostgreSQL
    ▲                     │
    └──── HTML (Jinja) ◀──┘
```

- **GET:** a rota obtém os dados pelo serviço e renderiza o template.
- **POST:** a rota envia o formulário ao serviço. Em caso de sucesso, mensagem `flash` e redirecionamento (POST → redirect → GET). Em caso de erro, o mesmo formulário é renderizado com a mensagem e com os dados já digitados.
- **Exceção:** `GET /consultas/horarios-livres` responde JSON, para que a tela de nova consulta atualize os horários sem recarregar a página. Nenhuma outra rota responde JSON.

### Contrato entre camadas

- Um DAO por entidade em `dados/` (ex.: `PacienteDAO`), com os métodos `listar`, `buscar_por_id`, `inserir`, `atualizar`, `excluir` e consultas específicas quando necessário.
- Os DAOs abrem a conexão com `conexao_banco()` (`dados/conexao.py`): cada bloco `with` é uma transação, com commit no fim ou rollback em caso de erro.
- Os DAOs recebem e devolvem dicionários cujas chaves são os nomes das colunas (`RealDictCursor`). No Jinja, `paciente.nome` funciona da mesma forma.
- O atributo `name` dos campos de formulário é o nome da coluna (`name="data_nasc"`). Campos repetidos (telefones, procedimentos) são lidos com `request.form.getlist`.
- Gravações que envolvem tabelas filhas (telefones, convênios, especialidades, horários, procedimentos) acontecem em um único bloco `conexao_banco()`, ou seja, em uma única transação.
- O DAO não trata erros do banco. O serviço captura `psycopg2.Error` e lança `ErroNegocio` (`negocio/__init__.py`) com a mensagem do gatilho (`erro.diag.message_primary`), e a rota exibe essa mensagem com `flash`.
- Uma rota pode usar um DAO provisório, com os mesmos métodos e dados fixos, até o DAO definitivo existir. Assim a interface avança sem depender do banco pronto.

### Estrutura de pastas

```
clinica_medica/
├── app.py                      # cria o Flask, registra rotas, filtros e comandos de terminal
├── config.py                   # lê o .env
├── requirements.txt            # Flask, psycopg2-binary, python-dotenv
├── .env.exemplo                # modelo do .env (conexão com o banco, SECRET_KEY, FLASK_DEBUG)
├── README.md
├── plano-dev.md
├── banco/
│   ├── Trabalho1_ClinicaMedica.sql   # script de criação (nome original)
│   ├── usuario.sql             # tabela de login (até ser incorporada ao script principal)
│   ├── funcoes-gatilhos.sql
│   └── dados-exemplo.sql
├── docs/                       # PDFs originais: enunciado, DER, modelo lógico
├── dados/
│   ├── conexao.py              # obter_conexao, conexao_banco, testar_conexao
│   ├── usuario.py              # UsuarioDAO
│   ├── paciente.py             # PacienteDAO, com telefones e convênios
│   ├── medico.py               # MedicoDAO, com telefones, especialidades e horários
│   ├── cadastros.py            # convênio, especialidade, procedimento, sala
│   ├── consulta.py             # ConsultaDAO: agenda, atendimento, procedimentos
│   ├── financeiro.py           # conta, pagamentos, contas em aberto
│   └── relatorio.py            # consultas de resumo dos relatórios
├── negocio/
│   ├── __init__.py             # ErroNegocio, ErroValidacao, erro_do_banco, converter_moeda/decimal
│   ├── validacao.py            # CPF, telefone, e-mail, datas e horas
│   ├── autenticacao.py         # login, troca de senha, PERFIS
│   ├── usuarios.py             # cadastro de usuários e vínculo com médico
│   ├── cadastros.py            # convênio, especialidade, procedimento, sala
│   ├── pacientes.py            # pacientes, telefones e convênios
│   ├── medicos.py              # médicos, especialidades e horários; DIAS_SEMANA
│   ├── agenda.py
│   ├── atendimento.py
│   ├── financeiro.py           # validação de pagamentos, FORMAS_PAGAMENTO
│   └── relatorios.py           # período e montagem dos relatórios
├── rotas/
│   ├── acesso.py               # perfis por área, login obrigatório, exige_acesso
│   ├── autenticacao.py         # login, logout, troca de senha
│   ├── inicio.py               # início e /estilo
│   ├── usuarios.py
│   ├── cadastros.py
│   ├── pacientes.py
│   ├── medicos.py
│   ├── consultas.py
│   └── relatorios.py
├── templates/
│   ├── base.html               # layout com menu
│   ├── base-externa.html       # layout sem menu, para o login
│   ├── macros.html             # campos de formulário, cabeçalho de página, status, menu
│   ├── partes/                 # estilos.html, scripts.html, avisos.html (incluídos nos dois layouts)
│   ├── login.html
│   ├── minha-senha.html
│   ├── inicio.html
│   ├── estilo.html
│   ├── relatorios.html
│   ├── usuarios/               # lista.html, formulario.html
│   ├── cadastros/              # lista.html, genérico para os quatro cadastros
│   ├── pacientes/              # lista.html, formulario.html, ficha.html
│   ├── medicos/                # lista.html, formulario.html
│   ├── consultas/              # agenda.html, nova.html, atendimento.html, conta.html
│   └── erros/                  # acesso-negado.html, nao-encontrado.html
└── static/
    ├── css/estilo.css
    ├── js/
    │   ├── comum.js            # validação, confirmação de exclusão, envio duplo, avisos
    │   ├── mascaras.js         # CPF, telefone, moeda; validação de CPF
    │   ├── linhas-dinamicas.js # adicionar e remover linhas a partir de <template>
    │   ├── filtro-tabela.js
    │   ├── nova-consulta.js
    │   ├── atendimento.js
    │   └── pagamento.js
    └── img/logo.svg
```

---

## 3. Nomenclatura

- **Nomes de arquivos e pastas** criados no projeto: letras minúsculas com palavras separadas por hífen (`base-externa.html`, `linhas-dinamicas.js`, `funcoes-gatilhos.sql`). Arquivos Python usam uma palavra só ou sublinhado, porque o Python não importa módulos com hífen no nome. Os arquivos originais do repositório (script SQL e PDFs) mantêm o nome.
- **URLs, classes e ids de HTML/CSS e comandos de terminal:** minúsculas com hífen (`/minha-senha`, `.item-menu`, `flask testar-banco`).
- **Dentro do código:** a convenção de cada linguagem. Python com `snake_case` e classes em `PascalCase`; JavaScript com `camelCase`; colunas SQL e `name` dos campos de formulário com `snake_case`.
- **Valores fixos no banco:** maiúsculas sem acento, como em `forma_pagamento` (`AGENDADA`, `RECEPCAO`).

---

## 4. Direção visual

Linha geral: sistema interno de uma clínica pequena. Sóbrio, denso o bastante para uso o dia inteiro, sem enfeites. A base é o Bootstrap 5.3, com cores, fonte e alguns componentes ajustados.

### Regras

- Componentes do Bootstrap sempre que existirem: grid, formulários, tabelas, cards, alertas, modal, offcanvas.
- Um único arquivo de CSS próprio (`static/css/estilo.css`), carregado depois do Bootstrap. Ele ajusta as variáveis do Bootstrap (`--bs-*`) em vez de reescrever componentes. Nenhum `style="..."` e nenhum `<style>` dentro de templates.
- Um único padrão de botão, tabela e formulário no sistema inteiro, visível na página `/estilo`.
- Paleta própria: nada do azul padrão do Bootstrap.
- Menu lateral sempre visível no computador; títulos de página alinhados à esquerda.
- Sem emojis. Bootstrap Icons apenas no menu e em poucos botões.
- Evitar degradês, sombras grandes, cards muito arredondados, "cards de indicador" com ícone em círculo colorido, animações e banners.

### Cores

| Variável | Valor | Uso |
|---|---|---|
| `--fundo` | `#f4f3ef` | fundo da página (off-white quente) |
| `--superficie` | `#ffffff` | painéis, tabelas e campos |
| `--borda` | `#dcd9d0` | divisórias e contornos |
| `--texto` | `#22262a` | texto principal |
| `--texto-suave` | `#6b6f73` | rótulos e legendas |
| `--principal` | `#1d5c57` | menu, botão principal, links (verde-petróleo) |
| `--principal-escuro` | `#15443f` | hover |
| `--perigo` | `#a23b2c` | excluir, cancelar |

Status da consulta: texto colorido sobre fundo claro.

| Status | Texto | Fundo |
|---|---|---|
| `AGENDADA` | `#4a5a6a` | `#eceff2` |
| `CONFIRMADA` | `#1d5c57` | `#e3eeec` |
| `REALIZADA` | `#2f6b2f` | `#e6f0e2` |
| `CANCELADA` | `#a23b2c` | `#f6e6e2` |
| `FALTOU` | `#8a5a00` | `#f7eed9` |

### Tipografia

IBM Plex Sans (Google Fonts), 15px. A classe `.numero` aplica algarismos de largura fixa (`font-variant-numeric: tabular-nums`) em valores, horários e CPF.

### Layout

- Menu lateral fixo à esquerda (fundo petróleo, 232px), com itens agrupados em *Atendimento*, *Cadastros* e *Administração*, e o usuário logado no rodapé do menu.
- Cada página tem um cabeçalho com o título à esquerda e os botões de ação à direita.
- Abaixo de 992px de largura, o menu vira uma gaveta (offcanvas do Bootstrap) aberta pelo botão "Menu" de uma barra no topo.
- Login: painel estreito centralizado, nome do sistema acima, sem imagem de fundo.

### Componentes

Cantos de 4px; borda de 1px no lugar de sombra; botões retangulares (principal preenchido, secundário só com contorno, perigo em vermelho); tabelas com linhas finas e hover discreto; formulários em grade com rótulo acima do campo. Na validação, só os campos com erro ficam destacados; os válidos continuam neutros.

---

## 5. Banco de dados

### 5.1 Tabela `usuario`

```sql
CREATE TABLE usuario (
	id_usuario SERIAL PRIMARY KEY,
	nome VARCHAR(100) NOT NULL,
	email VARCHAR(100) UNIQUE NOT NULL,
	senha_hash VARCHAR(255) NOT NULL,
	perfil VARCHAR(10) NOT NULL
		CHECK (perfil IN ('ADMIN', 'RECEPCAO', 'MEDICO')),
	ativo BOOLEAN NOT NULL DEFAULT TRUE,
	id_medico INTEGER UNIQUE REFERENCES medico(id_medico),

	CHECK (perfil <> 'MEDICO' OR id_medico IS NOT NULL)
);
```

- Nome no singular, como as demais tabelas (`paciente`, `medico`). Criada depois de `medico` no script.
- `id_medico` liga o usuário de perfil `MEDICO` ao cadastro do médico; é por ele que o sistema sabe qual agenda e quais atendimentos mostrar.
- O primeiro administrador é criado pelo comando `flask criar-admin`, porque o hash da senha é gerado em Python.
- Usuários são desativados (`ativo = FALSE`), nunca excluídos, para não perder o histórico.

### 5.2 Ajustes no esquema

| # | Onde | Ajuste | Motivo |
|---|---|---|---|
| 1 | `sala` | remover a vírgula depois de `descricao VARCHAR(100),` | erro de sintaxe que impede a execução do script. Feito |
| 2 | `paciente."e-mail"` | renomear para `email` | o hífen obriga aspas em toda consulta |
| 3 | `consulta.status` | `CHECK (status IN ('AGENDADA','CONFIRMADA','REALIZADA','CANCELADA','FALTOU'))` | o enunciado define os cinco status |
| 4 | `pagamento` | adicionar `valor_paciente` (ou definir que `valor_pago` é a parte do paciente) | o enunciado exige os valores do convênio e do paciente separados; o DER tem `valor_paciente`. Adotado na Fase 10, sem mudar o banco: `valor_pago` é a parte do paciente e `valor_convenio` a do convênio |
| 5 | valor da consulta | adicionar `valor_consulta` em `medico` (ou valor fixo, ou digitado no atendimento) | `conta.valor_consulta` precisa de uma origem. Adotado na Fase 9, sem mudar o banco: digitado no atendimento, já preenchido com `VALOR_CONSULTA_PADRAO` do `.env` |
| 6 | `conta.valor_total` | `COALESCE` na expressão gerada ou `DEFAULT 0` nas parcelas | soma com `NULL` resulta em `NULL` |
| 7 | `consulta.id_conta` | aceitar nulo e preencher quando a conta é criada | a conta só existe depois do atendimento |
| 8 | `horario.dia_semana` | `CHECK` com `SEGUNDA` … `DOMINGO` | a grade semanal e o cálculo de horários livres precisam de valores fixos |
| 9 | duração da consulta | duração fixa (ex.: 30 min), igual na aplicação e nos gatilhos | necessária para horários livres e detecção de conflito. Adotado na Fase 8: 30 minutos |
| 10 | `horario_medico`, `medico_especialidade` | `UNIQUE (id_medico, id_horario)` e `UNIQUE (id_medico, id_especialidade)` | evitar pares repetidos |
| 11 | modelo lógico | alinhar com o SQL: `sala.status`, `consulta_procedimento.realizado`, PK de `ESPECIALIDADE` (`id_sala`), tipo de `forma_pagamento` | divergências entre o PDF e o script |

### 5.3 Funções e gatilhos usados pela interface

Qualquer mensagem levantada por um gatilho (`RAISE EXCEPTION`) aparece na tela como aviso, com os dados do formulário preservados. As regras de agenda e de conta também são conferidas pela aplicação (Fases 8 e 9), para o sistema funcionar corretamente antes de os gatilhos existirem; com eles, o banco passa a garantir as mesmas regras mesmo fora da aplicação. Os dois lados usam a mesma duração de consulta (30 minutos: `DURACAO_CONSULTA` em `negocio/agenda.py` e `fn_duracao_consulta()` no banco).

As funções e os gatilhos ficam em `banco/funcoes-gatilhos.sql`, executado depois do script de criação. O arquivo pode ser executado de novo: substitui as funções e recria os gatilhos.

| Regra | Gatilho | Situação |
|---|---|---|
| Impedir consulta fora do horário de atendimento do médico | `trg_valida_horario_medico` | feito; a consulta inteira (início + 30 min) precisa caber na faixa do dia |
| Impedir consultas sobrepostas do mesmo médico ou na mesma sala | `trg_valida_conflito_agenda` | feito; considera a duração (09:00 ocupa até 09:30) e consultas com status nulo; cancelada não ocupa |
| Preencher `consulta_procedimento.valor_unitario` com `procedimento.valor` | — | pendente; a aplicação preenche, e o recálculo da conta usa `procedimento.valor` quando o campo está vazio |
| Recalcular `conta.valor_procedimento` quando os procedimentos da consulta mudam | `trg_atualiza_valor_procedimento_conta` | feito |
| Criar a conta quando a consulta passa a `REALIZADA` | — | pendente; a aplicação cria a conta no atendimento |
| Impedir pagamentos acima do total da conta | `trg_valida_pagamento` | feito; também barra valores negativos ou zerados, valor de convênio sem convênio e convênio sem carteirinha válida na data do pagamento |

Gravações simultâneas: o gatilho de agenda trava o médico e a sala (`pg_advisory_xact_lock`) e o de pagamento trava a conta (`SELECT ... FOR UPDATE`) até o fim da transação. Assim, duas recepcionistas gravando ao mesmo tempo não passam juntas pela verificação: a segunda espera a primeira e é recusada se houver conflito.

Com os quatro gatilhos instalados, todas as baterias de teste continuam passando. As inserções diretas que montam consultas no passado, na preparação dos testes, desligam os gatilhos só naquele comando (`SET LOCAL session_replication_role = replica`).

---

## 6. Perfis e permissões

| Área | ADMIN | RECEPCAO | MEDICO |
|---|---|---|---|
| Usuários | gerencia | — | — |
| Cadastros simples | gerencia | — | — |
| Médicos e horários | gerencia | vê | — |
| Pacientes (dados cadastrais) | gerencia | gerencia | vê |
| Agenda | gerencia | gerencia | vê as próprias consultas |
| Atendimento e prontuário | vê | — | registra nas próprias consultas |
| Conta e pagamento | gerencia | gerencia | — |
| Relatórios | vê | — | — |

- A tabela acima está no dicionário `ACESSO` de `rotas/acesso.py`. É a única fonte da regra: as rotas usam `exige_acesso("area")` ou `pode("area")`, e o menu usa `pode("area")` para decidir o que mostrar. Além das áreas da tabela, há as ações específicas `agendar` (ADMIN, RECEPCAO: marcar consultas e mudar o status), `financeiro` (ADMIN, RECEPCAO: conta e pagamentos), `pagamentos_excluir` (ADMIN), `pacientes_editar` (ADMIN, RECEPCAO), `pacientes_excluir` (ADMIN), `medicos_editar` (ADMIN) e `prontuario` (ADMIN, MEDICO).
- Exclusão de pacientes e médicos: só `ADMIN`.
- Sintomas, diagnóstico e prescrição aparecem para `ADMIN` e para o `MEDICO` da própria consulta; um médico não vê o prontuário das consultas de outro. A recepção, e o médico nas consultas de outros, veem na ficha do paciente só data, médico e status. O filtro é feito no servidor (`ServicoPacientes.consultas`): os campos nem chegam ao template.
- O menu mostra apenas o que o perfil acessa. Uma rota acessada sem permissão responde 403 com `erros/acesso-negado.html`.

---

## 7. Rotas

| Método | URL | Página ou ação | Perfis |
|---|---|---|---|
| GET, POST | `/login` | `login.html` | público |
| GET | `/logout` | encerra a sessão | todos |
| GET, POST | `/minha-senha` | `minha-senha.html` | todos |
| GET | `/` | `inicio.html` | todos |
| GET | `/usuarios/` | `usuarios/lista.html` | ADMIN |
| GET, POST | `/usuarios/novo` | `usuarios/formulario.html` | ADMIN |
| GET, POST | `/usuarios/<id>/editar` | `usuarios/formulario.html` | ADMIN |
| POST | `/usuarios/<id>/alternar-ativo` | ativa ou desativa | ADMIN |
| GET, POST | `/cadastros/<tipo>` | `cadastros/lista.html`; `tipo`: `convenios`, `especialidades`, `procedimentos`, `salas` | ADMIN |
| POST | `/cadastros/<tipo>/<id>/excluir` | exclui | ADMIN |
| GET | `/pacientes/` | `pacientes/lista.html` (`?busca=`) | todos |
| GET, POST | `/pacientes/novo` | `pacientes/formulario.html` | ADMIN, RECEPCAO |
| GET | `/pacientes/<id>` | `pacientes/ficha.html` | todos |
| GET, POST | `/pacientes/<id>/editar` | `pacientes/formulario.html` | ADMIN, RECEPCAO |
| POST | `/pacientes/<id>/excluir` | exclui | ADMIN |
| GET | `/medicos/` | `medicos/lista.html` (`?id_especialidade=`) | ADMIN, RECEPCAO |
| GET, POST | `/medicos/novo` | `medicos/formulario.html` | ADMIN |
| GET, POST | `/medicos/<id>/editar` | `medicos/formulario.html` | ADMIN |
| POST | `/medicos/<id>/excluir` | exclui | ADMIN |
| GET | `/agenda` | `consultas/agenda.html` (`?data=&id_medico=&status=`) | todos; MEDICO vê só as próprias |
| GET, POST | `/consultas/nova` | `consultas/nova.html` | ADMIN, RECEPCAO |
| GET | `/consultas/horarios-livres` | JSON (`?id_medico=&data=`) | ADMIN, RECEPCAO |
| POST | `/consultas/<id>/status` | altera o status | ADMIN, RECEPCAO |
| GET, POST | `/consultas/<id>/atendimento` | `consultas/atendimento.html` | MEDICO da consulta; ADMIN só leitura |
| GET | `/consultas/<id>/conta` | `consultas/conta.html` | ADMIN, RECEPCAO |
| POST | `/consultas/<id>/pagamentos` | registra pagamento | ADMIN, RECEPCAO |
| POST | `/consultas/<id>/pagamentos/<id_pagamento>/excluir` | exclui um pagamento lançado por engano | ADMIN |
| GET | `/relatorios` | `relatorios.html` | ADMIN |
| GET, POST | `/estilo` | `estilo.html` | apenas em modo de desenvolvimento |

---

### Observação: Fase 12 — Acabamento e entrega

- [ ] Páginas `erros/acesso-negado.html` e `erros/nao-encontrado.html` revisadas
- [ ] Estados vazio e de erro em todas as telas
- [ ] Responsividade (375px de largura), navegação por teclado, foco visível, `label` em todos os campos, contraste
- [ ] Revisão de consistência: textos, botões, ordem das ações
- [ ] `banco/dados-exemplo.sql` com dados realistas e um usuário de cada perfil [BD]
- [ ] `README.md` final com capturas de tela e roteiro de demonstração (login → agendar → atender → cobrar)

