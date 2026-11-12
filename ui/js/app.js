// SIAPP — início da interface: o que cada aba carrega, atalhos de teclado e ligação
// dos botões. Abas, divisão, janelas e preferências: janelas.js. Cada aba tem seu
// arquivo em ui/js/ (catalogo.js, documentos.js…).
"use strict";

// Ao mostrar cada aba, recarrega o que pode ter mudado.
const AO_ABRIR_ABA = {
  projeto: () => carregarInicio(),
  dados: () => carregarDados(),
  mapa: () => { carregarMapa(); carregarCamadas(); },
  docs: () => carregarDocumentos(),
  perfis: () => carregarPerfis(),
  interp: () => { if (ui.subInterp === "bloco") { carregarBloco(); carregarProducao(); } else carregarSecao(); },
  viab: () => carregarViabilidade(),
  comunidade: () => carregarComunidade(),
};

// Aba Dados: cadastro, levantamento, produção e camadas (o catálogo carrega ao conectar).
async function carregarDados() {
  if (!projetoAberto) {
    $("cad-info").textContent = "Abra o projeto primeiro (Início).";
    return;
  }
  const r = await chamar(null, "cadastro_info");
  if (r.ok) desenharCadastroInfo(r);
  preencherBaciasLevantamento([...$("sel-bacia").options].map((o) => o.value));
  carregarLevantamento();
  carregarProducao();
  carregarCamadas();
  if (ui.subDados === "consolidado") carregarConsolidado();
}

// O projeto fica aberto para todas as abas; aqui, só ajustes da tela inicial.
function aoAbrirProjeto(r) {
  $("ini-pasta").textContent = "Projeto aberto";
  $("ini-pasta").disabled = true;
  $("ini-pasta").hidden = true;
  $("ini-pasta-ajuda").textContent = r.pasta || "";
  $("cfg-pasta").textContent = r.pasta || "";
  mostrarProjetoNoTopo(r.pasta);
  carregarInicio();
}

function ligar(id, evento, fn) { $(id)[evento] = fn; }

