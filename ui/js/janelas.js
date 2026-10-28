// SIAPP — abas, divisão da janela, abas em janelas próprias, preferências (cores,
// tamanho do texto, arranjo), configurações, diagnóstico, exportações, histórico de
// mensagens e a tela "Abrindo o projeto".
//
// Uma janela destacada carrega esta mesma página com ?janela=<aba>: mostra só aquela
// aba. O motor (Python) é um só para todas as janelas; uma janela pede a outra que
// mostre algo com api.janela_chamar(alvo, "irPara", [...]).
"use strict";

const MODO_JANELA = new URLSearchParams(location.search).get("janela") || "";
const ABAS_SIAPP = ["projeto", "dados", "mapa", "docs", "perfis", "interp", "viab", "comunidade"];
const NOMES_ABAS = { projeto: "Projeto", dados: "Dados", mapa: "Mapa", docs: "Documentos", perfis: "Perfis",
  interp: "Interpretação", viab: "Viabilidade", comunidade: "Comunidade" };
const PALETAS_SIAPP = [
  ["marinho", "Marinho e lima", "#1b2f5c", "#b6dd5a", "#141b2c", "Padrão do SIAPP. No claro o marinho é o destaque; no escuro, o lima."],
  ["petroleo", "Petróleo", "#0e6b70", "#e0f0f0", "#172026", "Verde-azulado sóbrio e técnico."],
  ["oceano", "Oceano", "#1d5fb0", "#e3edf9", "#161e2d", "Azul institucional, o mais neutro para apresentar."],
  ["arenito", "Arenito", "#9a5b13", "#f6e8d4", "#1f1b15", "Areia e ocre, quente; puxa para geologia."],
  ["grafite", "Grafite", "#4146b8", "#e8e9fa", "#1a1b1f", "Cinza neutro com índigo: o que tem cor de verdade aparece mais."],
  ["floresta", "Floresta", "#2d6a38", "#e2efe2", "#182019", "Verde calmo."],
  ["contraste", "Alto contraste", "#0040a8", "#ffd23f", "#000000", "Para projetor, sol na tela ou baixa visão."],
];

// estado da interface desta janela
const ui = {
  ativa: MODO_JANELA || "projeto", dividida: false, direita: "mapa", razao: 0.5,
  subDados: "catalogo", subInterp: "secao",
  fora: new Set(),          // abas que estão em janela própria (só a principal acompanha)
  recolhidas: {},
  visiveis: new Set(),
};
let prefs = null;

// ---------------------------------------------------------------- preferências
async function carregarPreferencias() {
  const r = await chamar(null, "preferencias");
  if (!r.ok) return;
  prefs = r.preferencias;
  aplicarAparencia();
  ui.recolhidas = { ...prefs.recolhidas };
  const L = prefs.layout;
  ui.subDados = L.sub_dados;
  ui.subInterp = L.sub_interp;
  if (!MODO_JANELA && prefs.lembrar_arranjo) {
    ui.ativa = L.ativa;
    ui.direita = L.direita;
    ui.razao = L.razao;
    ui.dividida = L.dividida;
  }
  ui.fora = new Set(r.abertas || []);
  if (!MODO_JANELA && ui.fora.has(ui.ativa)) ui.ativa = ABAS_SIAPP.find((a) => !ui.fora.has(a)) || "projeto";
  if (ui.dividida && (ui.fora.has(ui.direita) || ui.direita === ui.ativa)) ui.dividida = false;
}

async function guardarPreferencias(mudancas) {
  const r = await chamar(null, "salvar_preferencias", mudancas);
  if (r.ok) prefs = r.preferencias;
  return r;
}

let _guardarLayout = null;
function guardarLayout() {
  if (MODO_JANELA) return;
  clearTimeout(_guardarLayout);
  _guardarLayout = setTimeout(() => guardarPreferencias({ layout: {
    ativa: ui.ativa, dividida: ui.dividida, direita: ui.direita, razao: Math.round(ui.razao * 1000) / 1000,
    sub_dados: ui.subDados, sub_interp: ui.subInterp } }), 400);
}

