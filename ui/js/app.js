// SIAPP — início da interface: abas, atalhos de teclado e ligação dos botões.
// Cada aba tem seu arquivo em ui/js/ (catalogo.js, documentos.js…).
"use strict";

// Ao abrir cada aba, recarrega o que pode ter mudado.
const AO_ABRIR_ABA = {
  catalogo: () => {},
  docs: () => carregarDocumentos(),
};

function trocarAba(qual) {
  for (const b of document.querySelectorAll(".aba[data-vista]")) {
    const ativa = b.dataset.vista === qual;
    b.classList.toggle("ativa", ativa);
    b.setAttribute("aria-selected", ativa);
    $("vista-" + b.dataset.vista).hidden = !ativa;
  }
  (AO_ABRIR_ABA[qual] || (() => {}))();
}

function ligar(id, evento, fn) { $(id)[evento] = fn; }

async function iniciar() {
  if (api) return;
  api = window.pywebview.api;
  const r = await api.info();
  $("versao").textContent = "v" + r.versao;
  const ajuda = $("ajuda-pasta");
  ajuda.textContent = "Por enquanto, sempre a pasta ";
  ajuda.append(el("strong", "", r.nome_pasta_projeto),
               ", ao lado do aplicativo. O diálogo já abre nela: é só confirmar.");
  ajuda.title = r.pasta_projeto;
  const sel = $("sel-bacia");
  for (const b of r.bacias) {
    const o = document.createElement("option");
    o.value = o.textContent = b;
    sel.appendChild(o);
  }
  sel.value = "Sergipe";

  for (const b of document.querySelectorAll(".aba[data-vista]")) b.onclick = () => trocarAba(b.dataset.vista);

  // catálogo
  ligar("btn-pasta", "onclick", escolherPasta);
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
  ligar("ed-form", "onsubmit", salvarCorrecao);
  ligar("ed-manter", "onclick", manterOriginal);
  ligar("ed-desfazer", "onclick", desfazerCorrecao);
  ligar("ed-adicionar", "onclick", adicionarDoEditor);
  ligar("ed-fechar", "onclick", fecharEditor);
  ligar("form-palavra", "onsubmit", adicionarPalavra);
  ligar("tolerante", "onchange", () => termoAtual && $("busca").value.trim() && buscar());
  ligar("ocr-cancelar", "onclick", async () => {
    await chamar($("ocr-cancelar"), "cancelar_processamento");
    status("Cancelando o processamento…", "trab");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("vista-docs").hidden) {
      if (!$("editor").hidden) fecharEditor();
      else if (!$("painel-pagina").hidden) fecharPagina();
    } else if (!$("vista-catalogo").hidden && !$("gaveta").hidden) fecharGaveta();
  });
  status("Pronto. Comece escolhendo a pasta do projeto.");
}

window.addEventListener("pywebviewready", iniciar);
if (window.pywebview && window.pywebview.api && window.pywebview.api.info) iniciar();
setTimeout(() => {
  if (!api) status("Motor não encontrado. Abra o SIAPP pelo arquivo iniciar.bat (ou python siapp.py).", "erro");
}, 4000);
