/*
 * Comportamentos usados em todas as páginas.
 *
 * 1. Validação: formulários com class="needs-validation" e novalidate usam a
 *    validação do navegador, mas com o visual do Bootstrap (.was-validated).
 * 2. Confirmação: formulários com data-confirmar="Mensagem" abrem a janela
 *    #modal-confirmacao antes de enviar. data-confirmar-botao muda o texto do botão.
 * 3. Envio duplo: em formulários POST o botão é desabilitado depois do clique.
 *    Se o botão tiver data-enviando="Salvando...", o texto também muda.
 * 4. Avisos de sucesso somem sozinhos depois de alguns segundos.
 * 5. Elementos com data-mostrar-quando="campo=valor" aparecem só quando o
 *    campo indicado tem aquele valor.
 * 6. Botões com data-imprimir abrem a impressão da página.
 */
(function () {
  'use strict';

  const modal = document.getElementById('modal-confirmacao');
  let formularioAguardando = null;

  // Mostra a janela de confirmação. Retorna true se o envio pode seguir direto.
  function pedirConfirmacao(formulario) {
    const mensagem = formulario.dataset.confirmar || 'Confirma esta ação?';

    if (!modal || !window.bootstrap) {
      return window.confirm(mensagem);
    }

    formularioAguardando = formulario;
    modal.querySelector('[data-confirmacao-mensagem]').textContent = mensagem;
    modal.querySelector('[data-confirmacao-ok]').textContent = formulario.dataset.confirmarBotao || 'Excluir';
    bootstrap.Modal.getOrCreateInstance(modal).show();
    return false;
  }

  if (modal) {
    modal.querySelector('[data-confirmacao-ok]').addEventListener('click', function () {
      if (!formularioAguardando) return;
      const formulario = formularioAguardando;
      formularioAguardando = null;
      formulario.dataset.confirmado = 'sim';
      bootstrap.Modal.getInstance(modal).hide();
      formulario.requestSubmit();
    });
  }

  function travarBotao(botao) {
    // setTimeout: se o botão for desabilitado durante o evento, o navegador
    // deixa de enviar o name/value dele junto com o formulário
    setTimeout(function () {
      botao.disabled = true;
      botao.dataset.travado = 'sim';
      if (botao.dataset.enviando) {
        botao.dataset.textoOriginal = botao.innerHTML;
        botao.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>' +
          botao.dataset.enviando;
      }
    }, 0);
  }

  document.addEventListener('submit', function (evento) {
    const formulario = evento.target;

    // 1. validação
    if (formulario.classList.contains('needs-validation')) {
      formulario.classList.add('was-validated');
      if (!formulario.checkValidity()) {
        evento.preventDefault();
        const primeiroInvalido = formulario.querySelector(':invalid');
        if (primeiroInvalido) primeiroInvalido.focus();
        return;
      }
    }

    // 2. confirmação
    if (formulario.dataset.confirmar && formulario.dataset.confirmado !== 'sim') {
      if (!pedirConfirmacao(formulario)) {
        evento.preventDefault();
        return;
      }
    }
    delete formulario.dataset.confirmado;

    // 3. envio duplo
    if (formulario.method === 'post') {
      const botao = evento.submitter || formulario.querySelector('[type="submit"]');
      if (botao) travarBotao(botao);
    }
  });

  // Ao voltar com o botão "voltar" do navegador a página pode vir do cache
  // com os botões ainda travados
  window.addEventListener('pageshow', function (evento) {
    if (!evento.persisted) return;
    document.querySelectorAll('[data-travado]').forEach(function (botao) {
      botao.disabled = false;
      if (botao.dataset.textoOriginal) botao.innerHTML = botao.dataset.textoOriginal;
      delete botao.dataset.travado;
      delete botao.dataset.textoOriginal;
    });
  });

  // 4. avisos de sucesso
  if (window.bootstrap) {
    document.querySelectorAll('.area-avisos .alert-success').forEach(function (aviso) {
      setTimeout(function () {
        bootstrap.Alert.getOrCreateInstance(aviso).close();
      }, 6000);
    });
  }

  // 5. Partes do formulário que dependem de outro campo:
  //    <div data-mostrar-quando="perfil=MEDICO"> só aparece quando o campo
  //    name="perfil" vale MEDICO. Para checkbox, basta o nome: "possui_convenio".
  //    Os campos de uma parte oculta ficam desabilitados, então não são
  //    enviados nem validados.
  function atualizarDependentes() {
    document.querySelectorAll('[data-mostrar-quando]').forEach(function (bloco) {
      const partes = bloco.dataset.mostrarQuando.split('=');
      const escopo = bloco.closest('form') || document;
      const campo = escopo.querySelector('[name="' + partes[0] + '"]');
      if (!campo) return;

      const visivel = campo.type === 'checkbox' ? campo.checked : campo.value === partes[1];
      bloco.hidden = !visivel;
      bloco.querySelectorAll('input, select, textarea').forEach(function (c) {
        c.disabled = !visivel;
      });
    });
  }

  document.addEventListener('change', function (evento) {
    if (evento.target.name) atualizarDependentes();
  });
  atualizarDependentes();

  // 6. Botões com data-imprimir abrem a impressão do navegador (relatórios)
  document.addEventListener('click', function (evento) {
    if (evento.target.closest('[data-imprimir]')) window.print();
  });
})();
