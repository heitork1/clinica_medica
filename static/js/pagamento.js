/*
 * Registro de pagamento (templates/consultas/conta.html).
 *
 * - Enquanto o valor do paciente não é alterado à mão, ele completa o saldo:
 *   ao digitar a parte do convênio, a parte do paciente vira saldo - convênio.
 * - A forma de pagamento só é obrigatória quando o paciente paga algum valor.
 * - Mostra o total do pagamento e o saldo que sobra, e marca o campo como
 *   inválido se o pagamento passar do saldo (o servidor confere de novo).
 */
(function () {
  'use strict';

  const formulario = document.querySelector('[data-pagamento]');
  if (!formulario) return;

  const real = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const saldo = Math.round(Number(formulario.dataset.saldo) * 100);
  const possuiConvenio = formulario.querySelector('[name="possui_convenio"]');
  const campoConvenio = formulario.querySelector('[name="valor_convenio"]');
  const campoPaciente = formulario.querySelector('[name="valor_pago"]');
  const campoForma = formulario.querySelector('[name="forma_pagamento"]');
  const resumo = formulario.querySelector('[data-resumo-pagamento]');
  let pacienteAlterado = false;

  function centavos(campo) {
    return Math.round(Mascaras.moedaParaNumero(campo.value) * 100);
  }

  function escreverCentavos(campo, valor) {
    campo.value = valor > 0 ? Mascaras.formatarMoeda(String(valor)) : '0,00';
  }

  function atualizar(evento) {
    if (evento && evento.target === campoPaciente) pacienteAlterado = true;

    const comConvenio = possuiConvenio && possuiConvenio.checked;
    const convenio = comConvenio && campoConvenio ? centavos(campoConvenio) : 0;

    if (!pacienteAlterado && evento && evento.target !== campoPaciente) {
      escreverCentavos(campoPaciente, Math.max(saldo - convenio, 0));
    }

    const paciente = centavos(campoPaciente);
    const total = convenio + paciente;
    const passou = total > saldo;

    campoForma.required = paciente > 0;
    campoPaciente.setCustomValidity(passou ? 'O pagamento passa do saldo da conta.' : '');
    resumo.textContent = 'Este pagamento: ' + real.format(total / 100) +
      ' · Saldo depois dele: ' + real.format(Math.max(saldo - total, 0) / 100);
    resumo.classList.toggle('text-danger', passou);
  }

  formulario.addEventListener('input', atualizar);
  formulario.addEventListener('change', atualizar);
  atualizar();
})();
