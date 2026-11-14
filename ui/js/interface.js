// SIAPP — peças da interface que valem para todas as abas (0.57): menus do topo, janela de
// diálogo, menu Ajuda, busca de poço (Ctrl+K), atalhos de teclado editáveis, avisos de
// primeira vez, avisos no canto da tela e explicações longas atrás de um "?".
//
// Atalhos e avisos já vistos ficam nas preferências (preferencias.json, chaves "atalhos" e
// "avisos_vistos"), então valem para todas as janelas e sobrevivem a uma reinstalação.
"use strict";

// ---------------------------------------------------------------- menus (botão + lista)
function fecharMenus(exceto) {
  for (const m of document.querySelectorAll(".menu")) {
    if (m === exceto) continue;
    const pop = m.querySelector(":scope > .menu-pop");
    const bt = m.querySelector(":scope > [aria-haspopup]");
    if (pop) pop.hidden = true;
    if (bt) bt.setAttribute("aria-expanded", "false");
  }
}

function ligarMenus() {
  for (const m of document.querySelectorAll(".menu")) {
    const bt = m.querySelector(":scope > [aria-haspopup]");
    const pop = m.querySelector(":scope > .menu-pop");
    if (!bt || !pop) continue;
    bt.addEventListener("click", (e) => {
      e.stopPropagation();
      const abrir = pop.hidden;
      fecharMenus(m);
      pop.hidden = !abrir;
      bt.setAttribute("aria-expanded", String(abrir));
    });
    // escolher um item fecha o menu (o item faz o resto no onclick dele)
    pop.addEventListener("click", (e) => { if (e.target.closest("button")) fecharMenus(); });
  }
  document.addEventListener("click", (e) => { if (!e.target.closest(".menu")) fecharMenus(); });
}

// ---------------------------------------------------------------- janela de diálogo
let aoFecharDialogo = null;

function abrirDialogo(titulo, corpo, botoes = [], classe = "") {
  fecharDialogo();
  fecharMenus();
  $("dlg-titulo").textContent = titulo;
  limpar($("dlg-corpo")).appendChild(corpo);
  const pe = limpar($("dlg-pe"));
  for (const b of botoes) pe.appendChild(b);
  pe.hidden = !botoes.length;
  $("dialogo").querySelector(".modal").className = "modal dialogo " + classe;
  $("dialogo").hidden = false;
  const foco = $("dialogo").querySelector("input, .dlg-pe .btn:not(.secundario), .dlg-pe .btn");
  if (foco) foco.focus();
}

function fecharDialogo() {
  if ($("dialogo").hidden) return;
  $("dialogo").hidden = true;
  limpar($("dlg-corpo"));
  const f = aoFecharDialogo;
  aoFecharDialogo = null;
  if (f) f();
}

function botaoDialogo(texto, classe, fn) {
  const b = el("button", classe, texto);
  b.type = "button";
  b.onclick = fn;
  return b;
}

// ---------------------------------------------------------------- menu Ajuda
function conteudoModelo(id) {
  const t = $(id);
  const caixa = el("div", "dlg-ajuda");
  if (t) caixa.appendChild(t.content.cloneNode(true));
  return caixa;
}

const AJUDA = {
  guia: () => abrirDialogo("Guia do REATE", conteudoModelo("tpl-guia"), [], "largo"),
  limites: () => {
    const c = conteudoModelo("tpl-limites");
    c.appendChild(el("p", "ajuda", "Os limites que mudam o que você faz aparecem também na hora em que importam: " +
      "ao processar documentos, ao calcular a avaliação e ao montar o modelo 3D."));
    abrirDialogo("Limites e confiabilidade", c);
  },
  atalhos: () => abrirAtalhos(),
  novidades: () => abrirNovidades(),
  diag: () => abrirConfig("diag"),
  doacao: () => abrirDoacao(),
  sobre: () => {
    const c = el("div", "dlg-sobre");
    c.append(el("p", "dlg-sobre-nome", `SIAPP ${$("versao").textContent}`),
             el("p", "", "Sistema Integrado de Aquisição e Processamento de Perfis."),
             el("p", "", "Transforma o acervo público de poços da ANP (portal REATE) em dados organizados: " +
               "catálogo, documentos, perfis, correlação e modelo 3D."),
             el("p", "ajuda", "Código aberto (AGPL-3.0) · Ruan da Silva Nobre · PIBIC UFAL"));
    const botoes = [];
    if (doacaoConfig) {
      const b = el("button", "btn secundario", "Apoie o projeto");
      b.type = "button";
      b.onclick = abrirDoacao;
      botoes.push(b);
    }
    abrirDialogo("Sobre o SIAPP", c, botoes);
  },
};

