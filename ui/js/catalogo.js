// SIAPP — Acervo › Catálogo do REATE: bacias, categorias, poços, árvore de arquivos e downloads.
"use strict";

let pocosAtuais = [];

async function escolherPasta(ev) {
  inicioAbertura();
  const r = await chamar((ev && ev.currentTarget) || $("ini-pasta"), "escolher_pasta");
  fimAbertura();
  if (!r.ok || r.cancelado) return;
  liberarProjeto(r);
  status(r.bacia_anterior
    ? `Projeto existente aberto (última bacia: ${r.bacia_anterior}).`
    : "Projeto criado — siapp.json gravado na pasta.", "ok");
}

// Abre a pasta do projeto sem o diálogo (preferência "abrir ao iniciar").
async function abrirProjetoSozinho() {
  inicioAbertura();
  const r = await chamar(null, "abrir_projeto_padrao");
  fimAbertura();
  if (!r.ok) return false;
  liberarProjeto(r);
  status(`Projeto aberto: ${r.pasta.split(/[\\/]/).pop()}` +
         (r.bacia_anterior ? ` (última bacia: ${r.bacia_anterior})` : "") + ". Abre sozinho ao iniciar (Configurações).", "ok");
  return true;
}

// O projeto ficou aberto (nesta janela ou em outra): libera as abas.
function liberarProjeto(r) {
  const primeiraVez = !projetoAberto;
  projetoAberto = true;
  if (r.bacia_anterior) baciaAnterior = r.bacia_anterior;
  aoAbrirProjeto(r);
  liberar("etapa-bacia");
  $("sel-bacia").disabled = false;
  $("btn-conectar").disabled = false;
  if (r.bacia_anterior) $("sel-bacia").value = r.bacia_anterior;
  if (primeiraVez) aplicarLayout(new Set(abasVisiveis()));
}

async function conectar() {
  const bacia = $("sel-bacia").value;
  status(`Conectando ao REATE — Bacia ${bacia}…`, "trab");
  const r = await chamar($("btn-conectar"), "conectar", bacia);
  if (!r.ok) return;
  desenharConexao(r, bacia);
  status(`Conectado à Bacia ${bacia}. Catálogo salvo em ${r.salvo_em}.`, "ok");
}

// Desenha as categorias de uma conexão (do clique em Conectar ou do "Ver arquivos" da ficha, 0.65).
function desenharConexao(r, bacia) {
  baciaConectada = bacia;
  // a lista e a gaveta abertas eram da bacia anterior: some com elas
  pedidoLista++;
  fecharGaveta();
  pocosAtuais = [];
  baciaDaLista = "";
  $("painel-pocos").hidden = true;
  $("vazio").hidden = false;

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
}

// Listar uma categoria grande leva segundos. Se nesse meio-tempo o usuário listar
// outra categoria ou conectar em outra bacia, a resposta antiga é descartada.
let pedidoLista = 0;
let baciaDaLista = "";    // bacia da lista de poços que está na tela

async function listarPocos(categoria, botao) {
  document.querySelectorAll(".lista-cat button").forEach((b) => b.classList.remove("ativa"));
  botao.classList.add("ativa");
  status(`Listando poços de "${categoria}"…`, "trab");

  const meu = ++pedidoLista;
  const bacia = baciaConectada;
  const r = await chamar(null, "listar_pocos", categoria, bacia);
  if (meu !== pedidoLista || bacia !== baciaConectada) {
    if (r.ok) status(`A lista de "${categoria}" (${bacia}) chegou depois da troca e foi guardada na bacia ${bacia}, sem aparecer aqui.`, "ok");
    return;
  }
  if (!r.ok) return;
  desenharListaPocos(r, categoria, bacia);
  status(`${r.pocos.length} poços em "${categoria}". Lista salva em ${r.salvo_em}.`, "ok");
}

function desenharListaPocos(r, categoria, bacia) {
  document.querySelectorAll(".lista-cat button").forEach((b) => b.classList.toggle("ativa", b.textContent === categoria));
  fecharGaveta();
  listaParcial = !!r.parcial;
  pocosAtuais = r.pocos;
  baciaDaLista = r.bacia || bacia;
  $("vazio").hidden = true;
  $("painel-pocos").hidden = false;
  $("titulo-pocos").textContent = categoria;
  resumoBase = `${r.pocos.length} poços`;
  if (r.partes.length) resumoBase += ` · reunidos de ${r.partes.length} subpastas "parte"`;
  if (r.duplicados.length) resumoBase += ` · ${r.duplicados.length} repetido(s) entre partes`;
  if (r.arquivos_soltos.length) resumoBase += ` · ${r.arquivos_soltos.length} arquivo(s) solto(s)`;
  if (r.parcial) resumoBase = "só este poço (a categoria ainda não foi listada: clique nela, à esquerda, para ver todos)";
  else if (r.pocos.length) resumoBase += " · clique num poço para ver os arquivos";
  $("filtro").value = "";
  desenharPocos();
}

let resumoBase = "";
let listaParcial = false;     // 0.65: categoria mostrada só com o poço aberto pela ficha

function desenharPocos() {
  const termo = $("filtro").value.trim().toUpperCase();
  const visiveis = termo ? pocosAtuais.filter((p) => p.nome.toUpperCase().includes(termo)) : pocosAtuais;
  $("resumo-pocos").textContent = termo && !listaParcial ? `${visiveis.length} de ${pocosAtuais.length} poços` : resumoBase;
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

  const r = await chamar(null, "explorar_poco", p.nome, p.caminho, $("titulo-pocos").textContent, p.parte, baciaDaLista);
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
    if (item.no.rel && !item.abrir) {
      item.abrir = botaoAbrir(item.no.rel, item.no.tipo);
      item.selo.after(item.abrir);
    }
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
  const r = await chamar($("btn-baixar"), "baixar", pocoAberto, pedido, baciaDaLista);
  if (!r.ok) return;
  for (const a of sel) marcarArquivo(a, "fila");
  status(`${r.enfileirados} arquivo(s) na fila de download.`, "trab");
}


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
    if (item) { item.no.rel = ev.arquivo_local; item.no.tipo = ev.tipo_arquivo; marcarArquivo(item, "baixado"); }
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
