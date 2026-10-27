// SIAPP — aba Documentos: texto/OCR, busca, página, correções e dicionário.
"use strict";

let docs = [];                 // lista vinda do motor
let docAtual = null;           // {rel, pagina, n_paginas} da página aberta no painel
let termoAtual = "";
let paginaAtual = null;        // resposta de ver_pagina da página aberta
let achados = [];              // resultados da última busca, na ordem mostrada
let achadoAtual = -1;          // índice em `achados` da página aberta (-1: nenhum)
let verTexto = "final";        // "final" (arrumado) | "ocr" (como o OCR leu)
const gruposFechados = new Set();   // grupos da lista que o usuário fechou

const SITUACAO = {
  pendente: "sem texto — clique para ver",
  desatualizado: "arquivo mudou — processar de novo",
  processado: "",
};

function descreverDoc(d) {
  if (d.situacao !== "processado") return SITUACAO[d.situacao];
  const partes = [`${d.n_paginas} pág`];
  if (d.embutido) partes.push(`${d.embutido} com texto`);
  if (d.ocr) partes.push(`${d.ocr} por OCR`);
  return partes.join(" · ");
}

async function carregarDocumentos() {
  if (!projetoAberto) {
    $("docs-resumo").textContent = "Abra primeiro o projeto (aba Projeto).";
    return;
  }
  const r = await chamar(null, "documentos");
  if (!r.ok) return;
  docs = r.documentos;
  const pend = docs.filter((d) => d.situacao !== "processado");
  $("docs-resumo").textContent = docs.length
    ? `${docs.length} documento(s) · ${docs.length - pend.length} processado(s) · ${pend.length} pendente(s)`
    : "Nenhum PDF, TIF ou imagem baixado ainda. Baixe na aba Dados › Catálogo do REATE.";
  $("btn-processar").disabled = pend.length === 0;
  $("aviso-idioma").hidden = r.idioma_ok || pend.length === 0;
  preencherFiltrosDocs();
  desenharDocs();
  carregarAtalhos();
  carregarDicionario();
}