// ---------------------------------------------------------------- Apoie o projeto (0.67)
// Só aparece se recursos/doacao.json tiver chave Pix (com nome e cidade) ou um link https. Nada é inventado aqui.
let doacaoConfig = null;

async function prepararDoacao() {
  const r = await chamar(null, "doacao");
  doacaoConfig = r.ok && r.ativo ? r : null;
  $("menu-doacao").hidden = !doacaoConfig;
}

async function copiarParaDoacao(texto, botao) {
  let ok = false;
  try { await navigator.clipboard.writeText(texto); ok = true; } catch (e) { /* abaixo: seleciona para Ctrl+C */ }
  if (ok) {
    const antes = botao.textContent;
    botao.textContent = "Copiado";
    setTimeout(() => { botao.textContent = antes; }, 1500);
  } else {
    status("Não deu para copiar sozinho: o texto ficou selecionado, use Ctrl+C.", "erro");
  }
  return ok;
}

function linhaCopiavel(rotulo, valor, id) {
  const caixa = el("div", "doacao-linha");
  const campo = el("input");
  campo.readOnly = true;
  campo.value = valor;
  campo.id = id;
  campo.onfocus = () => campo.select();
  const b = el("button", "btn secundario pequeno", "Copiar");
  b.type = "button";
  b.onclick = async () => { if (!(await copiarParaDoacao(valor, b))) { campo.focus(); campo.select(); } };
  caixa.append(el("label", "doacao-rotulo", rotulo), campo, b);
  return caixa;
}

function abrirDoacao() {
  const d = doacaoConfig;
  if (!d) return;
  const c = el("div", "dlg-doacao");
  c.appendChild(el("p", "", d.texto));
  if (d.pix) {
    c.appendChild(el("h3", "", "Pix"));
    c.appendChild(linhaCopiavel(`Chave (${d.pix.tipo})`, d.pix.chave, "doacao-pix-chave"));
    c.appendChild(linhaCopiavel("Pix copia e cola", d.pix.copia_e_cola, "doacao-pix-codigo"));
    c.appendChild(el("p", "ajuda", `No app do banco: Pix › Pix copia e cola. Recebedor: ${d.pix.nome} (${d.pix.cidade}). ` +
      "Você escolhe o valor."));
  }
  if (d.links.length) {
    c.appendChild(el("h3", "", d.pix ? "Outras formas" : "Como apoiar"));
    const ul = el("ul", "doacao-links");
    for (const l of d.links) {
      const a = el("a", "", l.rotulo);
      a.href = l.url;
      a.target = "_blank";
      a.rel = "noopener";
      const li = el("li");
      li.append(a, el("span", "ajuda", " " + l.url));
      ul.appendChild(li);
    }
    c.appendChild(ul);
  }
  c.appendChild(el("p", "ajuda", "Doar é opcional: o SIAPP é gratuito e continua igual para todos."));
  abrirDialogo(d.titulo, c);
}

// O que mudou nas últimas versões (do CHANGELOG), para quem acabou de receber uma versão nova.
async function abrirNovidades() {
  const r = await chamar(null, "novidades");
  if (!r.ok) return;
  const c = el("div", "dlg-ajuda novidades");
  for (const v of r.versoes) {
    c.appendChild(el("h2", "", `${v.versao}${v.data ? " — " + dataCurta(v.data) : ""}`));
    if (v.resumo) c.appendChild(el("p", "", v.resumo));
    for (const s of v.secoes) {
      c.appendChild(el("h3", "", s.titulo));
      const ul = el("ul");
      for (const i of s.itens) ul.appendChild(el("li", "", i));
      c.appendChild(ul);
    }
  }
  abrirDialogo("Novidades", c, [], "largo");
}

