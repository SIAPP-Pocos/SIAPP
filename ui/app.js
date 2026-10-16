// SIAPP — interface. Toda ação passa por window.pywebview.api (motor Python).
"use strict";

const $ = (id) => document.getElementById(id);
let api = null;
let pocosAtuais = [];

// ------------------------------------------------------------------ status
function status(texto, tipo = "") {
  $("status").textContent = texto;
  document.querySelector(".rodape").className = "rodape " + tipo;
}

function liberar(idEtapa) { $(idEtapa).classList.remove("bloqueada"); }

async function chamar(botao, fn, ...args) {
  if (botao) { botao.disabled = true; botao.classList.add("ocupado"); }
  try {
    const r = await api[fn](...args);
    if (!r.ok) status(r.erro, "erro");
    return r;
  } catch (e) {
    status("Falha na comunicação com o motor: " + e, "erro");
    return { ok: false };
  } finally {
    if (botao) { botao.disabled = false; botao.classList.remove("ocupado"); }
  }
}

// ------------------------------------------------------------------ etapas
async function escolherPasta() {
  const r = await chamar($("btn-pasta"), "escolher_pasta");
  if (!r.ok || r.cancelado) return;

  projetoAberto = true;
  $("caminho-pasta").textContent = r.pasta;
  $("caminho-pasta").hidden = false;
  liberar("etapa-bacia");
  $("sel-bacia").disabled = false;
  $("btn-conectar").disabled = false;
  if (r.bacia_anterior) $("sel-bacia").value = r.bacia_anterior;

  status(r.bacia_anterior
    ? `Projeto existente aberto (última bacia: ${r.bacia_anterior}).`
    : "Projeto criado — siapp.json gravado na pasta.", "ok");
}

async function conectar() {
  const bacia = $("sel-bacia").value;
  status(`Conectando ao REATE — Bacia ${bacia}…`, "trab");
  const r = await chamar($("btn-conectar"), "conectar", bacia);
  if (!r.ok) return;

  const lista = $("lista-cat");
  lista.innerHTML = "";
  for (const c of r.categorias) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.textContent = c.nome;
    b.onclick = () => listarPocos(c.nome, b);
    li.appendChild(b);
    lista.appendChild(li);
  }
  liberar("etapa-categoria");
  $("ajuda-categoria").textContent =
    `${r.categorias.length} categorias em ${r.base}. Clique para listar os poços.`;
  status(`Conectado à Bacia ${bacia}. Catálogo salvo em ${r.salvo_em}.`, "ok");
}

async function listarPocos(categoria, botao) {
  document.querySelectorAll(".lista-cat button").forEach((b) => b.classList.remove("ativa"));
  botao.classList.add("ativa");
  status(`Listando poços de "${categoria}"…`, "trab");

  const r = await chamar(null, "listar_pocos", categoria);
  if (!r.ok) return;

  fecharGaveta();
  pocosAtuais = r.pocos;
  $("vazio").hidden = true;
  $("painel-pocos").hidden = false;
  $("titulo-pocos").textContent = categoria;
  resumoBase = `${r.pocos.length} poços`;
  if (r.partes.length) resumoBase += ` · reunidos de ${r.partes.length} subpastas "parte"`;
  if (r.duplicados.length) resumoBase += ` · ${r.duplicados.length} repetido(s) entre partes`;
  if (r.arquivos_soltos.length) resumoBase += ` · ${r.arquivos_soltos.length} arquivo(s) solto(s)`;
  if (r.pocos.length) resumoBase += " · clique num poço para ver os arquivos";
  $("filtro").value = "";
  desenharPocos();
  status(`${r.pocos.length} poços em "${categoria}". Lista salva em ${r.salvo_em}.`, "ok");
}

let resumoBase = "";

function desenharPocos() {
  const termo = $("filtro").value.trim().toUpperCase();
  const visiveis = termo ? pocosAtuais.filter((p) => p.nome.toUpperCase().includes(termo)) : pocosAtuais;
  $("resumo-pocos").textContent = termo ? `${visiveis.length} de ${pocosAtuais.length} poços` : resumoBase;
  const grade = $("grade-pocos");
  grade.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const p of visiveis) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.textContent = p.nome;
    b.title = (p.parte ? `${p.nome}\nem ${p.parte}` : p.nome) + "\nClique para ver os arquivos";
    if (pocoAberto === p.nome) b.classList.add("ativo");
    b.onclick = () => explorarPoco(p, b);
    li.appendChild(b);
    frag.appendChild(li);
  }
  grade.appendChild(frag);
}

