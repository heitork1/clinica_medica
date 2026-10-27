/*
 * Tela de atendimento (templates/consultas/atendimento.html).
 *
 * Recalcula, a cada mudança, o valor unitário e o subtotal de cada
 * procedimento (pelo data-valor da opção escolhida), o total dos
 * procedimentos e o total da conta (procedimentos + valor da consulta).
 * O cálculo é só para conferência: quem grava os valores é o servidor.
 */
(function () {
  'use strict';

  const formulario = document.querySelector('[data-atendimento]');
  if (!formulario) return;

  const real = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  // valores em centavos para não acumular erro de ponto flutuante
  function centavos(texto) {
    return Math.round(Number(texto || 0) * 100);
  }

  function recalcular() {
    let totalProcedimentos = 0;

    formulario.querySelectorAll('[data-linhas-lista] > .linha-dinamica').forEach(function (linha) {
      const select = linha.querySelector('select[name="id_procedimento"]');
      const quantidade = Math.max(parseInt(linha.querySelector('input[name="quantidade"]').value, 10) || 0, 0);
      const opcao = select.selectedOptions[0];
      const unitario = opcao && opcao.value ? centavos(opcao.dataset.valor) : null;

      linha.querySelector('[data-valor-unitario]').textContent = unitario === null ? '—' : real.format(unitario / 100);
      linha.querySelector('[data-subtotal]').textContent =
        unitario === null ? '—' : real.format(unitario * quantidade / 100);
      if (unitario !== null) totalProcedimentos += unitario * quantidade;
    });

    const consulta = Math.round(Mascaras.moedaParaNumero(formulario.querySelector('[name="valor_consulta"]').value) * 100);
    formulario.querySelector('[data-total-procedimentos]').textContent = real.format(totalProcedimentos / 100);
    formulario.querySelector('[data-total-consulta]').textContent = real.format(consulta / 100);
    formulario.querySelector('[data-total-geral]').textContent = real.format((totalProcedimentos + consulta) / 100);
  }

  formulario.addEventListener('input', recalcular);
  formulario.addEventListener('change', recalcular);
  formulario.addEventListener('linhas:alteradas', recalcular);
  recalcular();
})();