// ---------------------------------------------------------------- nome do projeto no topo
function mostrarProjetoNoTopo(pasta, nomeProjeto) {
  const nome = nomeProjeto || String(pasta || "").split(/[\\/]/).filter(Boolean).pop() || "";
  $("projeto-nome").textContent = nome || "Nenhum projeto aberto";
  $("projeto-topo").title = nome ? `Projeto: ${pasta}\nInício: o projeto e os módulos` : "Início: abrir o projeto";
  $("projeto-topo").classList.toggle("aberto", Boolean(nome));
}

// ---------------------------------------------------------------- busca de poço
function abrirBusca() {
  const caixa = el("div", "busca-poco");
  const inp = el("input");
  inp.type = "search";
  inp.id = "busca-poco";
  inp.autocomplete = "off";
  inp.placeholder = "Nome do poço, em qualquer grafia (ex.: 7-GMR-13)";
  const lista = el("ul", "busca-lista");
  lista.id = "busca-lista";
  lista.setAttribute("role", "listbox");
  caixa.append(inp, lista);
  let itens = [], sel = 0, pedido = 0, espera = null;

  function desenhar(msg) {
    limpar(lista);
    if (msg) { lista.appendChild(el("li", "busca-nada", msg)); return; }
    itens.forEach((p, i) => {
      const li = el("li", i === sel ? "on" : "");
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", String(i === sel));
      const nome = el("strong", "", p.id);
      const extra = [p.bacia, p.campo, p.como ? `achado como ${p.como}` : ""].filter(Boolean).join(" · ");
      li.append(nome, el("span", "", extra));
      li.onclick = () => escolher(p.id);
      lista.appendChild(li);
    });
  }
  async function procurar() {
    const t = inp.value.trim();
    if (!projetoAberto) return desenhar("Abra o projeto primeiro.");
    if (t.replace(/[^0-9a-z]/gi, "").length < 2) { itens = []; return desenhar("Digite ao menos 2 letras ou números."); }
    const n = ++pedido;
    const r = await chamar(null, "buscar_pocos", t);
    if (n !== pedido || !r.ok) return;
    itens = r.pocos;
    sel = 0;
    desenhar(itens.length ? "" : "Nenhum poço com esse nome no cadastro nem no catálogo deste projeto.");
  }
  function escolher(id) {
    fecharDialogo();
    irPara("mapa", "abrirFicha", id);
  }
  inp.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(procurar, 150); });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && itens.length) { sel = Math.min(sel + 1, itens.length - 1); desenhar(); e.preventDefault(); }
    else if (e.key === "ArrowUp" && itens.length) { sel = Math.max(sel - 1, 0); desenhar(); e.preventDefault(); }
    else if (e.key === "Enter" && itens[sel]) { escolher(itens[sel].id); e.preventDefault(); }
  });
  abrirDialogo("Buscar poço", caixa, [], "estreito no-alto");
  desenhar(projetoAberto ? "Digite o nome; Enter abre a ficha do primeiro." : "Abra o projeto primeiro.");
}

// ---------------------------------------------------------------- atalhos de teclado
function vistaAtual() { return vistaDe(ui.ativa); }
function visivel(e) { return e && !e.hidden && e.offsetParent !== null; }
function clicar(id) { const b = $(id); if (b && !b.disabled) b.click(); }

const PRINCIPAL_POR_VISTA = {
  dados: ["btn-conectar", "lv-iniciar", "tp-procurar"], docs: ["btn-processar"], perfis: ["av-calcular"],
  secao: ["sec-montar"], bloco: ["bl-montar"], viab: ["vb-avaliar"],
};
function acaoPrincipal() {
  for (const id of PRINCIPAL_POR_VISTA[vistaAtual()] || []) {
    const b = $(id);
    if (visivel(b) && !b.disabled) { b.click(); return true; }
  }
  return false;
}
function paginaDocumento(id) {
  if (vistaAtual() !== "docs" || !visivel($("painel-pagina")) || (typeof visorAberto === "function" && visorAberto())) return false;
  clicar(id);
  return true;
}

