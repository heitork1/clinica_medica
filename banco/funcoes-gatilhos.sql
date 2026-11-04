---================================================================================
-- TRABALHO PRÁTICO - BANCO DE DADOS II
-- ETAPA 3: GATILHOS E FUNÇÕES (TRIGGERS & PROCEDURES)
-- ================================================================================
-- GATILHO 1: Validação de Conflito de Agenda (Médico e Sala)
-- Tabela: consulta
-- Momento: BEFORE INSERT OR UPDATE
-- ================================================================================
-- Garante que um médico não tenha duas consultas marcadas no mesmo horário
-- e que uma mesma sala não seja ocupada por duas consultas ao mesmo tempo.
-- Consultas canceladas não geram conflito.
CREATE OR REPLACE FUNCTION fn_valida_conflito_agenda()
RETURNS TRIGGER AS $$
BEGIN
    -- Se a consulta foi cancelada, não precisa verificar conflito
    IF NEW.status = 'CANCELADA' THEN
        RETURN NEW;
    END IF;

    -- 1. Verifica se o médico já possui outra consulta marcada no mesmo dia e horário
    IF EXISTS (
        SELECT 1 FROM consulta c
        WHERE c.id_medico = NEW.id_medico
          AND c.data_hora_marcado = NEW.data_hora_marcado
          AND c.status <> 'CANCELADA'
          AND c.id_consulta <> COALESCE(NEW.id_consulta, -1)
    ) THEN
        RAISE EXCEPTION 'O médico já possui consulta marcada no horário %.',
            to_char(NEW.data_hora_marcado, 'DD/MM/YYYY HH24:MI');
    END IF;

    -- 2. Se foi informada uma sala, verifica se ela já está ocupada no mesmo dia e horário
    IF NEW.id_sala IS NOT NULL AND EXISTS (
        SELECT 1 FROM consulta c
        WHERE c.id_sala = NEW.id_sala
          AND c.data_hora_marcado = NEW.data_hora_marcado
          AND c.status <> 'CANCELADA'
          AND c.id_consulta <> COALESCE(NEW.id_consulta, -1)
    ) THEN
        RAISE EXCEPTION 'A sala já está ocupada no horário %.',
            to_char(NEW.data_hora_marcado, 'DD/MM/YYYY HH24:MI');
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


-- ================================================================================
-- GATILHO 2: Validação da Grade de Horários do Médico
-- Tabela: consulta
-- Momento: BEFORE INSERT OR UPDATE
-- ================================================================================
-- Garante que a consulta seja marcada apenas em um dia e horário em que o
-- médico realmente atenda (conforme a tabela horario_medico e horario).
CREATE OR REPLACE FUNCTION fn_valida_horario_medico()
RETURNS TRIGGER AS $$
DECLARE
    v_dia_semana TEXT;
    v_hora       TIME;
BEGIN
    -- Se a consulta foi cancelada, não precisa validar grade
    IF NEW.status = 'CANCELADA' THEN
        RETURN NEW;
    END IF;

    IF NEW.data_hora_marcado IS NULL THEN
        RAISE EXCEPTION 'Informe a data e a hora da consulta.';
    END IF;

    -- Converte o dia da semana da data marcada (0=Domingo, 1=Segunda ... 6=Sábado)
    v_dia_semana := CASE EXTRACT(DOW FROM NEW.data_hora_marcado)::INT
        WHEN 0 THEN 'DOMINGO'
        WHEN 1 THEN 'SEGUNDA'
        WHEN 2 THEN 'TERCA'
        WHEN 3 THEN 'QUARTA'
        WHEN 4 THEN 'QUINTA'
        WHEN 5 THEN 'SEXTA'
        WHEN 6 THEN 'SABADO'
    END;

    -- Extrai apenas a hora da consulta
    v_hora := NEW.data_hora_marcado::TIME;

    -- Verifica se o médico possui expediente cadastrado para esse dia e horário
    IF NOT EXISTS (
        SELECT 1
        FROM horario_medico hm
        JOIN horario h ON h.id_horario = hm.id_horario
        WHERE hm.id_medico = NEW.id_medico
          AND UPPER(h.dia_semana) = v_dia_semana
          AND v_hora >= h.hora_inicio
          AND v_hora <  h.hora_fim
    ) THEN
        RAISE EXCEPTION 'O médico não atende em % às %.',
            v_dia_semana, to_char(v_hora, 'HH24:MI');
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


