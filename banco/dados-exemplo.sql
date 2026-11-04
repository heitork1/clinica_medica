-- ============================================================================
-- DADOS DE EXEMPLO PARA DEMONSTRAÇÃO
-- ----------------------------------------------------------------------------
-- Ordem de execução, em um banco recém-criado:
--   1) Trabalho1_ClinicaMedica.sql
--   2) usuario.sql
--   3) funcoes-gatilhos.sql
--   4) dados-exemplo.sql   (este arquivo)
--
-- As tabelas devem estar vazias: os ids são os gerados em ordem (1, 2, 3...)
-- e este arquivo se refere a eles.
--
-- As datas das consultas são relativas a HOJE: "semana passada" e "semana que
-- vem", sempre em dias úteis dentro do horário de cada médico. Assim os
-- gatilhos aceitam e a agenda sempre tem consultas passadas e futuras.
--
-- Logins (senha entre parênteses):
--   admin@clinica.com     (admin123)     perfil ADMIN
--   recepcao@clinica.com  (recepcao123)  perfil RECEPCAO
--   helena@clinica.com    (medico123)    perfil MEDICO - Dra. Helena Souza
--   carlos@clinica.com    (medico123)    perfil MEDICO - Dr. Carlos Mendes
-- ============================================================================


-- ---------------------------------------------------------------------------
-- Cadastros simples
-- ---------------------------------------------------------------------------
INSERT INTO convenio (nome) VALUES
    ('Unimed'),          -- 1
    ('Bradesco Saúde'),  -- 2
    ('SulAmérica');      -- 3

INSERT INTO especialidade (nome_especialidade) VALUES
    ('Clínica Geral'),   -- 1
    ('Cardiologia'),     -- 2
    ('Pediatria'),       -- 3
    ('Dermatologia');    -- 4

INSERT INTO sala (descricao) VALUES
    ('Consultório 1'),   -- 1
    ('Consultório 2'),   -- 2
    ('Consultório 3');   -- 3

INSERT INTO procedimento (descricao, valor) VALUES
    ('Eletrocardiograma', 120.00),     -- 1
    ('Hemograma completo', 45.00),     -- 2
    ('Curativo', 30.00),               -- 3
    ('Aplicação de injeção', 25.00),   -- 4
    ('Retirada de pontos', 40.00);     -- 5


-- ---------------------------------------------------------------------------
-- Pacientes (CPFs válidos, mas fictícios)
-- ---------------------------------------------------------------------------
INSERT INTO paciente (nome, data_nasc, cpf, rg, sexo, endereco, "e-mail") VALUES
    ('Mariana Oliveira Costa', '1988-04-12', '526.018.159-06', '1234567', 'Feminino',  'Rua das Flores, 120 - Joinville/SC',     'mariana.costa@email.com'),   -- 1
    ('Roberto Almeida Lima',   '1975-09-30', '083.016.613-05', '2345678', 'Masculino', 'Av. Brasil, 845 - Joinville/SC',          'roberto.lima@email.com'),    -- 2
    ('Lucas Pereira Santos',   '2016-02-18', '186.091.390-34', NULL,      'Masculino', 'Rua XV de Novembro, 33 - Joinville/SC',  NULL),                        -- 3
    ('Fernanda Rocha Dias',    '1992-11-05', '996.030.824-30', '3456789', 'Feminino',  'Rua Rio Branco, 570 - Joinville/SC',     'fernanda.dias@email.com'),   -- 4
    ('Antônio Ferreira Neto',  '1960-07-21', '628.194.821-12', '4567890', 'Masculino', 'Rua Dr. João Colin, 78 - Joinville/SC',   NULL),                        -- 5
    ('Juliana Martins Souza',  '2001-01-09', '993.518.190-19', '5678901', 'Feminino',  'Rua Blumenau, 301 - Joinville/SC',       'juliana.souza@email.com');   -- 6

INSERT INTO telefone_paciente (numero_telefone, id_paciente) VALUES
    ('(47) 99111-2233', 1),
    ('(47) 3422-1000',  1),
    ('(47) 99222-3344', 2),
    ('(47) 99333-4455', 3),   -- telefone do responsável
    ('(47) 99444-5566', 4),
    ('(47) 99555-6677', 5),
    ('(47) 99666-7788', 6);

-- Planos: o da Fernanda (paciente 4) está VENCIDO, para mostrar o aviso na tela
INSERT INTO plano_convenio (id_paciente, id_convenio, numero_carteirinha, validade, tipo_plano) VALUES
    (1, 1, '0012345678', CURRENT_DATE + 365, 'Enfermaria'),
    (2, 1, '0087654321', CURRENT_DATE + 200, 'Apartamento'),
    (2, 3, '5544332211', CURRENT_DATE + 90,  'Básico'),
    (4, 2, '9988776655', CURRENT_DATE - 30,  'Básico');