async function iniciar() {
  if (api) return;
  api = window.pywebview.api;
  const r = await api.info();
  $("versao").textContent = "v" + r.versao;
  const ajuda = $("ini-pasta-ajuda");
  limpar(ajuda);
  ajuda.append("Tudo fica na pasta ", el("strong", "", r.nome_pasta_projeto),
               ", ao lado do aplicativo. O diálogo já abre nela: é só confirmar.");
  ajuda.title = r.pasta_projeto;
  const sel = $("sel-bacia");
  for (const b of r.bacias) {
    const o = document.createElement("option");
    o.value = o.textContent = b;
    sel.appendChild(o);
  }
  sel.value = "Sergipe";

  for (const b of document.querySelectorAll(".aba[data-vista]")) {
    b.onclick = () => { fecharMenus(); trocarAba(b.dataset.subInterp || b.dataset.vista); };
  }
  for (const b of document.querySelectorAll("[data-ir]")) b.onclick = () => trocarAba(b.dataset.ir);
  ligarJanelas();
  ligarInterface();
  ligarInicio();

  // projeto
  ligar("ini-pasta", "onclick", escolherPasta);
  $("cfg-pasta").textContent = r.pasta_projeto;

  // dados › catálogo
  ligar("btn-conectar", "onclick", conectar);
  ligar("filtro", "oninput", desenharPocos);
  ligar("g-fechar", "onclick", fecharGaveta);
  ligar("btn-baixar", "onclick", baixarSelecionados);
  ligar("dl-cancelar", "onclick", cancelarDownloads);
  // documentos
  ligar("btn-processar", "onclick", processarPendentes);
  ligar("btn-atualizar-docs", "onclick", carregarDocumentos);
  ligar("form-busca", "onsubmit", buscar);
  ligar("pg-fechar", "onclick", fecharPagina);
  ligar("pg-ant", "onclick", () => docAtual && abrirPagina(docAtual.rel, docAtual.pagina - 1, termoAtual));
  ligar("pg-prox", "onclick", () => docAtual && abrirPagina(docAtual.rel, docAtual.pagina + 1, termoAtual));
  ligar("pg-abrir", "onclick", () => docAtual && chamar($("pg-abrir"), "abrir_arquivo", docAtual.rel));
  ligar("pg-ampliar", "onclick", () => docAtual && abrirVisor(docAtual.rel, docAtual.pagina));
  ligar("pg-img", "ondblclick", () => docAtual && !$("tr-box").open && abrirVisor(docAtual.rel, docAtual.pagina));
  ligar("pg-processar", "onclick", processarEste);
  ligar("ed-form", "onsubmit", salvarCorrecao);
  ligar("ed-manter", "onclick", manterOriginal);
  ligar("ed-desfazer", "onclick", desfazerCorrecao);
  ligar("ed-adicionar", "onclick", adicionarDoEditor);
  ligar("ed-fechar", "onclick", fecharEditor);
  ligar("form-palavra", "onsubmit", adicionarPalavra);
  ligarTranscricao();
  ligarVisor();
  ligar("tolerante", "onchange", () => termoAtual && $("busca").value.trim() && buscar());
  ligarDocumentos();
  // mapa e comunidade
  ligarMapa();
  ligarPerfis();
  ligarSecao();
  ligarBloco();
  ligarExternos();
  ligarComunidade();
  ligarConsolidado();
  ligar("ocr-cancelar", "onclick", async () => {
    await chamar($("ocr-cancelar"), "cancelar_processamento");
    status("Cancelando o processamento…", "trab");
  });

  document.addEventListener("keydown", (e) => {
    // F3 / Shift+F3: próximo / anterior achado da busca (documentos)
    if (e.key === "F3" && !$("vista-docs").hidden && achados.length) {
      e.preventDefault();
      irAchado(e.shiftKey ? -1 : 1);
      return;
    }
    if (e.key !== "Escape") return;
    if (visorAberto()) fecharVisor();
    else if (!$("config").hidden) $("config").hidden = true;
    else if (![...document.querySelectorAll(".popover")].every((p) => p.hidden)) {
      for (const p of document.querySelectorAll(".popover")) p.hidden = true;
    } else if (!$("vista-docs").hidden) {
      if (!$("pg-edicao").hidden) { if (!edicaoPaginaSuja()) cancelarEdicaoPagina(); }
      else if (!$("editor").hidden) fecharEditor();
      else if (!$("painel-pagina").hidden) fecharPagina();
    } else if (!$("vista-dados").hidden && !$("gaveta").hidden) fecharGaveta();
    else if (!$("vista-mapa").hidden && !$("ficha").hidden) fecharFicha();
  });

  // preferências (cores, arranjo) antes de mostrar a primeira aba
  await carregarPreferencias();
  atualizarTeclasVisiveis();
  if (typeof preencherAparencia === "function") preencherAparencia();
  const est = await chamar(null, "estado");
  if (est.ok && est.projeto_aberto) {
    liberarProjeto({ pasta: est.pasta });          // janela destacada (ou recarregada): o projeto já está aberto
  }
  aplicarLayout(new Set(abasVisiveis()));
  if (MODO_JANELA) {
    status(projetoAberto ? `${NOMES_ABAS[MODO_JANELA]} em janela própria.` : "Abra o projeto na janela principal.");
    return;
  }
  if (!projetoAberto && est.ok && est.existe_projeto && prefs && prefs.abrir_ao_iniciar) {
    if (await abrirProjetoSozinho()) chamar(null, "restaurar_janelas");
    avisarAtualizacao();
    return;
  }
  if (projetoAberto) chamar(null, "restaurar_janelas");
  avisarAtualizacao();
  status("Pronto. Comece abrindo o projeto (Início).");
}

window.addEventListener("pywebviewready", iniciar);
if (window.pywebview && window.pywebview.api && window.pywebview.api.info) iniciar();
setTimeout(() => {
  if (!api) status("Motor não encontrado. Abra o SIAPP pelo arquivo iniciar.bat (ou python siapp.py).", "erro");
}, 4000);
