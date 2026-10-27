-- Funções e gatilhos em PL/pgSQL. Executar depois de Trabalho1_ClinicaMedica.sql.
-- O arquivo pode ser executado de novo: as funções são substituídas e os gatilhos recriados.

---================================================================================
--ETAPA 3 GATILHOS E FUNÇÕES
---================================================================================

-- Duração de cada consulta. A aplicação usa o mesmo valor (DURACAO_CONSULTA em negocio/agenda.py).
CREATE OR REPLACE FUNCTION fn_duracao_consulta()
RETURNS INTERVAL AS $$
    SELECT INTERVAL '30 minutes';
$$ LANGUAGE sql IMMUTABLE;


-- GATILHO 1: impede consultas sobrepostas do mesmo médico ou na mesma sala.
-- Duas consultas se sobrepõem quando uma começa antes de a outra terminar
-- (09:00 ocupa até 09:30, então 09:15 conflita e 09:30 não).
CREATE OR REPLACE FUNCTION fn_valida_conflito_agenda()
RETURNS TRIGGER AS $$
DECLARE
    v_inicio TIMESTAMP := NEW.data_hora_marcado;
    v_fim    TIMESTAMP := NEW.data_hora_marcado + fn_duracao_consulta();
BEGIN
    -- Ignora consultas canceladas
    IF NEW.status = 'CANCELADA' OR NEW.data_hora_marcado IS NULL THEN
        RETURN NEW;
    END IF;

    -- Trava o médico e a sala até o fim da transação: duas gravações simultâneas
    -- no mesmo horário esperam uma pela outra em vez de passarem juntas pela verificação.
    PERFORM pg_advisory_xact_lock(1, NEW.id_medico);
    IF NEW.id_sala IS NOT NULL THEN
        PERFORM pg_advisory_xact_lock(2, NEW.id_sala);
    END IF;

    -- Conflito de médico
    IF EXISTS (
        SELECT 1 FROM consulta c
        WHERE c.id_medico = NEW.id_medico
          AND c.data_hora_marcado < v_fim
          AND c.data_hora_marcado + fn_duracao_consulta() > v_inicio
          AND c.status IS DISTINCT FROM 'CANCELADA'
          AND c.id_consulta <> COALESCE(NEW.id_consulta, -1)
    ) THEN
        RAISE EXCEPTION '% já tem consulta marcada nesse horário (%).',
            (SELECT nome_medico FROM medico WHERE id_medico = NEW.id_medico),
            to_char(v_inicio, 'DD/MM/YYYY HH24:MI');
    END IF;

    -- Conflito de sala
    IF NEW.id_sala IS NOT NULL AND EXISTS (
        SELECT 1 FROM consulta c
        WHERE c.id_sala = NEW.id_sala
          AND c.data_hora_marcado < v_fim
          AND c.data_hora_marcado + fn_duracao_consulta() > v_inicio
          AND c.status IS DISTINCT FROM 'CANCELADA'
          AND c.id_consulta <> COALESCE(NEW.id_consulta, -1)
    ) THEN
        RAISE EXCEPTION 'A sala % já está ocupada nesse horário (%).',
            (SELECT descricao FROM sala WHERE id_sala = NEW.id_sala),
            to_char(v_inicio, 'DD/MM/YYYY HH24:MI');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_valida_conflito_agenda ON consulta;
CREATE TRIGGER trg_valida_conflito_agenda
BEFORE INSERT OR UPDATE OF data_hora_marcado, id_medico, id_sala, status
ON consulta
FOR EACH ROW
EXECUTE FUNCTION fn_valida_conflito_agenda();


-- GATILHO 2: a consulta inteira (início + duração) precisa caber em uma faixa
-- de atendimento do médico naquele dia da semana.
-- Os valores de dia_semana devem ser cadastrados no banco em maiúsculas e sem acento!
CREATE OR REPLACE FUNCTION fn_valida_horario_medico()
RETURNS TRIGGER AS $$
DECLARE
    v_dia_semana TEXT;
    v_dia        DATE;
BEGIN
    IF NEW.status = 'CANCELADA' THEN
        RETURN NEW;
    END IF;

    IF NEW.data_hora_marcado IS NULL THEN
        RAISE EXCEPTION 'Informe a data e a hora da consulta.';
    END IF;

    -- Mapeia o número do dia para o texto usado na tabela horario
    v_dia_semana := CASE EXTRACT(DOW FROM NEW.data_hora_marcado)::INT
        WHEN 0 THEN 'DOMINGO'
        WHEN 1 THEN 'SEGUNDA'
        WHEN 2 THEN 'TERCA'
        WHEN 3 THEN 'QUARTA'
        WHEN 4 THEN 'QUINTA'
        WHEN 5 THEN 'SEXTA'
        WHEN 6 THEN 'SABADO'
    END;
    v_dia := NEW.data_hora_marcado::DATE;

    -- compara como data + hora para que uma consulta perto da meia-noite não "volte" para 00:00
    IF NOT EXISTS (
        SELECT 1
        FROM horario_medico hm
        JOIN horario h ON h.id_horario = hm.id_horario
        WHERE hm.id_medico = NEW.id_medico
          AND UPPER(h.dia_semana) = v_dia_semana
          AND NEW.data_hora_marcado >= v_dia + h.hora_inicio
          AND NEW.data_hora_marcado + fn_duracao_consulta() <= v_dia + h.hora_fim
    ) THEN
        RAISE EXCEPTION '% não atende em % às % (a consulta dura %).',
            (SELECT nome_medico FROM medico WHERE id_medico = NEW.id_medico),
            to_char(v_dia, 'DD/MM/YYYY'),
            to_char(NEW.data_hora_marcado, 'HH24:MI'),
            to_char(fn_duracao_consulta(), 'FMMI "minutos"');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_valida_horario_medico ON consulta;
