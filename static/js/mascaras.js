/*
 * Máscaras de digitação: <input data-mascara="cpf | telefone | moeda">
 *
 * O evento é escutado no document, então funciona também em campos criados
 * depois do carregamento (linhas dinâmicas). CPF e telefone marcam o campo
 * como inválido (setCustomValidity) enquanto estiverem incompletos ou errados.
 *
 * As funções ficam disponíveis em window.Mascaras para outros scripts.
 */
window.Mascaras = (function () {
  'use strict';

  function somenteDigitos(texto) {
    return (texto || '').replace(/\D/g, '');
  }

  // 12345678909 -> 123.456.789-09
  function formatarCpf(valor) {
    const d = somenteDigitos(valor).slice(0, 11);
    let saida = d.slice(0, 3);
    if (d.length > 3) saida += '.' + d.slice(3, 6);
    if (d.length > 6) saida += '.' + d.slice(6, 9);
    if (d.length > 9) saida += '-' + d.slice(9, 11);
    return saida;
  }

  // 47991234567 -> (47) 99123-4567   |   4733334444 -> (47) 3333-4444
  function formatarTelefone(valor) {
    const d = somenteDigitos(valor).slice(0, 11);
    if (d.length === 0) return '';
    if (d.length <= 2) return '(' + d;

    const ddd = d.slice(0, 2);
    const numero = d.slice(2);
    const corte = d.length === 11 ? 5 : 4; // celular tem 9 dígitos, fixo tem 8
    if (numero.length <= corte) return '(' + ddd + ') ' + numero;
    return '(' + ddd + ') ' + numero.slice(0, corte) + '-' + numero.slice(corte);
  }

  // Os dígitos entram pela direita, como em caixa eletrônico: 123456 -> 1.234,56
  function formatarMoeda(valor) {
    const d = somenteDigitos(valor).replace(/^0+/, '');
    if (!d) return '';
    const completo = d.padStart(3, '0');
    const inteiro = completo.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return inteiro + ',' + completo.slice(-2);
  }

  // "1.234,56" -> 1234.56
  function moedaParaNumero(texto) {
    const d = somenteDigitos(texto);
    return d ? Number(d) / 100 : 0;
  }

  function cpfValido(valor) {
    const d = somenteDigitos(valor);
    if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;

    // confere os dois dígitos verificadores
    for (let tamanho = 9; tamanho <= 10; tamanho++) {
      let soma = 0;
      for (let i = 0; i < tamanho; i++) {
        soma += Number(d[i]) * (tamanho + 1 - i);
      }
      const digito = (soma * 10) % 11 % 10;
      if (digito !== Number(d[tamanho])) return false;
    }
    return true;
  }

  // Troca o valor mantendo o cursor depois do mesmo dígito em que estava
  function aplicar(campo, formatar) {
    const novo = formatar(campo.value);
    if (novo === campo.value) return;

    const editando = document.activeElement === campo;
    const digitosAntesDoCursor = editando
      ? somenteDigitos(campo.value.slice(0, campo.selectionStart)).length
      : 0;

    campo.value = novo;
    if (!editando) return;

    let posicao = 0;
    let contados = 0;
    while (posicao < novo.length && contados < digitosAntesDoCursor) {
      if (/\d/.test(novo[posicao])) contados++;
      posicao++;
    }
    campo.setSelectionRange(posicao, posicao);
  }

  function formatarCampo(campo) {
    switch (campo.dataset.mascara) {
      case 'cpf':
        aplicar(campo, formatarCpf);
        campo.setCustomValidity(campo.value && !cpfValido(campo.value) ? 'CPF inválido.' : '');
        break;
      case 'telefone': {
        aplicar(campo, formatarTelefone);
        const digitos = somenteDigitos(campo.value).length;
        campo.setCustomValidity(campo.value && digitos < 10 ? 'Telefone incompleto.' : '');
        break;
      }
      case 'moeda':
        campo.value = formatarMoeda(campo.value); // na moeda o cursor fica sempre no fim
        break;
    }
  }

  document.addEventListener('input', function (evento) {
    if (evento.target.matches('[data-mascara]')) formatarCampo(evento.target);
  });

  // formata os valores que já vieram preenchidos do servidor
  document.querySelectorAll('[data-mascara]').forEach(formatarCampo);

  return {
    somenteDigitos: somenteDigitos,
    formatarCpf: formatarCpf,
    formatarTelefone: formatarTelefone,
    formatarMoeda: formatarMoeda,
    moedaParaNumero: moedaParaNumero,
    cpfValido: cpfValido,
    formatarCampo: formatarCampo
  };
})();
