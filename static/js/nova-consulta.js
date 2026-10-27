/*
 * Tela de nova consulta (templates/consultas/nova.html).
 *
 * - "Procurar" filtra a lista de pacientes por nome ou CPF.
 * - "Especialidade" filtra a lista de médicos (atributo data-especialidades).
 * - Ao escolher médico e data, busca os horários livres em
 *   /consultas/horarios-livres (JSON) e preenche a lista de horários.
 */
(function () {
  'use strict';

  const formulario = document.querySelector('[data-nova-consulta]');
  if (!formulario) return;

  const filtroPaciente = formulario.querySelector('#filtro-paciente');
  const selectPaciente = formulario.querySelector('#campo-id_paciente');
  const filtroEspecialidade = formulario.querySelector('#filtro-especialidade');
  const selectMedico = formulario.querySelector('#campo-id_medico');
  const campoData = formulario.querySelector('#campo-data');
  const selectHora = formulario.querySelector('#campo-hora');
  const aviso = formulario.querySelector('#aviso-horarios');
  const textoAvisoInicial = aviso.textContent.trim();

  function normalizar(texto) {
    return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  // ------------------------------------------------------------ pacientes
  filtroPaciente.addEventListener('input', function () {
    const termo = normalizar(filtroPaciente.value);
    const digitos = termo.replace(/\D/g, '');
    const visiveis = [];

    Array.from(selectPaciente.options).forEach(function (opcao) {
      if (!opcao.value) return;
      const texto = opcao.textContent;
      const combina = normalizar(texto).includes(termo) ||
        (digitos.length >= 3 && texto.replace(/\D/g, '').includes(digitos));
      opcao.hidden = !combina;
      if (combina) visiveis.push(opcao);
    });

    // um único resultado já fica escolhido; escolha que sumiu do filtro é desfeita
    if (visiveis.length === 1) {
      selectPaciente.value = visiveis[0].value;
    } else if (selectPaciente.selectedOptions[0] && selectPaciente.selectedOptions[0].hidden) {
      selectPaciente.value = '';
    }
  });

  // -------------------------------------------------------------- médicos
  filtroEspecialidade.addEventListener('change', function () {
    const id = filtroEspecialidade.value;
    Array.from(selectMedico.options).forEach(function (opcao) {
      if (!opcao.value) return;
      const especialidades = (opcao.dataset.especialidades || '').split(',');
      opcao.hidden = id !== '' && !especialidades.includes(id);
    });
    if (selectMedico.selectedOptions[0] && selectMedico.selectedOptions[0].hidden) {
      selectMedico.value = '';
      carregarHorarios();
    }
  });

  // ------------------------------------------------------------- horários
  function preencherHorarios(horarios, placeholder) {
    const anterior = selectHora.value || selectHora.dataset.selecionado;
    selectHora.innerHTML = '';
    selectHora.add(new Option(placeholder, ''));
    horarios.forEach(function (hora) {
      selectHora.add(new Option(hora, hora));
    });
    selectHora.disabled = horarios.length === 0;
    if (anterior && horarios.includes(anterior)) selectHora.value = anterior;
    selectHora.dataset.selecionado = '';
  }

  function carregarHorarios() {
    if (!selectMedico.value || !campoData.value) {
      preencherHorarios([], 'Escolha médico e data');
      aviso.textContent = textoAvisoInicial;
      return;
    }

    preencherHorarios([], 'Carregando...');
    const url = formulario.dataset.urlHorarios + '?' +
      new URLSearchParams({ id_medico: selectMedico.value, data: campoData.value });

    fetch(url, { headers: { Accept: 'application/json' } })
      .then(function (resposta) { return resposta.json(); })
      .then(function (dados) {
        preencherHorarios(dados.horarios, dados.horarios.length ? 'Selecione...' : 'Sem horários livres');
        aviso.textContent = dados.aviso ||
          dados.horarios.length + ' horário' + (dados.horarios.length === 1 ? ' livre' : 's livres') + ' neste dia.';
      })
      .catch(function () {
        preencherHorarios([], 'Indisponível');
        aviso.textContent = 'Não foi possível carregar os horários. Recarregue a página e tente de novo.';
      });
  }

  selectMedico.addEventListener('change', carregarHorarios);
  campoData.addEventListener('change', carregarHorarios);

  // volta de um erro do servidor com médico e data preenchidos
  carregarHorarios();
})();