// ------------------------------------------------------- explorar um poço
let pedidoAtual = 0;      // descarta respostas de cliques antigos
let pocoAberto = null;

function tamanho(bytes) {
  if (!bytes) return "0 B";
  const un = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = bytes;
  while (v >= 1024 && i < un.length - 1) { v /= 1024; i++; }
  return (i === 0 ? v : v.toFixed(v < 10 ? 1 : 0)) + " " + un[i];
}

function el(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto !== undefined) e.textContent = texto;
  return e;
}

function abrirGaveta() { $("gaveta").hidden = false; }
function fecharGaveta() {
  $("gaveta").hidden = true;
  pocoAberto = null;
  pedidoAtual++;
  document.querySelectorAll("#grade-pocos button.ativo").forEach((b) => b.classList.remove("ativo"));
}

async function explorarPoco(p, botao) {
  document.querySelectorAll("#grade-pocos button.ativo").forEach((b) => b.classList.remove("ativo"));
  botao.classList.add("ativo");
  pocoAberto = p.nome;
  const meu = ++pedidoAtual;

  $("g-titulo").textContent = p.nome;
  $("g-sub").textContent = [$("titulo-pocos").textContent, p.parte].filter(Boolean).join(" · ");
  $("g-resumo").innerHTML = "";
  $("g-arvore").innerHTML = "";
  $("g-arvore").appendChild(el("li", "carregando", "Lendo as pastas do poço no portal…"));
  $("g-rodape").textContent = "";
  $("g-acoes").hidden = true;
  arquivosGaveta = new Map();
  abrirGaveta();
  status(`Mapeando ${p.nome}…`, "trab");

  const r = await chamar(null, "explorar_poco", p.nome, p.caminho, $("titulo-pocos").textContent, p.parte);
  if (meu !== pedidoAtual) return;          // usuário já clicou em outro poço
  $("g-arvore").innerHTML = "";
  if (!r.ok) {
    $("g-arvore").appendChild(el("li", "erro-arvore", r.erro || "Falha ao ler o poço."));
    return;
  }

  // resumo
  const res = $("g-resumo");
  res.append(el("span", "chip forte", `${r.resumo.n_arquivos} arquivos`),
             el("span", "chip forte", tamanho(r.resumo.tamanho_total)));
  for (const [ext, n] of Object.entries(r.resumo.por_extensao)) {
    const perfil = [".dlis", ".lis", ".las"].includes(ext);
    res.appendChild(el("span", "chip" + (perfil ? " perfil" : ""), `${ext.replace(".", "").toUpperCase()} ${n}`));
  }

  // árvore (começa pelos filhos: a raiz é o próprio poço)
  const raiz = $("g-arvore");
  if (!r.arvore.filhos.length) raiz.appendChild(el("li", "carregando", "Pasta vazia no portal."));
  for (const f of r.arvore.filhos) raiz.appendChild(noArvore(f));
  $("g-acoes").hidden = arquivosGaveta.size === 0;
  atualizarSelecao();

  const avisos = [`${r.resumo.n_pastas_lidas} pasta(s) lida(s). Árvore salva em ${r.salvo_em}.`];
  if (r.incompleto) avisos.push("Atenção: a árvore é grande demais e foi lida só em parte.");
  $("g-rodape").textContent = avisos.join(" ");
  const nBaixados = [...arquivosGaveta.values()].filter((a) => a.no.baixado).length;
  status(`${p.nome}: ${r.resumo.n_arquivos} arquivos, ${tamanho(r.resumo.tamanho_total)}` +
         (nBaixados ? ` · ${nBaixados} já baixado(s).` : "."), "ok");
}