function aplicarAparencia() {
  if (!prefs) return;
  const h = document.documentElement;
  h.dataset.paleta = prefs.paleta;
  h.dataset.tema = prefs.tema;
  h.dataset.fonte = prefs.fonte;
}

// Outra janela mudou as cores: esta acompanha.
function preferenciasMudaram(p) {
  prefs = p;
  aplicarAparencia();
  if (!$("config").hidden) preencherConfig();
}

// ---------------------------------------------------------------- abas e layout
function normalizarAba(qual) {
  if (["catalogo", "cadastro", "levantamento", "producao", "camadas"].includes(qual)) { ui.subDados = qual; return "dados"; }
  if (qual === "secao" || qual === "bloco") { ui.subInterp = qual; return "interp"; }
  if (qual === "inicio") return "projeto";
  return ABAS_SIAPP.includes(qual) ? qual : "projeto";
}

function vistaDe(aba) { return aba === "interp" ? ui.subInterp : aba; }

// Onde a aba está: "aqui", na janela própria dela (nome da aba) ou na "principal".
function destinoDe(aba) {
  if (MODO_JANELA) return aba === MODO_JANELA ? "aqui" : (ui.fora.has(aba) ? aba : "principal");
  return ui.fora.has(aba) ? aba : "aqui";
}

function trocarAba(qual) {
  const aba = normalizarAba(qual);
  const destino = destinoDe(aba);
  if (destino !== "aqui") {
    if (destino === aba) api.abrir_janela(aba);          // já aberta: vem para a frente
    else api.janela_chamar("principal", "trocarAba", [qual]);
    return;
  }
  if (!MODO_JANELA) {
    if (ui.dividida && aba === ui.direita) ui.direita = ui.ativa;
    ui.ativa = aba;
    if (ui.direita === ui.ativa) ui.dividida = false;
  }
  aplicarLayout(new Set([aba]));
  guardarLayout();
}

// Leva o usuário a uma aba e chama uma função dela — na janela onde a aba estiver.
async function irPara(qual, funcao, ...args) {
  const aba = normalizarAba(qual);
  const destino = destinoDe(aba);
  if (destino === "aqui") {
    trocarAba(qual);
    if (funcao && typeof window[funcao] === "function") return window[funcao](...args);
    return;
  }
  const r = await chamar(null, "janela_chamar", destino, "irPara", [qual, funcao || "", ...args]);
  if (r.ok && destino !== "principal") status(`${NOMES_ABAS[aba]} mostra o pedido na janela própria.`, "ok");
}

function abasVisiveis() {
  if (MODO_JANELA) return [MODO_JANELA];
  return ui.dividida ? [ui.ativa, ui.direita] : [ui.ativa];
}

