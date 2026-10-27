/*
 * Filtra as linhas de uma tabela pelo texto digitado, sem ir ao servidor.
 *
 *   <input type="search" data-filtro-tabela="#tabela-pacientes">
 *
 * A busca ignora maiúsculas e acentos ("joao" encontra "João") e não olha a
 * coluna de botões (td.coluna-acoes). Se a tabela tiver uma linha
 * <tr data-sem-resultado hidden>, ela aparece quando nada combinar.
 */
(function () {
  'use strict';

  function normalizar(texto) {
    return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  function textoDaLinha(linha) {
    return Array.from(linha.cells)
      .filter(function (celula) { return !celula.classList.contains('coluna-acoes'); })
      .map(function (celula) { return celula.textContent; })
      .join(' ');
  }

  function filtrar(campo) {
    const tabela = document.querySelector(campo.dataset.filtroTabela);
    if (!tabela) return;

    const termo = normalizar(campo.value);
    let visiveis = 0;

    tabela.querySelectorAll('tbody tr:not([data-sem-resultado])').forEach(function (linha) {
      const combina = normalizar(textoDaLinha(linha)).includes(termo);
      linha.hidden = !combina;
      if (combina) visiveis++;
    });

    const semResultado = tabela.querySelector('tr[data-sem-resultado]');
    if (semResultado) semResultado.hidden = visiveis > 0;
  }

  document.addEventListener('input', function (evento) {
    if (evento.target.matches('[data-filtro-tabela]')) filtrar(evento.target);
  });
})();