function noArvore(n) {
  const li = el("li");
  if (n.pasta) {
    const det = el("details");
    det.open = true;
    const sum = el("summary", "pasta" + (n.preferida ? " conv" : ""));
    sum.title = n.nome;
    sum.append(el("span", "nome", n.nome));
    if (n.preferida) sum.appendChild(el("span", "selo conv", "pasta de perfis"));
    if (n.nao_lida) sum.appendChild(el("span", "selo", "não lida"));
    sum.appendChild(el("span", "tam", `${n.n_arquivos} arq · ${tamanho(n.tamanho)}`));
    const ul = el("ul");
    for (const f of n.filhos) ul.appendChild(noArvore(f));
    det.append(sum, ul);
    li.appendChild(det);
  } else {
    const linha = el("label", "arquivo");
    linha.title = `${n.nome}\n${tamanho(n.tamanho)}`;
    const cb = el("input");
    cb.type = "checkbox";
    cb.checked = false;   // a escolha é sempre do usuário: cada tipo de arquivo serve a uma finalidade
    cb.onchange = atualizarSelecao;
    const selo = el("span", "selo", "");
    selo.hidden = true;
    linha.append(cb, el("span", "nome", n.nome));
    linha.append(selo, el("span", "tam", tamanho(n.tamanho)));
    li.appendChild(linha);
    const item = { no: n, cb, linha, selo };
    arquivosGaveta.set(n.caminho, item);
    if (n.baixado) marcarArquivo(item, "baixado");
    else if (n.parcial) marcarArquivo(item, "parcial");
  }
  return li;
}

// ---------------------------------------------------------------- download
let arquivosGaveta = new Map();   // caminho remoto -> {no, cb, linha, selo} do poço aberto

const SELOS = {
  baixado:   ["selo ok", "baixado"],
  parcial:   ["selo", "parcial — retoma"],
  fila:      ["selo", "na fila"],
  baixando:  ["selo trab", "baixando"],
  erro:      ["selo err", "erro"],
  cancelado: ["selo", "cancelado"],
};

function marcarArquivo(item, estado) {
  const [classe, texto] = SELOS[estado];
  item.selo.className = classe;
  item.selo.textContent = texto;
  item.selo.hidden = false;
  if (estado === "baixado") {
    item.no.baixado = true;
    item.cb.checked = false;
    item.cb.disabled = true;
    item.linha.title = `${item.no.nome}\n${tamanho(item.no.tamanho)}\nJá está em ambiente_teste\\bruto`;
  } else if (estado === "fila" || estado === "baixando") {
    item.cb.checked = false;
    item.cb.disabled = true;
  } else {
    item.cb.disabled = false;
  }
  atualizarSelecao();
}

function selecionados() {
  return [...arquivosGaveta.values()].filter((a) => a.cb.checked && !a.cb.disabled);
}

function atualizarSelecao() {
  const sel = selecionados();
  const bytes = sel.reduce((t, a) => t + (a.no.tamanho || 0), 0);
  $("btn-baixar").disabled = sel.length === 0;
  $("g-selecao").textContent = sel.length
    ? `${sel.length} arquivo(s) · ${tamanho(bytes)}`
    : "Marque os arquivos que quer baixar.";
}

async function baixarSelecionados() {
  const sel = selecionados();
  if (!sel.length || !pocoAberto) return;
  const pedido = sel.map((a) => ({ caminho: a.no.caminho, nome: a.no.nome,
                                   tamanho: a.no.tamanho, pasta_relativa: a.no.pasta_relativa }));
  const r = await chamar($("btn-baixar"), "baixar", pocoAberto, pedido);
  if (!r.ok) return;
  for (const a of sel) marcarArquivo(a, "fila");
  status(`${r.enfileirados} arquivo(s) na fila de download.`, "trab");
}

let resumoDownloads = "";