CREATE TRIGGER trg_valida_horario_medico
BEFORE INSERT OR UPDATE OF data_hora_marcado, id_medico
ON consulta
FOR EACH ROW
EXECUTE FUNCTION fn_valida_horario_medico();


-- GATILHO 3: recalcula conta.valor_procedimento quando os procedimentos da consulta mudam.
CREATE OR REPLACE FUNCTION fn_atualiza_valor_procedimento_conta()
RETURNS TRIGGER AS $$
DECLARE
    v_consulta_old INTEGER;
    v_consulta_new INTEGER;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        v_consulta_old := OLD.id_consulta;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_consulta_new := NEW.id_consulta;
    END IF;

    -- Recalcula a(s) conta(s) afetada(s).
    -- Se valor_unitario não foi informado, usa o valor cadastrado no procedimento.
    UPDATE conta ct
    SET valor_procedimento = (
        SELECT COALESCE(SUM(cp.quantidade * COALESCE(cp.valor_unitario, p.valor)), 0)
        FROM consulta c
        JOIN consulta_procedimento cp ON cp.id_consulta = c.id_consulta
        JOIN procedimento p ON p.id_procedimento = cp.id_procedimento
        WHERE c.id_conta = ct.id_conta
    )
    WHERE ct.id_conta IN (
        SELECT id_conta
        FROM consulta
        WHERE id_consulta IN (v_consulta_old, v_consulta_new)
    );

    RETURN NULL; -- gatilho AFTER: o retorno é ignorado
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_atualiza_valor_procedimento_conta ON consulta_procedimento;
CREATE TRIGGER trg_atualiza_valor_procedimento_conta
AFTER INSERT OR UPDATE OR DELETE
ON consulta_procedimento
FOR EACH ROW
EXECUTE FUNCTION fn_atualiza_valor_procedimento_conta();


-- GATILHO 4: valida o pagamento antes de gravar.
--   * valor_pago é a parte do paciente e valor_convenio a do convênio; nenhum pode ser negativo;
--   * valor_convenio só existe quando possui_convenio é verdadeiro;
--   * com convênio, o paciente da consulta precisa de carteirinha válida na data do pagamento
--     (carteirinha sem validade conta como válida);
--   * a soma de todos os pagamentos da conta não pode passar do total da conta.
CREATE OR REPLACE FUNCTION fn_valida_pagamento()
RETURNS TRIGGER AS $$
DECLARE
    v_total     NUMERIC(10,2);
    v_ja_pago   NUMERIC(10,2);
    v_paciente  INTEGER;
    v_data      DATE := COALESCE(NEW.data_pagamento, CURRENT_DATE);
BEGIN
    IF NEW.id_conta IS NULL THEN
        RAISE EXCEPTION 'O pagamento precisa estar ligado a uma conta.';
    END IF;

    IF COALESCE(NEW.valor_pago, 0) < 0 OR COALESCE(NEW.valor_convenio, 0) < 0 THEN
        RAISE EXCEPTION 'Os valores do pagamento não podem ser negativos.';
    END IF;

    IF COALESCE(NEW.valor_pago, 0) + COALESCE(NEW.valor_convenio, 0) <= 0 THEN
        RAISE EXCEPTION 'O pagamento precisa ter algum valor.';
    END IF;

    IF NOT COALESCE(NEW.possui_convenio, FALSE) AND COALESCE(NEW.valor_convenio, 0) <> 0 THEN
        RAISE EXCEPTION 'Valor do convênio informado em um pagamento sem convênio.';
    END IF;

    IF NEW.possui_convenio THEN
        SELECT c.id_paciente INTO v_paciente
        FROM consulta c
        WHERE c.id_conta = NEW.id_conta
        LIMIT 1;

        IF NOT EXISTS (
            SELECT 1 FROM plano_convenio pc
            WHERE pc.id_paciente = v_paciente
              AND (pc.validade IS NULL OR pc.validade >= v_data)
        ) THEN
            RAISE EXCEPTION 'O paciente não tem convênio com carteirinha válida em %.',
                to_char(v_data, 'DD/MM/YYYY');
        END IF;
    END IF;

    -- Trava a conta até o fim da transação: dois pagamentos simultâneos não
    -- conseguem, juntos, passar do total.
    SELECT COALESCE(ct.valor_consulta, 0) + COALESCE(ct.valor_procedimento, 0)
      INTO v_total
      FROM conta ct
     WHERE ct.id_conta = NEW.id_conta
       FOR UPDATE;

    SELECT COALESCE(SUM(COALESCE(pg.valor_pago, 0) + COALESCE(pg.valor_convenio, 0)), 0)
      INTO v_ja_pago
      FROM pagamento pg
     WHERE pg.id_conta = NEW.id_conta
       AND pg.id_pagamento IS DISTINCT FROM NEW.id_pagamento;

    IF v_ja_pago + COALESCE(NEW.valor_pago, 0) + COALESCE(NEW.valor_convenio, 0) > v_total THEN
        RAISE EXCEPTION 'O pagamento passa do total da conta (total R$ %, já pago R$ %, saldo R$ %).',
            replace(to_char(v_total, 'FM99999990.00'), '.', ','),
            replace(to_char(v_ja_pago, 'FM99999990.00'), '.', ','),
            replace(to_char(v_total - v_ja_pago, 'FM99999990.00'), '.', ',');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_valida_pagamento ON pagamento;
CREATE TRIGGER trg_valida_pagamento
BEFORE INSERT OR UPDATE
ON pagamento
FOR EACH ROW
EXECUTE FUNCTION fn_valida_pagamento();
