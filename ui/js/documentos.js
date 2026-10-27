// SIAPP — aba Documentos: texto/OCR, busca, página, correções e dicionário.
"use strict";

let docs = [];                 // lista vinda do motor
let docAtual = null;           // {rel, pagina, n_paginas} da página aberta no painel
let termoAtual = "";

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
    $("docs-resumo").textContent = "Escolha primeiro a pasta do projeto na aba Catálogo.";
    return;
  }
  const r = await chamar(null, "documentos");
  if (!r.ok) return;
  docs = r.documentos;
  const pend = docs.filter((d) => d.situacao !== "processado");
  $("docs-resumo").textContent = docs.length
    ? `${docs.length} documento(s) · ${docs.length - pend.length} processado(s) · ${pend.length} pendente(s)`
    : "Nenhum PDF, TIF ou imagem baixado ainda. Baixe na aba Catálogo.";
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
    b.onclick = () => abrirPagina(d.rel, 1, d.situacao === "processado" ? termoAtual : "");
    li.appendChild(b);
    ul.appendChild(li);
  }
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
  docAtual = { rel: r.rel, pagina: r.pagina, n_paginas: r.n_paginas, processado: r.processado };
  $("pg-nome").textContent = r.nome;
  $("pg-sub").textContent = r.titulo || "";
  $("pg-num").textContent = `pág ${r.pagina} de ${r.n_paginas}`;
  $("pg-ant").disabled = r.pagina <= 1;
  $("pg-prox").disabled = r.pagina >= r.n_paginas;
  $("pg-aviso").hidden = r.metodo !== "ocr";
  $("pg-pendente").hidden = r.processado;
  $("pg-processar").disabled = false;
  $("pg-texto-box").hidden = !r.processado;
  $("pg-img").src = r.imagem;
  iniciarTranscricao(r);
  fecharEditor();
  desenharTexto(r.segmentos);
  $("pg-corr-resumo").textContent = r.n_corrigidas
    ? `${r.n_corrigidas} palavra(s) corrigida(s) nesta página` : "";
  if (aposRedesenhar) { const f = aposRedesenhar; aposRedesenhar = null; f(); }
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