// Chamado pelo motor (siapp.py → evaluate_js) a cada evento da fila.
window.eventoDownload = function (ev) {
  const item = arquivosGaveta.get(ev.caminho);   // só existe se o poço estiver aberto
  const painel = $("dl");
  if (ev.tipo === "inicio") {
    painel.hidden = false;
    $("dl-nome").textContent = `${ev.indice}/${ev.total} · ${ev.nome}`;
    $("dl-nome").title = `${ev.poco} / ${ev.nome}`;
    $("dl-num").textContent = tamanho(ev.tamanho);
    $("dl-barra").style.width = "0%";
    if (item) marcarArquivo(item, "baixando");
  } else if (ev.tipo === "progresso") {
    const pct = ev.total ? Math.min(100, (100 * ev.feito) / ev.total) : 0;
    $("dl-barra").style.width = pct.toFixed(1) + "%";
    $("dl-num").textContent = `${tamanho(ev.feito)} de ${tamanho(ev.total)} · ${tamanho(ev.velocidade)}/s`;
  } else if (ev.tipo === "fim") {
    $("dl-barra").style.width = "100%";
    if (item) marcarArquivo(item, "baixado");
  } else if (ev.tipo === "erro") {
    if (item) { marcarArquivo(item, "erro"); item.selo.title = ev.erro; }
    status(ev.erro, "erro");
  } else if (ev.tipo === "cancelado") {
    if (item) marcarArquivo(item, "cancelado");
  } else if (ev.tipo === "ocioso") {
    painel.hidden = true;
    const partes = [];
    if (ev.baixados) partes.push(`${ev.baixados} baixado(s), ${tamanho(ev.bytes)}`);
    if (ev.ja_existiam) partes.push(`${ev.ja_existiam} já existia(m)`);
    if (ev.cancelados) partes.push(`${ev.cancelados} cancelado(s)`);
    if (ev.erros) partes.push(`${ev.erros} com erro`);
    status(`Downloads encerrados: ${partes.join(" · ") || "nada a fazer"}. ` +
           `Arquivos em ambiente_teste\\bruto.`, ev.erros ? "erro" : "ok");
  }
};

async function cancelarDownloads() {
  await chamar($("dl-cancelar"), "cancelar_downloads");
  status("Cancelando… o que já foi baixado fica salvo para continuar depois.", "trab");
}

// ============================================================== DOCUMENTOS
let docs = [];                 // lista vinda do motor
let docAtual = null;           // {rel, pagina, n_paginas} da página aberta no painel
let termoAtual = "";
let projetoAberto = false;

function trocarAba(qual) {
  const cat = qual === "catalogo";
  $("vista-catalogo").hidden = !cat;
  $("vista-docs").hidden = cat;
  $("aba-catalogo").classList.toggle("ativa", cat);
  $("aba-docs").classList.toggle("ativa", !cat);
  $("aba-catalogo").setAttribute("aria-selected", cat);
  $("aba-docs").setAttribute("aria-selected", !cat);
  if (!cat) carregarDocumentos();
}

const SITUACAO = {
  pendente: "não processado",
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
    $("docs-resumo").textContent = "Escolha primeiro a pasta do projeto na aba Catálogo.";
    return;
  }
  const r = await chamar(null, "documentos");
  if (!r.ok) return;
  docs = r.documentos;
  const pend = docs.filter((d) => d.situacao !== "processado");
  $("docs-resumo").textContent = docs.length
    ? `${docs.length} documento(s) · ${docs.length - pend.length} processado(s) · ${pend.length} pendente(s)`
    : "Nenhum PDF ou TIF baixado ainda. Baixe na aba Catálogo.";
  $("btn-processar").disabled = pend.length === 0;
  $("aviso-idioma").hidden = r.idioma_ok || pend.length === 0;
  desenharDocs();
  carregarAtalhos();
  carregarDicionario();
}

function desenharDocs() {
  const ul = $("lista-docs");
  ul.innerHTML = "";
  for (const d of docs) {
    const li = el("li");
    const b = el("button");
    b.dataset.rel = d.rel;
    b.title = `${d.rel}\n${tamanho(d.tamanho)}`;
    if (docAtual && docAtual.rel === d.rel) b.classList.add("ativo");
    const info = el("span", "d-info");
    info.append(el("span", "", d.poco || "—"));
    const sel = el("span", "selo" + (d.situacao === "processado" ? " ok" : ""), descreverDoc(d));
    sel.id = "sit-" + d.rel;
    info.appendChild(sel);
    b.append(el("span", "d-nome", d.nome), info);
    b.onclick = () => d.situacao === "processado"
      ? abrirPagina(d.rel, 1, termoAtual)
      : status("Este documento ainda não foi processado. Use “Processar pendentes”.", "erro");
    li.appendChild(b);
    ul.appendChild(li);
  }
}

async function processarPendentes() {
  const rels = docs.filter((d) => d.situacao !== "processado").map((d) => d.rel);
  if (!rels.length) return;
  const r = await chamar($("btn-processar"), "processar_documentos", rels);
  if (r.ok) status(`${r.enfileirados} documento(s) na fila de processamento.`, "trab");
}