function aplicarLayout(recarregar = new Set()) {
  const visiveis = abasVisiveis();
  const vistas = visiveis.map(vistaDe);
  for (const m of document.querySelectorAll(".area > main")) {
    const k = m.id.slice(6);
    const i = vistas.indexOf(k);
    m.hidden = i < 0;
    m.style.order = i <= 0 ? 1 : 3;
    m.style.flex = !ui.dividida || MODO_JANELA || i < 0 ? "" : `${i === 0 ? ui.razao : 1 - ui.razao} 1 0px`;
    m.classList.toggle("lado-dir", i === 1);
    const r = ui.recolhidas[k === "secao" || k === "bloco" ? "interp" : k];
    m.classList.toggle("recolhida", Boolean(r));
  }
  $("divisor").hidden = !(ui.dividida && !MODO_JANELA);
  for (const b of document.querySelectorAll(".aba[data-vista]")) {
    const a = b.dataset.vista;
    b.classList.toggle("ativa", a === visiveis[0]);
    b.classList.toggle("direita", visiveis[1] === a);
    b.classList.toggle("fora", ui.fora.has(a));
    b.setAttribute("aria-selected", a === visiveis[0]);
    b.title = ui.fora.has(a) ? "Está numa janela própria: clique para trazê-la para a frente"
      : visiveis[1] === a ? "Aberta na área da direita" : "";
  }
  for (const b of document.querySelectorAll("[data-interp]")) b.classList.toggle("ativa", b.dataset.interp === ui.subInterp);
  for (const b of document.querySelectorAll(".sub-nav [data-sub]")) b.classList.toggle("ativa", b.dataset.sub === ui.subDados);
  for (const p of document.querySelectorAll("[data-sub-painel]")) p.hidden = p.dataset.subPainel !== ui.subDados;
  for (const p of document.querySelectorAll("[data-sub-lat]")) p.hidden = p.dataset.subLat !== ui.subDados;
  desenharAcoesTopo();
  const novas = visiveis.filter((a) => !ui.visiveis.has(a) || recarregar.has(a));
  ui.visiveis = new Set(visiveis);
  for (const a of novas) (AO_ABRIR_ABA[a] || (() => {}))();
  window.dispatchEvent(new Event("resize"));
}

function desenharAcoesTopo() {
  $("btn-dividir").hidden = Boolean(MODO_JANELA);
  $("btn-dividir").classList.toggle("on", ui.dividida);
  $("btn-dividir").querySelector("span").textContent = ui.dividida ? "Desfazer divisão" : "Dividir";
  $("div-dir-box").hidden = !ui.dividida || Boolean(MODO_JANELA);
  $("div-trocar").hidden = !ui.dividida || Boolean(MODO_JANELA);
  if (ui.dividida) {
    const sel = limpar($("div-dir"));
    for (const a of ABAS_SIAPP) {
      if (a === ui.ativa || ui.fora.has(a)) continue;
      sel.appendChild(new Option(NOMES_ABAS[a], a));
    }
    sel.value = ui.direita;
  }
  const bj = $("btn-janela");
  bj.querySelector("span").textContent = MODO_JANELA ? "Voltar para a principal" : "Abrir em janela";
  bj.title = MODO_JANELA ? "Fecha esta janela e devolve a aba para a janela principal"
    : "Abre a aba ativa numa janela própria, para outro monitor";
  bj.disabled = !MODO_JANELA && ui.ativa === "projeto";
}

function alternarDivisao() {
  if (ui.dividida) {
    ui.dividida = false;
  } else {
    const livres = ABAS_SIAPP.filter((a) => a !== ui.ativa && !ui.fora.has(a));
    if (!livres.length) { status("Não há outra aba na janela principal para dividir.", "erro"); return; }
    if (!livres.includes(ui.direita)) ui.direita = livres.includes(ui.ativa === "mapa" ? "docs" : "mapa")
      ? (ui.ativa === "mapa" ? "docs" : "mapa") : livres[0];
    ui.dividida = true;
    status(`Janela dividida: ${NOMES_ABAS[ui.ativa]} | ${NOMES_ABAS[ui.direita]}. Arraste a divisória para ajustar.`, "ok");
  }
  aplicarLayout(new Set(ui.dividida ? [ui.direita] : []));
  guardarLayout();
}

function trocarLados() {
  [ui.ativa, ui.direita] = [ui.direita, ui.ativa];
  aplicarLayout();
  guardarLayout();
}

function ligarDivisor() {
  const d = $("divisor");
  d.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    d.setPointerCapture(e.pointerId);
    const area = $("area").getBoundingClientRect();
    document.body.classList.add("arrastando");
    const mover = (ev) => {
      ui.razao = Math.min(0.8, Math.max(0.2, (ev.clientX - area.left) / area.width));
      aplicarLayoutTamanho();
    };
    const soltar = () => {
      d.removeEventListener("pointermove", mover);
      document.body.classList.remove("arrastando");
      window.dispatchEvent(new Event("resize"));
      guardarLayout();
    };
    d.addEventListener("pointermove", mover);
    d.addEventListener("pointerup", soltar, { once: true });
    d.addEventListener("pointercancel", soltar, { once: true });
  });
  d.addEventListener("dblclick", () => { ui.razao = 0.5; aplicarLayoutTamanho(); window.dispatchEvent(new Event("resize")); guardarLayout(); });
}