-- Pacientes 3, 5 e 6 são particulares (sem convênio)


-- ---------------------------------------------------------------------------
-- Médicos
-- ---------------------------------------------------------------------------
INSERT INTO medico (nome_medico, percentual_honorario, crm) VALUES
    ('Dra. Helena Souza',  40.00, 'CRM 12345/SC'),   -- 1
    ('Dr. Carlos Mendes',  45.00, 'CRM 23456/SC'),   -- 2
    ('Dra. Paula Ribeiro', 35.00, 'CRM 34567/SC');   -- 3

INSERT INTO telefone_medico (numero_telefone, id_medico) VALUES
    ('(47) 99701-0001', 1),
    ('(47) 99702-0002', 2),
    ('(47) 99703-0003', 3);

INSERT INTO medico_especialidade (id_medico, id_especialidade) VALUES
    (1, 1),            -- Helena: Clínica Geral
    (2, 2),            -- Carlos: Cardiologia
    (2, 1),            -- Carlos também atende Clínica Geral
    (3, 3),            -- Paula: Pediatria
    (3, 4);            -- Paula: Dermatologia

-- Faixas de horário (compartilhadas entre os médicos)
INSERT INTO horario (hora_inicio, hora_fim, dia_semana) VALUES
    ('08:00', '12:00', 'SEGUNDA'),   -- 1
    ('08:00', '12:00', 'TERCA'),     -- 2
    ('08:00', '12:00', 'QUARTA'),    -- 3
    ('08:00', '12:00', 'QUINTA'),    -- 4
    ('08:00', '12:00', 'SEXTA'),     -- 5
    ('14:00', '18:00', 'SEGUNDA'),   -- 6
    ('14:00', '18:00', 'TERCA'),     -- 7
    ('14:00', '18:00', 'QUARTA'),    -- 8
    ('14:00', '18:00', 'QUINTA'),    -- 9
    ('14:00', '18:00', 'SEXTA');     -- 10

INSERT INTO horario_medico (id_medico, id_horario) VALUES
    -- Helena: segunda a sexta, manhã e tarde
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10),
    -- Carlos: segunda, quarta e sexta de manhã; terça e quinta à tarde
    (2, 1), (2, 3), (2, 5), (2, 7), (2, 9),
    -- Paula: terça e quinta, manhã e tarde
    (3, 2), (3, 4), (3, 7), (3, 9);


-- ---------------------------------------------------------------------------
-- Usuários do sistema
-- ---------------------------------------------------------------------------
INSERT INTO usuario (nome, email, senha_hash, perfil, id_medico) VALUES
    ('Administrador', 'admin@clinica.com',
     'scrypt:32768:8:1$d1oyglzx5bRf9ZkP$fcf3aad984c7b1ced9938afe1fc92143787e159493ccc33bdddae109c4549975edf02f1866f07fa3c4cbb103fe35ed08a0f1774d3f2b100df1d3f7e5516b6927',
     'ADMIN', NULL),
    ('Recepção', 'recepcao@clinica.com',
     'scrypt:32768:8:1$jAWTfJPDUb4CJ4Pc$83e0fff19079006e992d6f69a6723d0652a3365f28f665727e05de8c31b020359d73f4a5453e4037100bf30567eb83ce28e4363e7af36dcdb97327ccc886f1c3',
     'RECEPCAO', NULL),
    ('Dra. Helena Souza', 'helena@clinica.com',
     'scrypt:32768:8:1$Ny669SgA8egAC4qs$94b05706531a1423085dd6abe18696a8fda0f0491db5dc8763110aa0cbd10302832dc27a557e1074b4bcda93abe6ce1c283c1323f7390bbdb5f974d124e12eee',
     'MEDICO', 1),
    ('Dr. Carlos Mendes', 'carlos@clinica.com',
     'scrypt:32768:8:1$Ny669SgA8egAC4qs$94b05706531a1423085dd6abe18696a8fda0f0491db5dc8763110aa0cbd10302832dc27a557e1074b4bcda93abe6ce1c283c1323f7390bbdb5f974d124e12eee',
     'MEDICO', 2);


-- ---------------------------------------------------------------------------
-- Consultas
-- "segunda_passada" = segunda-feira da semana passada; some 1 dia para terça etc.
-- ---------------------------------------------------------------------------