async function buscar(ev) {
  if (ev) ev.preventDefault();
  const termo = $("busca").value.trim();
  if (!termo) return;
  termoAtual = termo;
  $("atalhos-box").open = false;   // abre espaço para os resultados; um clique reabre
  const r = await chamar($("btn-buscar"), "buscar_documentos", termo, $("tolerante").checked);
  if (!r.ok) return;
  const ul = $("resultados");
  ul.innerHTML = "";
  const resumo = $("busca-resumo");
  resumo.textContent = r.resultados.length
    ? `${r.resultados.length} página(s) em ${r.documentos} documento(s) para “${termo}”.`
    : `Nada encontrado para “${termo}”. Os documentos pendentes ainda não entram na busca.`;
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
  for (const res of r.resultados) {
    const li = el("li");
    const b = el("button");
    const cab = el("span", "r-cab");
    cab.append(el("strong", "", res.poco || "—"), el("span", "", res.arquivo),
               el("span", "", `pág ${res.pagina}`),
               el("span", "selo" + (res.metodo === "ocr" ? "" : " ok"), res.metodo === "ocr" ? "OCR" : "texto"));
    b.appendChild(cab);
    if (res.titulo) b.appendChild(el("span", "r-titulo", res.titulo));
    b.appendChild(trechoComDestaque(res.trecho));
    b.onclick = () => {
      document.querySelectorAll(".resultados button.ativo").forEach((x) => x.classList.remove("ativo"));
      b.classList.add("ativo");
      abrirPagina(res.doc, res.pagina, termo);
    };
    li.appendChild(b);
    ul.appendChild(li);
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
  const meu = ++pedidoPagina;
  $("painel-pagina").hidden = false;
  $("pg-num").textContent = "carregando…";
  const r = await chamar(null, "ver_pagina", rel, pagina, termo || "");
  if (meu !== pedidoPagina || !r.ok) return;
  docAtual = { rel: r.rel, pagina: r.pagina, n_paginas: r.n_paginas };
  $("pg-nome").textContent = r.nome;
  $("pg-sub").textContent = r.titulo || "";
  $("pg-num").textContent = `pág ${r.pagina} de ${r.n_paginas}`;
  $("pg-ant").disabled = r.pagina <= 1;
  $("pg-prox").disabled = r.pagina >= r.n_paginas;
  $("pg-aviso").hidden = r.metodo !== "ocr";
  $("pg-img").src = r.imagem;
  fecharEditor();
  desenharTexto(r.segmentos);
  $("pg-corr-resumo").textContent = r.n_corrigidas
    ? `${r.n_corrigidas} palavra(s) corrigida(s) nesta página` : "";
  document.querySelectorAll("#lista-docs button").forEach((b) => b.classList.toggle("ativo", b.dataset.rel === r.rel));
}

function fecharPagina() {
  $("painel-pagina").hidden = true;
  docAtual = null;
  pedidoPagina++;
  document.querySelectorAll("#lista-docs button.ativo, .resultados button.ativo").forEach((b) => b.classList.remove("ativo"));
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
      c.title = `O OCR leu: ${sg.orig}` + (sg.tipo === "auto" ? " (corrigida pelo dicionário)" : " (corrigida por você)");
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

let edicao = null;   // {orig, tipo}

function abrirEditor(span, orig, tipo, atual) {
  document.querySelectorAll("#pg-texto .sel").forEach((x) => x.classList.remove("sel"));
  span.classList.add("sel");
  edicao = { orig, tipo };
  $("ed-orig").textContent = orig;
  $("ed-estado").textContent = tipo === "auto" ? `→ corrigida pelo dicionário para “${atual}”`
                             : tipo === "usuario" ? `→ você corrigiu para “${atual}”` : "";
  $("ed-para").value = atual;
  $("ed-manter").hidden = tipo !== "auto";
  $("ed-desfazer").hidden = tipo !== "usuario";
  $("editor").hidden = false;
  $("ed-para").focus();
  $("ed-para").select();
}

function fecharEditor() {
  $("editor").hidden = true;
  edicao = null;
  document.querySelectorAll("#pg-texto .sel").forEach((x) => x.classList.remove("sel"));
}

// Depois de qualquer mudança no vocabulário: o motor já reindexou tudo.
async function aposVocabulario(r, msg) {
  if (!r.ok) return;
  desenharDicionario(r);
  status(`${msg} ${r.paginas_atualizadas} página(s) atualizadas em todos os documentos.`, "ok");
  carregarAtalhos();
  if (docAtual) abrirPagina(docAtual.rel, docAtual.pagina, termoAtual);
  if (termoAtual && $("busca").value.trim()) buscar();
}

async function salvarCorrecao(ev) {
  ev.preventDefault();
  if (!edicao) return;
  const para = $("ed-para").value.trim();
  const r = await chamar(null, "corrigir_palavra", edicao.orig, para);
  aposVocabulario(r, `“${edicao.orig}” agora é lida como “${para}”.`);
}

async function manterOriginal() {
  if (!edicao) return;
  const r = await chamar($("ed-manter"), "manter_original", edicao.orig);
  aposVocabulario(r, `“${edicao.orig}” não será mais corrigida automaticamente.`);
}

async function desfazerCorrecao() {
  if (!edicao) return;
  const r = await chamar($("ed-desfazer"), "remover_correcao", edicao.orig);
  aposVocabulario(r, `Correção de “${edicao.orig}” desfeita.`);
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

// ------------------------------------------------------------------ início
async function iniciar() {
  api = window.pywebview.api;
  const r = await api.info();
  $("versao").textContent = "v" + r.versao;
  const ajuda = $("ajuda-pasta");
  ajuda.textContent = "Por enquanto, sempre a pasta ";
  const nome = document.createElement("strong");
  nome.textContent = r.nome_pasta_projeto;
  ajuda.append(nome, ", ao lado do aplicativo. O diálogo já abre nela: é só confirmar.");
  ajuda.title = r.pasta_projeto;
  const sel = $("sel-bacia");
  for (const b of r.bacias) {
    const o = document.createElement("option");
    o.value = o.textContent = b;
    sel.appendChild(o);
  }
  sel.value = "Sergipe";
  $("btn-pasta").onclick = escolherPasta;
  $("btn-conectar").onclick = conectar;
  $("filtro").oninput = desenharPocos;
  $("g-fechar").onclick = fecharGaveta;
  $("btn-baixar").onclick = baixarSelecionados;
  $("aba-catalogo").onclick = () => trocarAba("catalogo");
  $("aba-docs").onclick = () => trocarAba("docs");
  $("btn-processar").onclick = processarPendentes;
  $("btn-atualizar-docs").onclick = carregarDocumentos;
  $("form-busca").onsubmit = buscar;
  $("pg-fechar").onclick = fecharPagina;
  $("pg-ant").onclick = () => docAtual && abrirPagina(docAtual.rel, docAtual.pagina - 1, termoAtual);
  $("pg-prox").onclick = () => docAtual && abrirPagina(docAtual.rel, docAtual.pagina + 1, termoAtual);
  $("pg-abrir").onclick = () => docAtual && chamar($("pg-abrir"), "abrir_arquivo", docAtual.rel);
  $("ed-form").onsubmit = salvarCorrecao;
  $("ed-manter").onclick = manterOriginal;
  $("ed-desfazer").onclick = desfazerCorrecao;
  $("ed-adicionar").onclick = adicionarDoEditor;
  $("ed-fechar").onclick = fecharEditor;
  $("form-palavra").onsubmit = adicionarPalavra;
  $("tolerante").onchange = () => termoAtual && $("busca").value.trim() && buscar();
  $("ocr-cancelar").onclick = async () => {
    await chamar($("ocr-cancelar"), "cancelar_processamento");
    status("Cancelando o processamento…", "trab");
  };
  $("dl-cancelar").onclick = cancelarDownloads;
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("vista-docs").hidden) {
      if (!$("editor").hidden) fecharEditor();
      else if (!$("painel-pagina").hidden) fecharPagina();
    }
    else if (!$("gaveta").hidden) fecharGaveta();
  });
  status("Pronto. Comece escolhendo a pasta do projeto.");
}

window.addEventListener("pywebviewready", iniciar);
if (window.pywebview && window.pywebview.api && window.pywebview.api.info) iniciar();
setTimeout(() => {
  if (!api) status("Motor não encontrado. Abra o SIAPP pelo arquivo iniciar.bat (ou python siapp.py).", "erro");
}, 4000);