function aplicarLayoutTamanho() {
  const [a, b] = abasVisiveis().map(vistaDe);
  if ($("vista-" + a)) $("vista-" + a).style.flex = `${ui.razao} 1 0px`;
  if (b && $("vista-" + b)) $("vista-" + b).style.flex = `${1 - ui.razao} 1 0px`;
}

// ---------------------------------------------------------------- barra lateral recolhível
function montarRecolher() {
  for (const lat of document.querySelectorAll(".grade > .lateral")) {
    const main = lat.parentElement;
    const k = main.id.slice(6);
    const aba = k === "secao" || k === "bloco" ? "interp" : k;
    const b = el("button", "recolher", "");
    b.type = "button";
    b.innerHTML = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10 3L5 8l5 5"></path></svg>';
    b.setAttribute("aria-label", "Recolher ou abrir a barra lateral");
    b.title = "Recolher a barra lateral";
    b.onclick = () => {
      ui.recolhidas[aba] = !ui.recolhidas[aba];
      if (!ui.recolhidas[aba]) delete ui.recolhidas[aba];
      aplicarLayout();
      guardarPreferencias({ recolhidas: { ...Object.fromEntries(ABAS_SIAPP.map((x) => [x, false])), ...ui.recolhidas } });
    };
    lat.prepend(b);
    const rot = el("span", "rotulo-vertical", lat.dataset.titulo || "");
    rot.setAttribute("aria-hidden", "true");
    lat.prepend(rot);
  }
}

// ---------------------------------------------------------------- janelas próprias
async function abrirOuVoltarJanela() {
  if (MODO_JANELA) {
    await chamar(null, "fechar_janela", MODO_JANELA);
    return;
  }
  const aba = ui.ativa;
  if (aba === "projeto") return;
  const r = await chamar($("btn-janela"), "abrir_janela", aba);
  if (r.ok) status(`${NOMES_ABAS[aba]} abriu numa janela própria. Feche-a (ou “Voltar para a principal”) para devolver a aba.`, "ok");
}

// Chamado pelo motor quando uma janela abre ou fecha (em todas as janelas).
function janelasMudaram(abertas) {
  const antes = ui.fora;
  ui.fora = new Set(abertas || []);
  if (MODO_JANELA) { desenharAcoesTopo(); return; }
  const recarregar = new Set();
  for (const a of antes) if (!ui.fora.has(a)) { ui.ativa = a; recarregar.add(a); }     // voltou: mostra
  if (ui.fora.has(ui.ativa)) {
    ui.ativa = (ui.dividida && !ui.fora.has(ui.direita)) ? ui.direita : (ABAS_SIAPP.find((x) => !ui.fora.has(x)) || "projeto");
  }
  if (ui.dividida && (ui.fora.has(ui.direita) || ui.direita === ui.ativa)) ui.dividida = false;
  aplicarLayout(recarregar);
  guardarLayout();
}

// ---------------------------------------------------------------- histórico de mensagens
const historicoStatus = [];

function anotarStatus(texto, tipo) {
  if (!texto) return;
  const agora = new Date();
  const hora = agora.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const ultimo = historicoStatus[historicoStatus.length - 1];
  if (ultimo && ultimo.texto === texto) return;
  if (ultimo && tipo === "trab" && ultimo.tipo === "trab") historicoStatus.pop();     // progresso: só o último
  historicoStatus.push({ hora, texto, tipo });
  if (historicoStatus.length > 200) historicoStatus.shift();
  if ($("ini-msgs")) desenharMensagens($("ini-msgs"), 5);
  if (!$("historico").hidden) desenharMensagens($("hist-lista"), 200);
}