// ---------------------------------------------------- lista: filtro e grupos
function preencherFiltrosDocs() {
  const opcoes = (id, valores, rotuloTodos) => {
    const sel = $(id);
    const atual = sel.value;
    limpar(sel).appendChild(new Option(rotuloTodos, ""));
    for (const v of valores) sel.appendChild(new Option(v, v));
    sel.value = valores.includes(atual) ? atual : "";
  };
  const unicos = (f) => [...new Set(docs.map(f).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  opcoes("df-bacia", unicos((d) => d.bacia), "Todas as bacias");
  const bacia = $("df-bacia").value;
  opcoes("df-campo", unicos((d) => (!bacia || d.bacia === bacia) ? d.campo : ""), "Todos os campos");
}

function filtroDocs() {
  return { texto: norm($("df-texto").value.trim()), bacia: $("df-bacia").value, campo: $("df-campo").value,
           situacao: $("df-situacao").value };
}

function filtroAtivo() {
  const f = filtroDocs();
  return Boolean(f.texto || f.bacia || f.campo || f.situacao);
}

function docsFiltrados() {
  const f = filtroDocs();
  return docs.filter((d) => {
    if (f.bacia && d.bacia !== f.bacia) return false;
    if (f.campo && d.campo !== f.campo) return false;
    if (f.situacao === "revisado" ? !d.revisadas
        : f.situacao === "pendente" ? d.situacao === "processado"
        : f.situacao && d.situacao !== f.situacao) return false;
    if (f.texto && !norm(`${d.nome} ${d.poco} ${d.pasta} ${d.campo}`).includes(f.texto)) return false;
    return true;
  });
}

function botaoDoc(d) {
  const li = el("li");
  const b = el("button");
  b.dataset.rel = d.rel;
  b.title = `${d.rel}\n${tamanho(d.tamanho)}`;
  if (docAtual && docAtual.rel === d.rel) b.classList.add("ativo");
  const info = el("span", "d-info");
  if (!$("df-agrupar").value) info.append(el("span", "", d.poco || "—"));
  const sel = el("span", "selo" + (d.situacao === "processado" ? " ok" : ""), descreverDoc(d));
  sel.id = "sit-" + d.rel;
  info.appendChild(sel);
  if (d.revisadas) info.appendChild(el("span", "selo rev", `${d.revisadas} revisada(s)`));
  b.append(el("span", "d-nome", d.nome), info);
  b.onclick = () => abrirPagina(d.rel, 1, d.situacao === "processado" ? termoAtual : "");
  li.appendChild(b);
  return li;
}

function grupoDocs(chave, classe, rotulo, sub, n, abertoPadrao) {
  const g = el("details", "grupo-docs " + classe);
  g.dataset.chave = chave;
  g.open = filtroAtivo() || (gruposFechados.has(chave) ? false : abertoPadrao);
  const s = el("summary");
  s.append(el("span", "g-nome", rotulo));
  if (sub) s.append(el("span", "g-campo", sub));
  s.append(el("span", "contagem", String(n)));
  g.appendChild(s);
  g.addEventListener("toggle", () => {
    if (g.open) gruposFechados.delete(chave); else gruposFechados.add(chave);
  });
  return g;
}

function desenharDocs() {
  const caixa = limpar($("lista-docs"));
  const lista = docsFiltrados();
  const agrupar = $("df-agrupar").value;
  const filtrando = filtroAtivo();
  $("df-resumo").textContent = filtrando ? `${lista.length} de ${docs.length} documento(s) no filtro.` : "";
  $("df-limpar").hidden = !filtrando;
  atualizarEscopo();
  if (!lista.length) {
    if (docs.length) caixa.appendChild(el("p", "ajuda", "Nenhum documento neste filtro."));
    return;
  }
  if (!agrupar) {
    const ul = el("ul", "lista-docs");
    for (const d of lista) ul.appendChild(botaoDoc(d));
    caixa.appendChild(ul);
    return;
  }
  const porBacia = new Map();
  for (const d of lista) {
    const b = d.bacia || "Sem bacia";
    if (!porBacia.has(b)) porBacia.set(b, new Map());
    const pocos = porBacia.get(b);
    const p = d.poco || "—";
    if (!pocos.has(p)) pocos.set(p, []);
    pocos.get(p).push(d);
  }
  const muitos = lista.length > 40;
  for (const [bacia, pocos] of [...porBacia].sort((a, b) => a[0].localeCompare(b[0], "pt-BR"))) {
    const nb = [...pocos.values()].reduce((n, x) => n + x.length, 0);
    const gb = grupoDocs("b:" + bacia, "bacia", bacia, "", nb, true);
    for (const [poco, ds] of [...pocos].sort((a, b) => a[0].localeCompare(b[0], "pt-BR"))) {
      const temAtivo = docAtual && ds.some((d) => d.rel === docAtual.rel);
      const gp = grupoDocs(`p:${bacia}/${poco}`, "poco", poco, ds[0].campo || "", ds.length, !muitos || temAtivo);
      if (agrupar === "pasta") {
        const porPasta = new Map();
        for (const d of ds) {
          const k = d.pasta || "(raiz do poço)";
          if (!porPasta.has(k)) porPasta.set(k, []);
          porPasta.get(k).push(d);
        }
        for (const [pasta, dd] of [...porPasta].sort((a, b) => a[0].localeCompare(b[0], "pt-BR"))) {
          const gq = grupoDocs(`q:${bacia}/${poco}/${pasta}`, "pasta", pasta, "", dd.length, true);
          const ul = el("ul", "lista-docs");
          for (const d of dd) ul.appendChild(botaoDoc(d));
          gq.appendChild(ul);
          gp.appendChild(gq);
        }
      } else {
        const ul = el("ul", "lista-docs");
        for (const d of ds) ul.appendChild(botaoDoc(d));
        gp.appendChild(ul);
      }
      gb.appendChild(gp);
    }
    caixa.appendChild(gb);
  }
}

function limparFiltroDocs() {
  $("df-texto").value = "";
  $("df-bacia").value = $("df-campo").value = $("df-situacao").value = "";
  preencherFiltrosDocs();
  desenharDocs();
}

// "Buscar em": o rótulo diz quantos documentos entram em cada escopo
function atualizarEscopo() {
  const sel = $("busca-escopo");
  const n = docsFiltrados().filter((d) => d.situacao === "processado").length;
  sel.options[1].textContent = filtroAtivo() ? `só os do filtro ao lado (${n})` : "só os do filtro ao lado";
  sel.options[1].disabled = !filtroAtivo();
  sel.options[2].disabled = !(docAtual && docAtual.processado);
  sel.options[2].textContent = docAtual ? `só o documento aberto (${(docs.find((d) => d.rel === docAtual.rel) || {}).nome || "…"})` : "só o documento aberto";
  if (sel.selectedOptions[0] && sel.selectedOptions[0].disabled) sel.value = "todos";
}

function ligarDocumentos() {
  $("df-texto").oninput = desenharDocs;
  $("df-bacia").onchange = () => { preencherFiltrosDocs(); desenharDocs(); };
  for (const id of ["df-campo", "df-situacao", "df-agrupar"]) $(id).onchange = desenharDocs;
  $("df-limpar").onclick = limparFiltroDocs;
  $("busca-escopo").onchange = () => termoAtual && $("busca").value.trim() && buscar();
  $("pg-ir-form").onsubmit = (ev) => {
    ev.preventDefault();
    const n = parseInt($("pg-ir").value, 10);
    if (docAtual && n >= 1) abrirPagina(docAtual.rel, Math.min(n, docAtual.n_paginas), termoAtual);
  };
  $("ac-ant").onclick = () => irAchado(-1);
  $("ac-prox").onclick = () => irAchado(1);
  $("pg-ver-final").onclick = () => trocarVerTexto("final");
  $("pg-ver-ocr").onclick = () => trocarVerTexto("ocr");
  $("pg-editar").onclick = abrirEdicaoPagina;
  $("pg-copiar").onclick = copiarTextoPagina;
  $("pg-edicao-salvar").onclick = salvarEdicaoPagina;
  $("pg-edicao-cancelar").onclick = cancelarEdicaoPagina;
  $("pg-edicao-auto").onclick = voltarTextoAutomatico;
}

async function processarEste() {
  if (!docAtual) return;
  const r = await chamar($("pg-processar"), "processar_documentos", [docAtual.rel]);
  if (!r.ok) return;
  $("pg-processar").disabled = true;
  status("Documento na fila de processamento. O texto aparece aqui quando terminar.", "trab");
}

async function processarPendentes() {
  const rels = docs.filter((d) => d.situacao !== "processado").map((d) => d.rel);
  if (!rels.length) return;
  const r = await chamar($("btn-processar"), "processar_documentos", rels);
  if (r.ok) status(`${r.enfileirados} documento(s) na fila de processamento.`, "trab");
}

// Escopo da busca: todos, os documentos do filtro da lista (bacia, campo, poço, pasta…)
// ou só o documento aberto. null = todos.
function docsDoEscopo() {
  const escopo = $("busca-escopo").value;
  if (escopo === "este" && docAtual) return [docAtual.rel];
  if (escopo === "filtrados" && filtroAtivo())
    return docsFiltrados().filter((d) => d.situacao === "processado").map((d) => d.rel);
  return null;
}

async function buscar(ev) {
  if (ev) ev.preventDefault();
  const termo = $("busca").value.trim();
  if (!termo) return;
  termoAtual = termo;
  $("atalhos-box").open = false;   // abre espaço para os resultados; um clique reabre
  const escopo = docsDoEscopo();
  const r = await chamar($("btn-buscar"), "buscar_documentos", termo, $("tolerante").checked, escopo);
  if (!r.ok) return;
  const ul = $("resultados");
  ul.innerHTML = "";
  const resumo = $("busca-resumo");
  const onde = escopo === null ? "" : escopo.length === 1 && docAtual && escopo[0] === docAtual.rel
    ? " neste documento" : ` nos ${escopo.length} documento(s) do filtro`;
  resumo.textContent = r.resultados.length
    ? `${r.resultados.length} página(s) em ${r.documentos} documento(s) para “${termo}”${onde}.`
    : `Nada encontrado para “${termo}”${onde}. Os documentos pendentes ainda não entram na busca.`;
  if (r.expansoes && r.expansoes.length) {
    const v = el("span", "variacoes", " Também procurei, como possível erro de OCR: ");
    r.expansoes.forEach((e, i) => {
      if (i) v.appendChild(document.createTextNode(" · "));
      e.variacoes.forEach((x, j) => {
        if (j) v.appendChild(document.createTextNode(", "));
        v.appendChild(el("code", "", x));
      });
    });
    resumo.appendChild(v);
  }
  // num documento só, na ordem das páginas; em vários, por relevância
  achados = escopo && escopo.length === 1 ? [...r.resultados].sort((a, b) => a.pagina - b.pagina) : r.resultados;
  achadoAtual = -1;
  achados.forEach((res, i) => {
    const li = el("li");
    const b = el("button");
    b.dataset.i = i;
    const cab = el("span", "r-cab");
    cab.append(el("strong", "", res.poco || "—"), el("span", "", res.arquivo),
               el("span", "", `pág ${res.pagina}`),
               el("span", "selo" + (res.metodo === "ocr" ? "" : " ok"), res.metodo === "ocr" ? "OCR" : "texto"));
    b.appendChild(cab);
    if (res.titulo) b.appendChild(el("span", "r-titulo", res.titulo));
    b.appendChild(trechoComDestaque(res.trecho));
    b.onclick = () => irAchado(0, i);
    li.appendChild(b);
    ul.appendChild(li);
  });
  if (docAtual) marcarAchado(docAtual.rel, docAtual.pagina);
}

// Anda pelos achados da busca, de documento em documento (‹ anterior · próximo ›).
function irAchado(delta, indice) {
  if (!achados.length) return;
  const i = indice !== undefined ? indice : Math.max(0, Math.min(achados.length - 1, achadoAtual + delta));
  if (indice === undefined && achadoAtual < 0 && delta < 0) return;
  const res = achados[i];
  achadoAtual = i;
  abrirPagina(res.doc, res.pagina, termoAtual);
}

function marcarAchado(rel, pagina) {
  const i = achados.findIndex((x) => x.doc === rel && x.pagina === pagina);
  if (i >= 0) achadoAtual = i;
  document.querySelectorAll(".resultados button.ativo").forEach((x) => x.classList.remove("ativo"));
  const box = $("pg-achados");
  box.hidden = !achados.length;
  if (!achados.length) return;
  const noAchado = i >= 0;
  $("ac-num").textContent = noAchado ? `achado ${i + 1} de ${achados.length}` : `${achados.length} achado(s)`;
  $("ac-termo").textContent = `“${termoAtual}”` + (noAchado ? "" : " — esta página não está entre eles");
  $("ac-ant").disabled = !noAchado ? achadoAtual < 0 : i <= 0;
  $("ac-prox").disabled = noAchado ? i >= achados.length - 1 : false;
  if (noAchado) {
    const b = document.querySelector(`.resultados button[data-i="${i}"]`);
    if (b) { b.classList.add("ativo"); b.scrollIntoView({ block: "nearest" }); }
  }
}

// O motor marca o termo com \x01 … \x02. Montamos o destaque com nós de texto
// (nunca innerHTML): o texto vem de OCR e pode conter qualquer caractere.
function trechoComDestaque(trecho) {
  const p = el("span", "r-trecho");
  for (const pedaco of trecho.split("\x01")) {
    const [marcado, resto] = pedaco.includes("\x02") ? pedaco.split("\x02") : [null, pedaco];
    if (marcado !== null) p.appendChild(el("mark", "", marcado));
    if (resto) p.appendChild(document.createTextNode(resto));
  }
  return p;
}

let pedidoPagina = 0;
async function abrirPagina(rel, pagina, termo) {
  if (edicaoPaginaSuja()) {
    mensagemEdicao("Salve ou cancele a edição do texto antes de sair desta página.");
    $("pg-edicao-texto").focus();
    return;
  }
  const meu = ++pedidoPagina;
  $("painel-pagina").hidden = false;
  $("pg-num").textContent = "carregando…";
  const r = await chamar(null, "ver_pagina", rel, pagina, termo || "");
  if (meu !== pedidoPagina || !r.ok) return;
  paginaAtual = r;
  docAtual = { rel: r.rel, pagina: r.pagina, n_paginas: r.n_paginas, processado: r.processado };
  $("pg-nome").textContent = r.nome;
  $("pg-sub").textContent = r.titulo || "";
  $("pg-num").textContent = `pág ${r.pagina} de ${r.n_paginas}`;
  $("pg-ir").value = "";
  $("pg-ir").max = r.n_paginas;
  $("pg-ir").placeholder = String(r.pagina);
  $("pg-ir-form").hidden = r.n_paginas < 3;
  $("pg-ant").disabled = r.pagina <= 1;
  $("pg-prox").disabled = r.pagina >= r.n_paginas;
  $("pg-aviso").hidden = r.metodo !== "ocr";
  $("pg-pendente").hidden = r.processado;
  $("pg-processar").disabled = false;
  $("pg-texto-box").hidden = !r.processado;
  $("pg-img").src = r.imagem;
  iniciarTranscricao(r);
  fecharEditor();
  fecharEdicaoPagina();
  desenharTextoPagina();
  if (aposRedesenhar) { const f = aposRedesenhar; aposRedesenhar = null; f(); }
  document.querySelectorAll("#lista-docs button").forEach((b) => b.classList.toggle("ativo", b.dataset.rel === r.rel));
  marcarAchado(r.rel, r.pagina);
  atualizarEscopo();
}

function fecharPagina() {
  if (edicaoPaginaSuja()) {
    mensagemEdicao("Salve ou cancele a edição do texto antes de fechar a página.");
    return;
  }
  fecharEdicaoPagina();
  $("painel-pagina").hidden = true;
  docAtual = null;
  paginaAtual = null;
  pedidoPagina++;
  document.querySelectorAll("#lista-docs button.ativo, .resultados button.ativo").forEach((b) => b.classList.remove("ativo"));
  atualizarEscopo();
}

// ------------------------------------------- texto da página: arrumado, OCR, edição
const MODO_TEXTO = {
  remontado: ["texto arrumado", "Linhas, colunas e parágrafos remontados pelas posições das palavras na página"],
  ocr: ["como o OCR leu", ""],
  revisado: ["revisado", ""],
};

function desenharTextoPagina() {
  const r = paginaAtual;
  if (!r || !r.processado) return;
  const modo = MODO_TEXTO[r.modo_texto] || MODO_TEXTO.ocr;
  const selo = $("pg-modo");
  selo.className = "selo" + (r.modo_texto === "revisado" ? " revisado" : "");
  selo.textContent = modo[0];
  selo.title = r.revisao
    ? `Texto revisado à mão${r.revisao.autor ? " por " + r.revisao.autor : ""} em ${r.revisao.criado_em.slice(0, 16).replace("T", " ")}`
    : modo[1];
  $("pg-ver-final").classList.toggle("ativo", verTexto === "final");
  $("pg-ver-ocr").classList.toggle("ativo", verTexto === "ocr");
  $("pg-ver-final").textContent = r.modo_texto === "revisado" ? "Texto revisado" : "Texto arrumado";
  const corpo = $("pg-texto");
  corpo.classList.toggle("ocr", verTexto === "ocr");
  if (verTexto === "ocr") {
    corpo.textContent = r.texto_ocr || "";
  } else {
    desenharTexto(r.segmentos);
  }
  $("pg-legenda").hidden = verTexto === "ocr";
  $("pg-corr-resumo").textContent = verTexto === "final" && r.n_corrigidas
    ? `${r.n_corrigidas} palavra(s) corrigida(s) nesta página` : "";
  const leg = r.legibilidade;
  $("pg-ilegivel").hidden = !(leg !== null && leg !== undefined && leg < 40);
  $("pg-ilegivel").textContent = `Texto pouco legível: só ${leg}% das palavras são palavras conhecidas `
    + "(página manuscrita, gráfico, carimbo ou imagem ruim). Use o texto como pista e confira tudo na imagem.";
  desenharErros(r.possiveis_erros || []);
}

function trocarVerTexto(modo) {
  verTexto = modo;
  fecharEditor();
  desenharTextoPagina();
}

async function copiarTextoPagina() {
  const texto = $("pg-texto").innerText;
  try {
    await navigator.clipboard.writeText(texto);
    status("Texto da página copiado.", "ok");
  } catch (e) {
    const sel = window.getSelection();
    const rng = document.createRange();
    rng.selectNodeContents($("pg-texto"));
    sel.removeAllRanges();
    sel.addRange(rng);
    status("Texto selecionado: use Ctrl+C para copiar.");
  }
}

// Palavras fora do dicionário: um clique abre o editor de correção com a sugestão
function desenharErros(erros) {
  const box = $("pg-erros-box");
  box.hidden = !erros.length || verTexto === "ocr";
  $("pg-erros-n").textContent = erros.length;
  const lista = limpar($("pg-erros"));
  for (const e of erros) {
    const c = el("button", "chip-erro");
    c.type = "button";
    c.append(e.palavra);
    if (e.vezes > 1) c.append(el("span", "sug", `×${e.vezes}`));
    if (e.sugestoes.length) c.append(el("span", "sug", "→ " + e.sugestoes[0]));
    c.title = e.sugestoes.length ? `Sugestões: ${e.sugestoes.join(", ")}` : "Sem sugestão no dicionário";
    c.onclick = () => corrigirPossivelErro(e);
    lista.appendChild(c);
  }
}

function corrigirPossivelErro(e) {
  if (verTexto !== "final") trocarVerTexto("final");
  const alvo = norm(e.palavra);
  const span = [...document.querySelectorAll("#pg-texto .pal, #pg-texto .corr")].find((x) => norm(x.textContent) === alvo);
  if (!span) return;
  const caixa = $("pg-texto");
  const topo = span.getBoundingClientRect().top - caixa.getBoundingClientRect().top + caixa.scrollTop;
  caixa.scrollTop = Math.max(0, topo - caixa.clientHeight / 2);
  abrirEditor(span, e.palavra, null, e.sugestoes[0] || e.palavra);
}

let textoAntesDaEdicao = null;

function edicaoPaginaSuja() {
  return !$("pg-edicao").hidden && textoAntesDaEdicao !== null && $("pg-edicao-texto").value !== textoAntesDaEdicao;
}

function mensagemEdicao(texto, erro = true) {
  const m = $("pg-edicao-msg");
  m.textContent = texto || "";
  m.hidden = !texto;
  m.style.color = erro ? "" : "var(--suave)";
}

function abrirEdicaoPagina() {
  if (!paginaAtual || !paginaAtual.processado) return;
  fecharEditor();
  textoAntesDaEdicao = paginaAtual.texto_editavel || "";
  $("pg-edicao-texto").value = textoAntesDaEdicao;
  $("pg-edicao-auto").hidden = !paginaAtual.revisao;
  $("pg-edicao-auto").textContent = "Voltar ao texto automático";
  delete $("pg-edicao-auto").dataset.confirmar;
  mensagemEdicao("");
  $("pg-edicao").hidden = false;
  $("pg-editar").disabled = true;
  $("pg-texto").hidden = true;
  $("pg-erros-box").hidden = true;
  $("pg-legenda").hidden = true;
  const area = $("pg-edicao-texto");
  area.focus();
  area.setSelectionRange(0, 0);
  area.scrollTop = 0;
}

function fecharEdicaoPagina() {
  $("pg-edicao").hidden = true;
  $("pg-editar").disabled = false;
  $("pg-texto").hidden = false;
  $("pg-legenda").hidden = verTexto === "ocr";
  textoAntesDaEdicao = null;
}

function cancelarEdicaoPagina() {
  fecharEdicaoPagina();
  desenharTextoPagina();
}

async function salvarEdicaoPagina() {
  if (!docAtual) return;
  const texto = $("pg-edicao-texto").value;
  const r = await chamar($("pg-edicao-salvar"), "salvar_texto_pagina", docAtual.rel, docAtual.pagina, texto);
  if (!r.ok) { mensagemEdicao(r.erro); return; }
  fecharEdicaoPagina();
  verTexto = "final";
  status(`Texto da página ${r.pagina} revisado: já vale na busca.`, "ok");
  const d = docs.find((x) => x.rel === docAtual.rel);
  if (d && !(paginaAtual && paginaAtual.revisao)) { d.revisadas = (d.revisadas || 0) + 1; desenharDocs(); }
  abrirPagina(docAtual.rel, docAtual.pagina, termoAtual);
}

// Dois cliques (sem diálogo do navegador): o primeiro pede confirmação no próprio botão.
async function voltarTextoAutomatico() {
  const b = $("pg-edicao-auto");
  if (!b.dataset.confirmar) {
    b.dataset.confirmar = "1";
    b.textContent = "Confirmar: apagar a revisão desta página";
    setTimeout(() => { if (b.dataset.confirmar) { delete b.dataset.confirmar; b.textContent = "Voltar ao texto automático"; } }, 5000);
    return;
  }
  delete b.dataset.confirmar;
  const r = await chamar(b, "descartar_texto_pagina", docAtual.rel, docAtual.pagina);
  if (!r.ok) { mensagemEdicao(r.erro); return; }
  fecharEdicaoPagina();
  status(`A página ${r.pagina} voltou ao texto arrumado automaticamente.`, "ok");
  const d = docs.find((x) => x.rel === docAtual.rel);
  if (d && r.removida && d.revisadas) { d.revisadas -= 1; desenharDocs(); }
  abrirPagina(docAtual.rel, docAtual.pagina, termoAtual);
}

// ------------------------------------------- texto clicável e correções
// Tokens clicáveis: letras, dígitos, "_" e "-" (mesma fronteira que o motor usa
// para aplicar uma correção: "T-GRMAA3-RN" é um token só).
const RE_TOKEN = /[\p{L}\p{N}_-]+/gu;

function desenharTexto(segmentos) {
  const corpo = $("pg-texto");
  corpo.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const sg of segmentos) {
    if (typeof sg !== "string") {
      const c = el("span", "corr " + sg.tipo, sg.t);
      c.title = `O OCR leu: ${sg.orig}` + ORIGEM_CORRECAO[sg.tipo];
      c.onclick = () => abrirEditor(c, sg.orig, sg.tipo, sg.t);
      frag.appendChild(c);
      continue;
    }
    let pos = 0;
    for (const m of sg.matchAll(RE_TOKEN)) {
      if (m.index > pos) frag.appendChild(document.createTextNode(sg.slice(pos, m.index)));
      const w = el("span", "pal", m[0]);
      w.onclick = () => abrirEditor(w, m[0], null, m[0]);
      frag.appendChild(w);
      pos = m.index + m[0].length;
    }
    if (pos < sg.length) frag.appendChild(document.createTextNode(sg.slice(pos)));
  }
  corpo.appendChild(frag);
}

const ORIGEM_CORRECAO = {
  auto: " (corrigida pelo dicionário)",
  usuario: " (corrigida por você)",
  comunidade: " (corrigida pela comunidade)",
};

let edicao = null;   // {orig, tipo}

function abrirEditor(span, orig, tipo, atual) {
  document.querySelectorAll("#pg-texto .sel").forEach((x) => x.classList.remove("sel"));
  span.classList.add("sel");
  edicao = { orig, tipo };
  $("ed-orig").textContent = orig;
  $("ed-estado").textContent = tipo === "auto" ? `→ corrigida pelo dicionário para “${atual}”`
                             : tipo === "usuario" ? `→ você corrigiu para “${atual}”`
                             : tipo === "comunidade" ? `→ corrigida pela comunidade para “${atual}”` : "";
  $("ed-para").value = atual;
  const erro = paginaAtual && (paginaAtual.possiveis_erros || []).find((e) => norm(e.palavra) === norm(orig));
  const sug = limpar($("ed-sugestoes"));
  sug.hidden = !(erro && erro.sugestoes.length);
  if (erro && erro.sugestoes.length) {
    sug.appendChild(el("span", "ajuda", "Sugestões do dicionário:"));
    for (const x of erro.sugestoes) {
      const b = el("button", "chip-busca", x);
      b.type = "button";
      b.onclick = () => { $("ed-para").value = x; $("ed-para").focus(); };
      sug.appendChild(b);
    }
  }
  $("ed-manter").hidden = !(tipo === "auto" || tipo === "comunidade");
  $("ed-desfazer").hidden = tipo !== "usuario";
  mensagemEditor("");
  $("editor").hidden = false;
  $("ed-para").focus();
  $("ed-para").select();
}

function fecharEditor() {
  $("editor").hidden = true;
  edicao = null;
  document.querySelectorAll("#pg-texto .sel").forEach((x) => x.classList.remove("sel"));
}

// Chamado uma vez depois que a página é redesenhada (ver abrirPagina).
let aposRedesenhar = null;

// Depois de qualquer mudança no vocabulário: o motor já reindexou tudo.
// A página volta para o mesmo ponto do texto, e a palavra mexida pisca — sem isso o
// texto voltava ao topo e a correção (já colorida) ficava fora da vista.
async function aposVocabulario(r, msg, palavra) {
  if (!r.ok) { mensagemEditor(r.erro); return; }
  desenharDicionario(r);
  status(`${msg} ${r.paginas_atualizadas} página(s) atualizadas em todos os documentos.`, "ok");
  carregarAtalhos();
  if (docAtual) {
    const rolagem = { texto: $("pg-texto").scrollTop, painel: $("painel-pagina").scrollTop };
    const voltar = () => {
      $("pg-texto").scrollTop = rolagem.texto;
      $("painel-pagina").scrollTop = rolagem.painel;
    };
    aposRedesenhar = () => {
      voltar();
      // a imagem nova ainda carrega e muda a altura do painel: volta de novo quando chegar
      if (!$("pg-img").complete) $("pg-img").addEventListener("load", voltar, { once: true });
      if (palavra) realcarPalavra(palavra);
    };
    abrirPagina(docAtual.rel, docAtual.pagina, termoAtual);
  }
  if (termoAtual && $("busca").value.trim()) buscar();
}

function realcarPalavra(palavra) {
  const alvo = norm(palavra);
  const achada = [...document.querySelectorAll("#pg-texto .corr, #pg-texto .pal")]
    .find((x) => norm(x.textContent) === alvo);
  if (!achada) return;
  achada.classList.add("piscar");
  const caixa = $("pg-texto");
  const topo = achada.getBoundingClientRect().top - caixa.getBoundingClientRect().top + caixa.scrollTop;
  if (topo < caixa.scrollTop || topo > caixa.scrollTop + caixa.clientHeight - 20)
    caixa.scrollTop = Math.max(0, topo - caixa.clientHeight / 2);
  setTimeout(() => achada.classList.remove("piscar"), 2400);
}

function norm(t) { return (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase(); }

// Recusa ou aviso dentro do editor: a mensagem do rodapé pode ficar cortada.
function mensagemEditor(texto) {
  $("ed-msg").textContent = texto || "";
  $("ed-msg").hidden = !texto;
}

async function salvarCorrecao(ev) {
  ev.preventDefault();
  if (!edicao) return;
  const para = $("ed-para").value.trim();
  if (para === edicao.orig) {
    // igual ao que o OCR leu: numa palavra corrigida pelo dicionário/comunidade, é
    // "o OCR estava certo"; numa palavra comum, não há o que mudar
    if (edicao.tipo === "auto" || edicao.tipo === "comunidade") return manterOriginal();
    mensagemEditor("A forma correta é igual ao que o OCR leu. Digite como a palavra deveria ser lida — ou feche, se já está certa.");
    return;
  }
  const r = await chamar(null, "corrigir_palavra", edicao.orig, para);
  aposVocabulario(r, `“${edicao.orig}” agora é lida como “${para}”.`, para);
}

async function manterOriginal() {
  if (!edicao) return;
  const orig = edicao.orig;
  const r = await chamar($("ed-manter"), "manter_original", orig);
  aposVocabulario(r, `“${orig}” não será mais corrigida automaticamente.`, orig);
}

async function desfazerCorrecao() {
  if (!edicao) return;
  const orig = edicao.orig;
  const r = await chamar($("ed-desfazer"), "remover_correcao", orig);
  aposVocabulario(r, `Correção de “${orig}” desfeita.`, orig);
}

async function adicionarDoEditor() {
  const palavra = $("ed-para").value.trim();
  if (!palavra) return;
  const r = await chamar($("ed-adicionar"), "adicionar_palavra", palavra);
  aposVocabulario(r, `“${palavra}” entrou no dicionário.`);
}

// ------------------------------------------------ palavras-chave (atalhos)
async function carregarAtalhos() {
  if (!projetoAberto) return;
  const r = await chamar(null, "palavras_chave");
  if (!r.ok) return;
  const caixa = $("atalhos");
  caixa.innerHTML = "";
  let algum = false;
  for (const c of r.categorias) {
    const minhas = c.categoria === "Minhas palavras";
    const termos = c.termos.filter((t) => t.paginas > 0 || minhas);
    if (!termos.length) continue;
    algum = true;
    const linha = el("div", "cat");
    linha.appendChild(el("span", "cat-nome", c.categoria));
    for (const t of termos) {
      const b = el("button", "chip-busca" + (t.paginas ? "" : " zero"));
      b.type = "button";
      b.append(el("span", "", t.termo), el("span", "n", String(t.paginas)));
      b.title = `${t.paginas} página(s) — clique para buscar`;
      b.onclick = () => { $("busca").value = t.termo; buscar(); };
      linha.appendChild(b);
    }
    caixa.appendChild(linha);
  }
  if (!algum) caixa.appendChild(el("p", "ajuda", "Processe documentos para ver as palavras-chave encontradas neles."));
}

// ------------------------------------------------------- dicionário
async function carregarDicionario() {
  if (!projetoAberto) return;
  const r = await chamar(null, "dicionario");
  if (r.ok) desenharDicionario(r);
}

function itemDic(texto, aoRemover, dica) {
  const li = el("li");
  const t = el("span", "", texto);
  const x = el("button", "x", "×");
  x.type = "button";
  x.title = dica;
  x.onclick = aoRemover;
  li.append(t, x);
  return li;
}

function desenharDicionario(d) {
  const chips = $("dic-palavras");
  chips.innerHTML = "";
  for (const p of d.palavras) {
    const c = el("span", "chip-dic", p);
    const x = el("button", "x", "×");
    x.type = "button";
    x.title = "Remover do dicionário";
    x.onclick = async () => aposVocabulario(await chamar(null, "remover_palavra", p), `“${p}” saiu do dicionário.`);
    c.appendChild(x);
    chips.appendChild(c);
  }
  const corr = $("dic-correcoes");
  corr.innerHTML = "";
  const pares = Object.entries(d.correcoes);
  $("n-corr").textContent = pares.length;
  for (const [de, para] of pares) {
    corr.appendChild(itemDic(`${de} → ${para}`, async () =>
      aposVocabulario(await chamar(null, "remover_correcao", de), `Correção de “${de}” desfeita.`),
      "Desfazer esta correção"));
  }
  if (!pares.length) corr.appendChild(el("li", "vazio-lista", "Nenhuma ainda."));
  const ign = $("dic-ignorar");
  ign.innerHTML = "";
  $("n-ign").textContent = d.ignorar.length;
  for (const w of d.ignorar) {
    ign.appendChild(itemDic(w, async () =>
      aposVocabulario(await chamar(null, "remover_ignorar", w), `“${w}” volta a ser corrigida pelo dicionário.`),
      "Voltar a corrigir automaticamente"));
  }
  if (!d.ignorar.length) ign.appendChild(el("li", "vazio-lista", "Nenhuma."));
  const com = $("dic-comunidade");
  com.innerHTML = "";
  const lista = d.correcoes_comunidade || [];
  $("n-com").textContent = lista.length;
  for (const c of lista.slice(0, 400)) {
    com.appendChild(itemDic(`${c.de} → ${c.para}`, async () =>
      aposVocabulario(await chamar(null, "manter_original", c.de),
                      `“${c.de}” fica como o OCR leu neste computador.`),
      "O OCR estava certo: não aplicar esta correção aqui"));
  }
  if (!lista.length) com.appendChild(el("li", "vazio-lista", "Nenhuma. Importe pacotes ou a base na aba Comunidade."));
}

async function adicionarPalavra(ev) {
  ev.preventDefault();
  const palavra = $("nova-palavra").value.trim();
  if (!palavra) return;
  const r = await chamar(null, "adicionar_palavra", palavra);
  if (r.ok) $("nova-palavra").value = "";
  aposVocabulario(r, `“${palavra}” entrou no dicionário.`);
}

// Chamado pelo motor a cada evento da fila de processamento.
window.eventoDocumento = function (ev) {
  const painel = $("ocr");
  if (ev.tipo === "idioma") {
    painel.hidden = false;
    $("ocr-nome").textContent = "Baixando idioma português do OCR (só na primeira vez)";
    $("ocr-barra").style.width = ev.total ? (100 * ev.feito / ev.total).toFixed(1) + "%" : "0%";
    $("ocr-num").textContent = tamanho(ev.feito) + (ev.total ? ` de ${tamanho(ev.total)}` : "");
  } else if (ev.tipo === "inicio") {
    painel.hidden = false;
    $("ocr-nome").textContent = `${ev.indice}/${ev.total} · ${ev.nome}`;
    $("ocr-nome").title = ev.doc;
    $("ocr-barra").style.width = "0%";
    $("ocr-num").textContent = "";
  } else if (ev.tipo === "pagina") {
    $("ocr-barra").style.width = (100 * ev.pagina / ev.paginas).toFixed(1) + "%";
    $("ocr-num").textContent = `pág ${ev.pagina} de ${ev.paginas}`;
    const sel = document.getElementById("sit-" + ev.doc);
    if (sel) { sel.className = "selo trab"; sel.textContent = `processando ${ev.pagina}/${ev.paginas}`; }
  } else if (ev.tipo === "fim") {
    const d = docs.find((x) => x.rel === ev.doc);
    if (d) {
      Object.assign(d, { situacao: "processado", n_paginas: ev.n_paginas, embutido: ev.embutido, ocr: ev.ocr });
      const sel = document.getElementById("sit-" + ev.doc);
      if (sel) { sel.className = "selo ok"; sel.textContent = descreverDoc(d); }
    }
    if (docAtual && docAtual.rel === ev.doc) abrirPagina(docAtual.rel, docAtual.pagina, termoAtual);
  } else if (ev.tipo === "erro") {
    const sel = document.getElementById("sit-" + ev.doc);
    if (sel) { sel.className = "selo err"; sel.textContent = "erro"; sel.title = ev.erro; }
    status(ev.erro, "erro");
  } else if (ev.tipo === "ocioso") {
    painel.hidden = true;
    const p = [];
    if (ev.processados) p.push(`${ev.processados} processado(s)`);
    if (ev.cancelados) p.push(`${ev.cancelados} cancelado(s)`);
    if (ev.erros) p.push(`${ev.erros} com erro`);
    status(`Processamento encerrado: ${p.join(" · ") || "nada a fazer"}. Os documentos já entram na busca.`,
           ev.erros ? "erro" : "ok");
    if (!$("vista-docs").hidden) carregarDocumentos();
  }
};