// Cada ação: id (o que fica nas preferências), nome, tecla padrão e o que faz.
// A função devolve false quando não se aplica na tela atual: aí a tecla segue o caminho normal.
const ATALHOS = [
  ["busca", "Buscar poço", "Ctrl+K", () => abrirBusca()],
  ["inicio", "Início", "Ctrl+0", () => trocarAba("projeto")],
  ["m1", "1 · Acervo", "Ctrl+1", () => trocarAba("dados")],
  ["m2", "2 · Documentos", "Ctrl+2", () => trocarAba("docs")],
  ["m3", "3 · Perfis", "Ctrl+3", () => trocarAba("perfis")],
  ["m4", "4 · Poços", "Ctrl+4", () => trocarAba("mapa")],
  ["m5", "5 · Correlação", "Ctrl+5", () => trocarAba("secao")],
  ["m6", "6 · Modelo 3D", "Ctrl+6", () => trocarAba("bloco")],
  ["atualizar", "Reler a aba do projeto (normalmente ela só relê quando algo mudou)", "F5", () => atualizarAbas()],
  ["principal", "Ação principal da tela (Conectar, Processar, Calcular, Montar…)", "Ctrl+Enter", acaoPrincipal],
  ["exportacoes", "Exportações", "Ctrl+E", () => clicar("btn-exportacoes")],
  ["config", "Configurações", "Ctrl+,", () => abrirConfig("config")],
  ["ajuda", "Menu Ajuda", "F1", () => clicar("btn-ajuda")],
  ["lateral", "Recolher ou abrir a barra lateral", "Ctrl+B", () => {
    const m = $("vista-" + vistaAtual());
    const r = m && m.querySelector(".lateral > .recolher");
    if (!r) return false;
    r.click();
  }],
  ["buscadoc", "Buscar no documento (Documentos)", "Ctrl+F", () => {
    if (vistaAtual() !== "docs") return false;
    $("busca").focus();
    $("busca").select();
  }],
  ["pgant", "Página anterior (Documentos)", "ArrowLeft", () => paginaDocumento("pg-ant")],
  ["pgprox", "Próxima página (Documentos)", "ArrowRight", () => paginaDocumento("pg-prox")],
].map(([id, nome, tecla, fn]) => ({ id, nome, tecla, fn }));
const ATALHOS_FIXOS = [["F3 · Shift+F3", "Próximo · anterior achado da busca (Documentos)"],
                       ["Esc", "Fechar a janela, o menu ou o painel aberto"]];

function teclaDe(a) {
  const t = prefs && prefs.atalhos ? prefs.atalhos[a.id] : undefined;
  return t === undefined ? a.tecla : t;
}

function comboDe(e) {
  let k = e.key;
  if (["Control", "Alt", "Shift", "Meta", "AltGraph", "Dead"].includes(k)) return "";
  if ((e.ctrlKey || e.altKey) && /^Digit\d$/.test(e.code || "")) k = e.code.slice(5);
  else if (k === " ") k = "Space";
  else if (k.length === 1) k = k.toUpperCase();
  const p = [];
  if (e.ctrlKey || e.metaKey) p.push("Ctrl");
  if (e.altKey) p.push("Alt");
  if (e.shiftKey && k.length > 1) p.push("Shift");
  p.push(k);
  return p.join("+");
}

function mostrarTecla(t) {
  if (!t) return "—";
  return t.replace("ArrowLeft", "←").replace("ArrowRight", "→").replace("ArrowUp", "↑").replace("ArrowDown", "↓");
}

function atualizarTeclasVisiveis() {
  const busca = ATALHOS.find((a) => a.id === "busca");
  $("btn-busca-tecla").textContent = mostrarTecla(teclaDe(busca));
  $("btn-busca-tecla").hidden = !teclaDe(busca);
  $("btn-busca").title = teclaDe(busca) ? `Buscar poço (${teclaDe(busca)})` : "Buscar poço";
}