-- Semana passada: consultas já realizadas, uma cancelada e uma em que o paciente faltou
INSERT INTO consulta (data_hora_marcado, data_hora_realizado, status, sintomas, diagnostico, prescricao,
                      id_paciente, id_medico, id_sala) VALUES
    -- 1: Mariana com a Dra. Helena (segunda, 09:00) - realizada
    (date_trunc('week', CURRENT_DATE) - INTERVAL '7 days' + INTERVAL '9 hours',
     date_trunc('week', CURRENT_DATE) - INTERVAL '7 days' + INTERVAL '9 hours 5 minutes',
     'REALIZADA',
     'Febre há dois dias, dor de garganta e cansaço.',
     'Faringite viral.',
     'Repouso, hidratação e paracetamol 750 mg a cada 8 horas por 3 dias.',
     1, 1, 1),
    -- 2: Roberto com o Dr. Carlos (quarta, 10:00) - realizada, com convênio
    (date_trunc('week', CURRENT_DATE) - INTERVAL '5 days' + INTERVAL '10 hours',
     date_trunc('week', CURRENT_DATE) - INTERVAL '5 days' + INTERVAL '10 hours 10 minutes',
     'REALIZADA',
     'Palpitações e falta de ar ao subir escadas.',
     'Hipertensão leve, sem alterações no eletrocardiograma.',
     'Losartana 50 mg uma vez ao dia. Retorno em 30 dias.',
     2, 2, 2),
    -- 3: Lucas com a Dra. Paula (terça, 09:00) - realizada, ainda sem pagamento
    (date_trunc('week', CURRENT_DATE) - INTERVAL '6 days' + INTERVAL '9 hours',
     date_trunc('week', CURRENT_DATE) - INTERVAL '6 days' + INTERVAL '9 hours 5 minutes',
     'REALIZADA',
     'Tosse seca e coriza há uma semana.',
     'Resfriado comum.',
     'Lavagem nasal com soro e observação. Retornar se houver febre.',
     3, 3, 3),
    -- 4: Fernanda com a Dra. Helena (sexta, 14:00) - cancelada
    (date_trunc('week', CURRENT_DATE) - INTERVAL '3 days' + INTERVAL '14 hours',
     NULL, 'CANCELADA', NULL, NULL, NULL,
     4, 1, 1),
    -- 5: Antônio com a Dra. Helena (quinta, 15:00) - faltou
    (date_trunc('week', CURRENT_DATE) - INTERVAL '4 days' + INTERVAL '15 hours',
     NULL, 'FALTOU', NULL, NULL, NULL,
     5, 1, 1);

-- Semana que vem: consultas por atender
INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala) VALUES
    -- 6: Juliana com a Dra. Paula (terça, 09:00) - confirmada
    (date_trunc('week', CURRENT_DATE) + INTERVAL '8 days' + INTERVAL '9 hours',  'CONFIRMADA', 6, 3, 3),
    -- 7: Mariana com o Dr. Carlos (quarta, 10:00) - agendada
    (date_trunc('week', CURRENT_DATE) + INTERVAL '9 days' + INTERVAL '10 hours', 'AGENDADA',   1, 2, 2),
    -- 8: Antônio com a Dra. Helena (segunda, 09:30) - agendada
    (date_trunc('week', CURRENT_DATE) + INTERVAL '7 days' + INTERVAL '9 hours 30 minutes', 'AGENDADA', 5, 1, 1),
    -- 9: Fernanda com a Dra. Helena (quinta, 14:30) - agendada
    (date_trunc('week', CURRENT_DATE) + INTERVAL '10 days' + INTERVAL '14 hours 30 minutes', 'AGENDADA', 4, 1, 1);


-- ---------------------------------------------------------------------------
-- Contas, procedimentos e pagamentos das consultas realizadas
-- ---------------------------------------------------------------------------

-- Conta 1: Mariana - consulta 150 + hemograma 45 + injeção 25 = 220 (pago parcialmente)
INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (70.00, 150.00);
UPDATE consulta SET id_conta = 1 WHERE id_consulta = 1;
INSERT INTO consulta_procedimento (id_consulta, id_procedimento, quantidade, valor_unitario) VALUES
    (1, 2, 1, 45.00),
    (1, 4, 1, 25.00);
INSERT INTO pagamento (data_pagamento, valor_pago, forma_pagamento, possui_convenio, valor_convenio, id_conta) VALUES
    (CURRENT_DATE - 7, 100.00, 'DINHEIRO', FALSE, NULL, 1);   -- falta pagar 120,00

-- Conta 2: Roberto - consulta 200 + eletrocardiograma 120 = 320 (quitada: convênio + paciente)
INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (120.00, 200.00);
UPDATE consulta SET id_conta = 2 WHERE id_consulta = 2;
INSERT INTO consulta_procedimento (id_consulta, id_procedimento, quantidade, valor_unitario) VALUES
    (2, 1, 1, 120.00);
INSERT INTO pagamento (data_pagamento, valor_pago, forma_pagamento, possui_convenio, valor_convenio, id_conta) VALUES
    (CURRENT_DATE - 5, 64.00, 'CARTAO', TRUE, 256.00, 2);     -- paciente 64 + Unimed 256

-- Conta 3: Lucas - só a consulta, 150 (em aberto, sem pagamento)
INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (0.00, 150.00);
UPDATE consulta SET id_conta = 3 WHERE id_consulta = 3;