function desenharMensagens(ul, n) {
  limpar(ul);
  const lista = historicoStatus.slice(-n).reverse();
  if (!lista.length) { ul.appendChild(el("li", "ajuda", "Nenhuma mensagem ainda.")); return; }
  for (const m of lista) {
    const li = el("li", m.tipo || "");
    li.append(el("span", "hora", m.hora), el("span", "", m.texto));
    ul.appendChild(li);
  }
}

function alternarPopover(id, desenhar) {
  const p = $(id);
  const abrir = p.hidden;
  for (const o of document.querySelectorAll(".popover")) o.hidden = true;
  p.hidden = !abrir;
  if (abrir && desenhar) desenhar();
}

// ---------------------------------------------------------------- exportações
async function desenharExportacoes() {
  const box = limpar($("exp-lista"));
  if (!projetoAberto) { box.appendChild(el("p", "ajuda", "Abra o projeto primeiro.")); return; }
  const r = await chamar(null, "pastas_exportacao");
  if (!r.ok) return;
  for (const p of r.pastas) {
    const linha = el("div", "pasta-linha");
    const txt = el("div", "");
    txt.append(el("code", "", `${p.nome}\\`), el("small", "", ` ${p.descricao}`));
    txt.appendChild(el("small", "ajuda bloco", p.existe ? `${numero(p.arquivos, 0)} arquivo(s)` +
      (p.atualizado ? ` · último em ${dataCurta(p.atualizado)}` : "") : "ainda vazia"));
    const b = el("button", "btn secundario pequeno", "Abrir");
    b.onclick = async () => {
      const x = await chamar(b, "abrir_pasta_exportacao", p.nome);
      if (x.ok) status(`Pasta ${x.pasta} aberta no Explorador de Arquivos.`, "ok");
    };
    linha.append(txt, b);
    box.appendChild(linha);
  }
}

// ---------------------------------------------------------------- configurações e diagnóstico
function abrirConfig(qual = "config") {
  $("config").hidden = false;
  mostrarAbaConfig(qual);
  preencherConfig();
}

function mostrarAbaConfig(qual) {
  for (const b of document.querySelectorAll("[data-cfg]")) b.classList.toggle("ativa", b.dataset.cfg === qual);
  $("cfg-config").hidden = qual !== "config";
  $("cfg-diag").hidden = qual !== "diag";
  if (qual === "diag") carregarDiagnostico();
}

function preencherConfig() {
  if (!prefs) return;
  const box = limpar($("cfg-paletas"));
  for (const [id, nome, c1, c2, c3, desc] of PALETAS_SIAPP) {
    const b = el("button", "paleta" + (prefs.paleta === id ? " ativa" : ""));
    b.type = "button";
    b.title = desc;
    const am = el("span", "amostras");
    for (const c of [c1, c2, c3]) { const s = el("span"); s.style.background = c; am.appendChild(s); }
    b.append(am, el("span", "", nome + (id === "marinho" ? " (padrão)" : "")));
    b.onclick = () => mudarAparencia({ paleta: id });
    box.appendChild(b);
  }
  $("cfg-tema").value = prefs.tema;
  $("cfg-fonte").value = prefs.fonte;
  $("cfg-abrir").checked = prefs.abrir_ao_iniciar;
  $("cfg-arranjo").checked = prefs.lembrar_arranjo;
}

async function mudarAparencia(m) {
  prefs = { ...prefs, ...m };
  aplicarAparencia();
  preencherConfig();
  await guardarPreferencias(m);      // o motor avisa as outras janelas (preferenciasMudaram)
}