let capturandoTecla = false;

function aoTeclar(e) {
  if (capturandoTecla) return;
  if (e.key === "Escape") {
    if (!$("dialogo").hidden) { fecharDialogo(); e.preventDefault(); e.stopPropagation(); return; }
    const aberto = [...document.querySelectorAll(".menu > .menu-pop")].some((p) => !p.hidden);
    if (aberto) { fecharMenus(); e.preventDefault(); e.stopPropagation(); }
    return;
  }
  if (!$("dialogo").hidden || !$("config").hidden) return;
  const c = comboDe(e);
  if (!c) return;
  const alvo = document.activeElement;
  const emCampo = alvo && (/^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName) || alvo.isContentEditable);
  for (const a of ATALHOS) {
    if (teclaDe(a) !== c) continue;
    // dentro de um campo, tecla sem Ctrl/Alt é do campo (setas, letras)
    if (emCampo && !/^(Ctrl|Alt)\+/.test(c) && !/^F\d+$/.test(c)) return;
    if (a.fn() !== false) { e.preventDefault(); e.stopPropagation(); }
    return;
  }
}

function abrirAtalhos() {
  const caixa = el("div", "dlg-atalhos");
  const tab = el("table", "tabela-atalhos");
  caixa.append(el("p", "ajuda", "Clique em Alterar e aperte a nova combinação. Se ela já for de outra ação, as duas trocam."),
               tab);

  function desenhar() {
    limpar(tab);
    for (const a of ATALHOS) {
      const tr = el("tr");
      const kb = el("kbd", "tecla", mostrarTecla(teclaDe(a)));
      const mudar = botaoDialogo("Alterar", "link", () => capturar(a, kb));
      const td2 = el("td"), td3 = el("td");
      td2.appendChild(kb);
      td3.appendChild(mudar);
      tr.append(el("td", "", a.nome), td2, td3);
      tab.appendChild(tr);
    }
    for (const [t, nome] of ATALHOS_FIXOS) {
      const tr = el("tr", "fixo");
      const td2 = el("td");
      td2.appendChild(el("kbd", "tecla", t));
      tr.append(el("td", "", nome), td2, el("td", "ajuda", "fixo"));
      tab.appendChild(tr);
    }
  }

  function capturar(a, kb) {
    capturandoTecla = true;
    kb.textContent = "aperte as teclas…";
    kb.classList.add("on");
    const pega = async (e) => {
      if (["Control", "Alt", "Shift", "Meta", "AltGraph"].includes(e.key)) return;
      e.preventDefault();
      e.stopPropagation();
      document.removeEventListener("keydown", pega, true);
      capturandoTecla = false;
      if (e.key === "Escape") { desenhar(); return; }
      const nova = comboDe(e);
      const dono = ATALHOS.find((x) => x.id !== a.id && teclaDe(x) === nova);
      const mudancas = { [a.id]: nova };
      if (dono) mudancas[dono.id] = teclaDe(a);
      const r = await guardarPreferencias({ atalhos: mudancas });
      if (!r.ok || prefs.atalhos[a.id] !== nova) status(`“${mostrarTecla(nova)}” não pode ser usada como atalho.`, "erro");
      else if (dono) status(`“${mostrarTecla(nova)}” era de ${dono.nome}: as duas ações trocaram de tecla.`, "ok");
      desenhar();
      atualizarTeclasVisiveis();
    };
    document.addEventListener("keydown", pega, true);
  }

  const restaurar = botaoDialogo("Restaurar os padrões", "btn secundario", async () => {
    const tirar = Object.fromEntries(Object.keys((prefs && prefs.atalhos) || {}).map((k) => [k, null]));
    await guardarPreferencias({ atalhos: tirar });
    desenhar();
    atualizarTeclasVisiveis();
  });
  desenhar();
  abrirDialogo("Atalhos de teclado", caixa, [restaurar]);
  aoFecharDialogo = () => { capturandoTecla = false; };
}

