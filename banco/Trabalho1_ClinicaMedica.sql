CREATE TABLE convenio (
	id_convenio SERIAL PRIMARY KEY,
	nome VARCHAR(100)
);


CREATE TABLE paciente (
	id_paciente SERIAL PRIMARY KEY,
	nome VARCHAR(100),
	data_nasc DATE,
	cpf VARCHAR(14),
	rg VARCHAR(20),
	sexo VARCHAR(20),
	endereco VARCHAR(200),
	"e-mail" VARCHAR(100)
);


CREATE TABLE telefone_paciente (
	id_telefone SERIAL PRIMARY KEY,
	numero_telefone VARCHAR(15),
	id_paciente INTEGER REFERENCES paciente(id_paciente)
);


CREATE TABLE plano_convenio (
	id_paciente INTEGER REFERENCES paciente(id_paciente),
	id_convenio INTEGER REFERENCES convenio(id_convenio),
	numero_carteirinha VARCHAR(50),
	validade DATE,
	tipo_plano VARCHAR(50),
	PRIMARY KEY (id_paciente, id_convenio)
);


CREATE TABLE sala (
	id_sala SERIAL PRIMARY KEY,
	descricao VARCHAR(100),
);


CREATE TABLE procedimento (
	id_procedimento SERIAL PRIMARY KEY,
	descricao VARCHAR(200),
	valor NUMERIC(10,2)
);


CREATE TABLE conta (
	id_conta SERIAL PRIMARY KEY,
	valor_procedimento NUMERIC(10,2),
	valor_consulta NUMERIC(10,2),
	valor_total NUMERIC(10,2)
		GENERATED ALWAYS AS
		(valor_procedimento + valor_consulta) STORED
);


CREATE TABLE pagamento (
	id_pagamento SERIAL PRIMARY KEY,
	data_pagamento DATE,
	valor_pago NUMERIC(10,2),
	forma_pagamento VARCHAR(10)
		CHECK (forma_pagamento IN ('CARTAO', 'PIX', 'DINHEIRO')),
	possui_convenio BOOLEAN,
	valor_convenio NUMERIC(10,2),
	id_conta INTEGER REFERENCES conta(id_conta)
);


CREATE TABLE horario (
	id_horario SERIAL PRIMARY KEY,
	hora_inicio TIME,
	hora_fim TIME,
	dia_semana VARCHAR(20)
);


CREATE TABLE medico (
	id_medico SERIAL PRIMARY KEY,
	nome_medico VARCHAR(100),
	percentual_honorario NUMERIC(5,2),
	crm VARCHAR(30) UNIQUE NOT NULL
);


CREATE TABLE telefone_medico (
	id_telefone SERIAL PRIMARY KEY,
	numero_telefone VARCHAR(15),
	id_medico INTEGER REFERENCES medico(id_medico)
);


CREATE TABLE horario_medico (
	id_horario_medico SERIAL PRIMARY KEY,
	id_medico INTEGER REFERENCES medico(id_medico),
	id_horario INTEGER REFERENCES horario(id_horario)
);


CREATE TABLE especialidade (
	id_especialidade SERIAL PRIMARY KEY,
	nome_especialidade VARCHAR(60)
);


CREATE TABLE medico_especialidade (
	id_medico_especialidade SERIAL PRIMARY KEY,
	id_medico INTEGER REFERENCES medico(id_medico),
	id_especialidade INTEGER REFERENCES especialidade(id_especialidade)
);


CREATE TABLE consulta (
	id_consulta SERIAL PRIMARY KEY,
	data_hora_marcado TIMESTAMP,
	data_hora_realizado TIMESTAMP,
	status VARCHAR(30),
	sintomas TEXT,
	diagnostico TEXT,
	prescricao TEXT,

	id_paciente INTEGER REFERENCES paciente(id_paciente),
	id_medico INTEGER REFERENCES medico(id_medico),
	id_sala INTEGER REFERENCES sala(id_sala),
	id_conta INTEGER REFERENCES conta(id_conta)
);


CREATE TABLE consulta_procedimento (
	id_consulta INTEGER REFERENCES consulta(id_consulta),
	id_procedimento INTEGER REFERENCES procedimento(id_procedimento),
	quantidade INTEGER,
	valor_unitario NUMERIC(10,2),

	PRIMARY KEY (id_consulta, id_procedimento)
);