let textoDiagnostico = "";
async function carregarDiagnostico() {
  const box = limpar($("dg-conteudo"));
  const r = await chamar(null, "diagnostico");
  if (!r.ok) return;
  const linhas = [`SIAPP — diagnóstico (${new Date().toLocaleString("pt-BR")})`];
  const t = el("table", "tabela dg-versoes");
  for (const [k, v] of Object.entries(r.versoes)) {
    const tr = document.createElement("tr");
    tr.append(el("th", "", k), el("td", "", v));
    t.appendChild(tr);
    linhas.push(`${k}: ${v}`);
  }
  box.appendChild(t);
  const info = `Pasta: ${r.pasta} · banco ${tamanho(r.banco_bytes)} · OCR ${r.ocr_instalado ? "instalado" : "não instalado"} · ` +
    `janelas: ${r.janelas.map((j) => NOMES_ABAS[j] || j).join(", ")}`;
  box.appendChild(el("p", "ajuda", info));
  linhas.push(info, "");
  box.appendChild(el("h3", "", "Erros desta sessão"));
  linhas.push("Erros desta sessão:");
  if (!r.erros_sessao.length) box.appendChild(el("p", "ajuda", "Nenhum."));
  for (const e of r.erros_sessao) {
    const p = el("div", "dg-erro");
    p.append(el("code", "", `${e.quando.slice(11)} ${e.funcao}`), el("span", "", ` ${e.erro}`));
    box.appendChild(p);
    linhas.push(`  ${e.quando} ${e.funcao}: ${e.erro}`);
  }
  box.appendChild(el("h3", "", "Últimos erros no siapp.log"));
  linhas.push("", "Últimos erros no siapp.log:");
  if (!r.erros_log.length) box.appendChild(el("p", "ajuda", "Nenhum."));
  for (const e of r.erros_log) {
    const p = el("div", "dg-erro");
    p.append(el("code", "", dataCurta(e.quando.replace(" ", "T"))), el("span", "", ` ${e.texto}`));
    if (e.causa) p.appendChild(el("small", "bloco", e.causa));
    box.appendChild(p);
    linhas.push(`  ${e.quando} ${e.nivel} ${e.texto}${e.causa ? " — " + e.causa : ""}`);
  }
  box.appendChild(el("h3", "", "Ações mais demoradas desta sessão"));
  linhas.push("", "Ações mais demoradas:");
  if (!r.lentas.length) box.appendChild(el("p", "ajuda", "Nenhuma ainda."));
  const tl = el("table", "tabela");
  for (const c of r.lentas) {
    const tr = document.createElement("tr");
    tr.append(el("td", "", c.funcao), el("td", "num", `${numero(c.ms / 1000, 1)} s`), el("td", "ajuda", c.quando.slice(11)));
    tl.appendChild(tr);
    linhas.push(`  ${c.funcao}: ${(c.ms / 1000).toFixed(1)} s`);
  }
  if (r.lentas.length) box.appendChild(tl);
  textoDiagnostico = linhas.join("\n");
}

async function copiarDiagnostico() {
  if (!textoDiagnostico) await carregarDiagnostico();
  let ok = false;
  try { await navigator.clipboard.writeText(textoDiagnostico); ok = true; } catch (e) { /* tenta o jeito antigo */ }
  if (!ok) {
    const ta = el("textarea");
    ta.value = textoDiagnostico;
    document.body.appendChild(ta);
    ta.select();
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    ta.remove();
  }
  status(ok ? "Diagnóstico copiado: cole na mensagem (versões, erros e tempos)." : "Não consegui copiar; selecione o texto e use Ctrl+C.", ok ? "ok" : "erro");
}

// ---------------------------------------------------------------- abertura do projeto
function progressoAbertura(p) {
  const box = $("abertura");
  if (!box) return;
  if (!abrindoProjeto) return;     // outra janela abrindo: esta não cobre a tela
  box.hidden = false;
  $("ab-texto").textContent = `Passo ${p.passo} de ${p.total}`;
  $("ab-barra").style.width = `${Math.round(((p.passo - 0.5) / p.total) * 100)}%`;
  const ol = $("ab-passos");
  const itens = [...ol.children];
  for (const li of itens) { li.className = "feito"; }
  const ultimo = itens[itens.length - 1];
  if (ultimo && ultimo.dataset.passo === String(p.passo)) ultimo.textContent = p.texto;
  else { const li = el("li", "", p.texto); li.dataset.passo = p.passo; ol.appendChild(li); }
  ol.lastElementChild.className = "atual";
}