// ---------------------------------------------------------------- avisos de primeira vez
// Aparecem antes da ação em que o limite muda o que a pessoa faz. Sempre na primeira vez de cada
// sessão; "Não mostrar de novo" grava nas preferências.
const AVISOS_PRIMEIRA_VEZ = {
  ocr: { botao: "btn-processar", titulo: "Antes de ler documentos escaneados", itens: [
    "O OCR serve para achar a página, não para fornecer números: num teste com documento real, 6 de 18 " +
      "profundidades vieram erradas.",
    "Um número só entra no banco quando você o transcreve e confere na imagem da página.",
    "Tabelas e texto à mão costumam sair ruins. Use a busca para chegar à página e leia na imagem."] },
  avaliacao: { botao: "av-calcular", titulo: "Antes de calcular a avaliação", itens: [
    "O Rw não tem estimativa automática: o 0,05 padrão é só ponto de partida. Use um valor publicado.",
    "Compare o resultado com o referencial teórico da formação e, se houver, com a interpretação da operadora.",
    "Trechos com caliper ou DRHO ruins ficam marcados, mas não são apagados."] },
  bloco: { botao: "bl-montar", titulo: "Antes de montar o modelo 3D", itens: [
    "Entre os poços, a superfície é interpolação, não dado. Fora do contorno dos poços nada é desenhado.",
    "Confira o erro em Validar (deixar um poço de fora) antes de usar números do bloco.",
    "Com menos de 8 poços, a krigagem vira interpolação linear."] },
};
const avisosNestaSessao = new Set();
let passarAviso = "";

function ligarAvisosPrimeiraVez() {
  document.addEventListener("click", (e) => {
    for (const [chave, av] of Object.entries(AVISOS_PRIMEIRA_VEZ)) {
      const alvo = e.target.closest && e.target.closest("#" + av.botao);
      if (!alvo || alvo.disabled) continue;
      if (passarAviso === chave) { passarAviso = ""; return; }
      if (avisosNestaSessao.has(chave) || (prefs && prefs.avisos_vistos && prefs.avisos_vistos[chave])) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      const corpo = el("div", "aviso-pv");
      const ul = el("ul");
      for (const t of av.itens) ul.appendChild(el("li", "", t));
      const rot = el("label", "opcao");
      const chk = el("input");
      chk.type = "checkbox";
      chk.id = "aviso-nao-mostrar";
      rot.append(chk, el("span", "", "Não mostrar de novo"));
      corpo.append(ul, rot);
      abrirDialogo(av.titulo, corpo, [
        botaoDialogo("Cancelar", "btn secundario", fecharDialogo),
        botaoDialogo("Entendi, continuar", "btn", () => {
          avisosNestaSessao.add(chave);
          if (chk.checked) guardarPreferencias({ avisos_vistos: { [chave]: true } });
          fecharDialogo();
          passarAviso = chave;
          alvo.click();
        }),
      ]);
      return;
    }
  }, true);
}

// ---------------------------------------------------------------- avisos no canto da tela
// Erros sempre; "ok" só quando encerra um trabalho longo (mais de 3 s em andamento), para não
// competir com o rodapé a cada clique.
let inicioTrabalho = 0;

function mostrarAviso(texto, tipo) {
  if (tipo === "trab") { if (!inicioTrabalho) inicioTrabalho = Date.now(); return; }
  const longo = inicioTrabalho && Date.now() - inicioTrabalho > 3000;
  inicioTrabalho = 0;
  if (!texto || !(tipo === "erro" || (tipo === "ok" && longo))) return;
  avisoNoCanto(texto, tipo);
}

function avisoNoCanto(texto, tipo = "ok") {
  const caixa = $("avisos");
  if (!caixa) return;
  for (const a of caixa.children) if (a.textContent === texto) return;     // a mesma mensagem já está lá
  while (caixa.children.length >= 3) caixa.firstChild.remove();
  const a = el("div", "aviso " + tipo, texto);
  a.setAttribute("role", tipo === "erro" ? "alert" : "status");
  a.title = "Clique para fechar";
  a.onclick = () => a.remove();
  caixa.appendChild(a);
  setTimeout(() => { a.classList.add("saindo"); setTimeout(() => a.remove(), 300); }, tipo === "erro" ? 7000 : 4000);
}