-- ================================================================================
-- GATILHO 3: Atualização Automática do Valor de Procedimentos na Conta
-- Tabela: consulta_procedimento
-- Momento: AFTER INSERT OR UPDATE OR DELETE
-- ================================================================================
-- Sempre que um procedimento for adicionado, alterado ou excluído de uma consulta,
-- este gatilho recalcula o total dos procedimentos e atualiza a tabela conta.
CREATE OR REPLACE FUNCTION fn_atualiza_valor_procedimento_conta()
RETURNS TRIGGER AS $$
DECLARE
    v_consulta_old INTEGER;
    v_consulta_new INTEGER;
BEGIN
    -- Identifica o id_consulta afetado antes e/ou depois da operação
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        v_consulta_old := OLD.id_consulta;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_consulta_new := NEW.id_consulta;
    END IF;

    -- Recalcula o total de procedimentos somando (quantidade * valor) de cada um
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

    RETURN NULL; -- Gatilho AFTER: o valor de retorno é ignorado
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_atualiza_valor_procedimento_conta ON consulta_procedimento;
CREATE TRIGGER trg_atualiza_valor_procedimento_conta
AFTER INSERT OR UPDATE OR DELETE
ON consulta_procedimento
FOR EACH ROW
EXECUTE FUNCTION fn_atualiza_valor_procedimento_conta();


-- ================================================================================
-- GATILHO 4: Validação de Pagamentos
-- Tabela: pagamento
-- Momento: BEFORE INSERT OR UPDATE
-- ================================================================================
-- Garante a integridade financeira:
--   * O pagamento deve estar vinculado a uma conta;
--   * Não são permitidos valores negativos;
--   * O pagamento deve conter algum valor maior que zero;
--   * A soma dos pagamentos não pode ultrapassar o valor total da conta.
CREATE OR REPLACE FUNCTION fn_valida_pagamento()
RETURNS TRIGGER AS $$
DECLARE
    v_total_conta NUMERIC(10,2);
    v_ja_pago     NUMERIC(10,2);
    v_novo_pago   NUMERIC(10,2);
BEGIN
    -- 1. Verifica vínculo obrigatório com a conta
    IF NEW.id_conta IS NULL THEN
        RAISE EXCEPTION 'O pagamento precisa estar vinculado a uma conta.';
    END IF;

    -- 2. Impede valores negativos
    IF COALESCE(NEW.valor_pago, 0) < 0 OR COALESCE(NEW.valor_convenio, 0) < 0 THEN
        RAISE EXCEPTION 'Os valores do pagamento não podem ser negativos.';
    END IF;

    -- 3. Calcula o valor total deste novo lançamento
    v_novo_pago := COALESCE(NEW.valor_pago, 0) + COALESCE(NEW.valor_convenio, 0);

    IF v_novo_pago <= 0 THEN
        RAISE EXCEPTION 'O pagamento deve ter um valor maior que zero.';
    END IF;

    -- 4. Obtém o valor total da conta
    SELECT COALESCE(valor_total, valor_consulta + valor_procedimento, 0)
      INTO v_total_conta
      FROM conta
     WHERE id_conta = NEW.id_conta;

    -- 5. Calcula o valor total já pago nesta conta anteriormente
    -- (exclui o registro atual caso seja um UPDATE)
    SELECT COALESCE(SUM(COALESCE(valor_pago, 0) + COALESCE(valor_convenio, 0)), 0)
      INTO v_ja_pago
      FROM pagamento
     WHERE id_conta = NEW.id_conta
       AND id_pagamento <> COALESCE(NEW.id_pagamento, -1);

    -- 6. Impede que o total pago ultrapasse o total da conta
    IF (v_ja_pago + v_novo_pago) > v_total_conta THEN
        RAISE EXCEPTION 'O pagamento ultrapassa o valor total da conta (Total: R$ %, Já pago: R$ %, Restante: R$ %).',
            replace(to_char(v_total_conta, 'FM99999990.00'), '.', ','),
            replace(to_char(v_ja_pago, 'FM99999990.00'), '.', ','),
            replace(to_char(v_total_conta - v_ja_pago, 'FM99999990.00'), '.', ',');
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