let abrindoProjeto = false;
function inicioAbertura() {
  abrindoProjeto = true;
  limpar($("ab-passos"));
  $("ab-barra").style.width = "0%";
  $("ab-texto").textContent = "Começando…";
}
function fimAbertura() {
  abrindoProjeto = false;
  $("abertura").hidden = true;
}

// Outra janela abriu o projeto: esta passa a funcionar também.
function projetoAbertoEmOutraJanela(info) {
  if (projetoAberto) return;
  projetoAberto = true;
  if (typeof liberarProjeto === "function") liberarProjeto(info);
}

// ---------------------------------------------------------------- ligações
function ligarJanelas() {
  ligarDivisor();
  montarRecolher();
  ligar("btn-dividir", "onclick", alternarDivisao);
  ligar("div-trocar", "onclick", trocarLados);
  ligar("div-dir", "onchange", () => { ui.direita = $("div-dir").value; aplicarLayout(new Set([ui.direita])); guardarLayout(); });
  ligar("btn-janela", "onclick", abrirOuVoltarJanela);
  ligar("btn-exportacoes", "onclick", () => alternarPopover("exportacoes", desenharExportacoes));
  ligar("exp-fechar", "onclick", () => { $("exportacoes").hidden = true; });
  ligar("btn-historico", "onclick", () => alternarPopover("historico", () => desenharMensagens($("hist-lista"), 200)));
  ligar("status", "onclick", () => alternarPopover("historico", () => desenharMensagens($("hist-lista"), 200)));
  ligar("hist-fechar", "onclick", () => { $("historico").hidden = true; });
  ligar("ini-historico", "onclick", () => alternarPopover("historico", () => desenharMensagens($("hist-lista"), 200)));
  ligar("btn-config", "onclick", () => abrirConfig("config"));
  ligar("cfg-fechar", "onclick", () => { $("config").hidden = true; });
  $("config").addEventListener("click", (e) => { if (e.target === $("config")) $("config").hidden = true; });
  for (const b of document.querySelectorAll("[data-cfg]")) b.onclick = () => mostrarAbaConfig(b.dataset.cfg);
  ligar("cfg-tema", "onchange", () => mudarAparencia({ tema: $("cfg-tema").value }));
  ligar("cfg-fonte", "onchange", () => mudarAparencia({ fonte: $("cfg-fonte").value }));
  ligar("cfg-abrir", "onchange", () => guardarPreferencias({ abrir_ao_iniciar: $("cfg-abrir").checked }));
  ligar("cfg-arranjo", "onchange", () => guardarPreferencias({ lembrar_arranjo: $("cfg-arranjo").checked }));
  ligar("dg-copiar", "onclick", copiarDiagnostico);
  ligar("dg-log", "onclick", () => chamar($("dg-log"), "abrir_log"));
  ligar("dg-atualizar", "onclick", carregarDiagnostico);
  for (const b of document.querySelectorAll("[data-interp]")) b.onclick = () => trocarAba(b.dataset.interp);
  for (const b of document.querySelectorAll(".sub-nav [data-sub]")) b.onclick = () => {
    ui.subDados = b.dataset.sub;
    if (ui.subDados !== "catalogo" && !$("gaveta").hidden) fecharGaveta();
    aplicarLayout(new Set(["dados"]));
    guardarLayout();
  };
  if (MODO_JANELA) {
    document.body.classList.add("destacada");
    $("janela-nome").hidden = false;
    $("janela-nome").textContent = NOMES_ABAS[MODO_JANELA] || MODO_JANELA;
    document.title = `SIAPP — ${NOMES_ABAS[MODO_JANELA] || MODO_JANELA}`;
  }
}
