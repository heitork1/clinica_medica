/*
 * Listas em que o usuário adiciona e remove linhas (telefones, convênios,
 * procedimentos). Estrutura esperada:
 *
 *   <div data-linhas data-linhas-minimo="1">
 *     <div data-linhas-lista>
 *       <div class="linha-dinamica"> ...campos... <button type="button" data-remover-linha>
 *     </div>
 *     <template data-linhas-modelo> <div class="linha-dinamica">...</div> </template>
 *     <button type="button" data-adicionar-linha>Adicionar</button>
 *   </div>
 *
 * Os campos de cada linha repetem o mesmo name; no Flask são lidos com
 * request.form.getlist("nome_do_campo"). Evite checkbox dentro das linhas:
 * checkbox desmarcado não é enviado e desalinha as listas.
 *
 * A cada mudança o grupo dispara o evento "linhas:alteradas" (usado, por
 * exemplo, para recalcular o subtotal dos procedimentos).
 */
(function () {
  'use strict';

  function linhasDe(grupo) {
    return grupo.querySelectorAll('[data-linhas-lista] > .linha-dinamica');
  }

  // Desabilita os botões de remover quando a lista chega ao mínimo
  function atualizarBotoes(grupo) {
    const minimo = Number(grupo.dataset.linhasMinimo || 0);
    const linhas = linhasDe(grupo);
    linhas.forEach(function (linha) {
      const botao = linha.querySelector('[data-remover-linha]');
      if (botao) botao.disabled = linhas.length <= minimo;
    });
  }

  function avisarMudanca(grupo) {
    atualizarBotoes(grupo);
    grupo.dispatchEvent(new CustomEvent('linhas:alteradas', { bubbles: true }));
  }

  function adicionarLinha(grupo) {
    const modelo = grupo.querySelector('template[data-linhas-modelo]');
    const lista = grupo.querySelector('[data-linhas-lista]');
    const nova = modelo.content.cloneNode(true);
    const primeiroCampo = nova.querySelector('input, select, textarea');

    lista.appendChild(nova);
    if (primeiroCampo) primeiroCampo.focus();
    avisarMudanca(grupo);
  }

  document.addEventListener('click', function (evento) {
    const botaoAdicionar = evento.target.closest('[data-adicionar-linha]');
    if (botaoAdicionar) {
      adicionarLinha(botaoAdicionar.closest('[data-linhas]'));
      return;
    }

    const botaoRemover = evento.target.closest('[data-remover-linha]');
    if (botaoRemover) {
      const grupo = botaoRemover.closest('[data-linhas]');
      botaoRemover.closest('.linha-dinamica').remove();
      avisarMudanca(grupo);
    }
  });

  document.querySelectorAll('[data-linhas]').forEach(atualizarBotoes);
})();