// O atalho trouxe uma versão nova ao abrir (lançador, 0.58): avisa uma vez.
async function avisarAtualizacao() {
  const r = await chamar(null, "aviso_atualizacao");
  if (!r.ok || !r.aviso) return;
  const texto = `SIAPP atualizado: ${r.aviso.de} → ${r.aviso.para}. O que mudou: Ajuda › Novidades.`;
  status(texto, "ok");
  avisoNoCanto(texto, "ok");
}

// ---------------------------------------------------------------- explicações longas atrás de um "?"
function recolherExplicacoes() {
  for (const p of document.querySelectorAll(".lateral p.ajuda, .sub-painel p.ajuda, [data-com-painel] p.ajuda")) {
    if (p.id || p.className.trim() !== "ajuda" || p.querySelector("button, a, input, select")) continue;
    if (p.textContent.replace(/\s+/g, " ").trim().length < 90) continue;
    p.classList.add("explicacao");
    p.hidden = true;
    const bt = el("button", "explicar", "?");
    bt.type = "button";
    bt.title = "Mostrar a explicação";
    bt.setAttribute("aria-label", "Mostrar a explicação");
    bt.setAttribute("aria-expanded", "false");
    bt.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      p.hidden = !p.hidden;
      bt.classList.toggle("on", !p.hidden);
      bt.setAttribute("aria-expanded", String(!p.hidden));
    };
    const ant = p.previousElementSibling;
    if (ant && /^H[23]$/.test(ant.tagName)) ant.appendChild(bt);
    else {
      const linha = el("div", "explicar-linha");
      linha.append(bt, el("span", "", "Como funciona"));
      p.before(linha);
    }
  }
}

// ---------------------------------------------------------------- ligações
// 0.64: ao abrir uma caixa (details) numa coluna que rola, a coluna acompanha: mostra o que abriu inteiro, acima do pé
// fixo (Montar), sem passar do título da caixa. Antes, a caixa abria escondida embaixo e era preciso caçar a rolagem.
function acompanharAbertura(ev) {
  const d = ev.target;
  if (!(d instanceof HTMLDetailsElement) || !d.open) return;
  const col = d.closest(".lateral, .principal, .modal-corpo");
  if (!col) return;
  requestAnimationFrame(() => {
    const rc = col.getBoundingClientRect(), rd = d.getBoundingClientRect();
    const pe = [...col.querySelectorAll(".etapa-montar")].find((e) => getComputedStyle(e).position === "sticky");
    const fundo = rc.bottom - (pe && !d.contains(pe) ? pe.getBoundingClientRect().height : 0) - 8;
    const sobra = rd.bottom - fundo;                          // quanto do que abriu ficou para baixo do visível
    const ate = rd.top - rc.top - 8;                          // não passa do título da caixa
    const passo = Math.min(sobra, ate);
    if (passo > 0) col.scrollBy({ top: passo, behavior: "smooth" });
  });
}

function ligarInterface() {
  document.addEventListener("toggle", acompanharAbertura, true);
  ligarMenus();
  for (const b of document.querySelectorAll("[data-ajuda]")) b.onclick = () => AJUDA[b.dataset.ajuda]();
  ligar("dlg-fechar", "onclick", fecharDialogo);
  $("dialogo").addEventListener("click", (e) => { if (e.target === $("dialogo")) fecharDialogo(); });
  ligar("btn-busca", "onclick", abrirBusca);
  ligar("projeto-topo", "onclick", () => trocarAba("projeto"));
  document.addEventListener("keydown", aoTeclar, true);
  ligarAvisosPrimeiraVez();
  recolherExplicacoes();
  atualizarTeclasVisiveis();
  if (MODO_JANELA) {
    $("btn-busca").hidden = true;
    $("projeto-topo").hidden = true;
  }
}
