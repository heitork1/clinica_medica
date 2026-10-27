-- Usuários do sistema (login). Executar depois de Trabalho1_ClinicaMedica.sql,
-- porque referencia a tabela medico. Na Fase 0 este bloco pode ser incorporado
-- ao script principal.

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
