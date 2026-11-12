// SIAPP — Início (0.58): o projeto aberto, os módulos com o estado de cada um e os outros projetos.
// Cada projeto é uma pasta com o seu banco e os seus arquivos (motor/projetos.py).
"use strict";

const ICONES_MODULO = {
  dados: '<path d="M2.5 4.5h11v8h-11z"/><path d="M2.5 7h11"/><path d="M6 9.5h4"/>',
  docs: '<path d="M4 1.8h5.5L12 4.3v9.9H4z"/><path d="M9.5 1.8v2.5H12"/><path d="M6 8h4M6 10.5h4"/>',
  perfis: '<path d="M4 2v12M8 2c-2 3 2 4 0 6s2 3 0 6M12 2v12"/>',
  mapa: '<path d="M8 14s-4.5-4.4-4.5-7.5a4.5 4.5 0 0 1 9 0C12.5 9.6 8 14 8 14z"/><circle cx="8" cy="6.5" r="1.6"/>',
  secao: '<path d="M3 2v12M8 2v12M13 2v12"/><path d="M3 5l5 1.5 5-1M3 9.5l5 1 5-.5"/>',
  bloco: '<path d="M8 1.8 13.5 5v6L8 14.2 2.5 11V5z"/><path d="M2.5 5 8 8.2 13.5 5M8 8.2v6"/>',
};
const MODULOS = [
  ["dados", "1", "Acervo"], ["docs", "2", "Documentos"], ["perfis", "3", "Perfis"],
  ["mapa", "4", "Poços"], ["secao", "5", "Correlação"], ["bloco", "6", "Modelo 3D"],
];
const EXTRAS = [["viab", "Viabilidade", "Distância à infraestrutura e custo do duto"],
                ["comunidade", "Comunidade", "Correções e dados compartilhados"]];

function svgIcone(caminhos) {
  return '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" ' +
         'stroke-linejoin="round" aria-hidden="true">' + caminhos + "</svg>";
}
const numInicio = (v) => numero(v || 0, 0);

async function carregarInicio() {
  carregarProjetos();
  $("ini-sec-modulos").hidden = !projetoAberto;
  if (!projetoAberto) return;
  const r = await chamar(null, "inicio_resumo");
  if (r.ok) desenharModulos(r);
}

// ---------------------------------------------------------------- módulos
// Uma ou duas linhas com o estado de cada módulo e o próximo passo. `alerta`: há algo esperando por você.
function estadoModulo(k, r) {
  if (k === "dados") {
    const d = r.dados;
    return { linhas: [d.bacias.length ? `${d.bacias.join(", ")}: levantada(s)` : "Nenhuma bacia levantada ainda",
                      `${numInicio(d.pocos)} poços · ${numInicio(d.listados)} arquivos listados · ${numInicio(d.baixados)} baixados`],
             acao: d.bacias.length ? "Continuar" : "Começar" };
  }
  if (k === "docs") {
    const d = r.docs;
    if (!d.total) return { linhas: ["Nenhum documento baixado"], acao: "Abrir" };
    return { linhas: [`${numInicio(d.total)} documento(s)`, d.sem_texto ? `${numInicio(d.sem_texto)} sem texto (esperando o OCR)` : "Todos com texto"],
             acao: d.sem_texto ? "Processar" : "Abrir", alerta: d.sem_texto > 0 };
  }
  if (k === "perfis") {
    const d = r.perfis;
    if (!d.total) return { linhas: ["Nenhum arquivo de perfil baixado"], acao: "Abrir" };
    const falta = Math.max(0, d.total - d.lidos);
    return { linhas: [`${numInicio(d.total)} arquivo(s) de perfil`, falta ? `${numInicio(falta)} ainda não lido(s)` : "Todos lidos"],
             acao: "Abrir" };
  }
  if (k === "mapa") {
    const d = r.mapa;
    if (!d.cadastro) return { linhas: ["Cadastro da ANP não baixado", "Sem ele, o mapa fica vazio"], acao: "Baixar o cadastro",
                              ir: "cadastro", alerta: true };
    return { linhas: [`${numInicio(d.cadastro)} poços no cadastro da ANP`, `${numInicio(d.com_topos)} com topos de formação (AGP)`],
             acao: "Ver no mapa" };
  }
  if (k === "secao") {
    const d = r.secao;
    if (!d.ultima) return { linhas: ["Nenhuma seção montada"], acao: "Montar" };
    return { linhas: [`Última: ${dataCurta(d.ultima.quando)}, ${d.ultima.pocos} poço(s)`, `${d.n} seção(ões) no projeto`],
             acao: "Abrir" };
  }
  const d = r.bloco;
  if (!d.ultimo) return { linhas: ["Nenhum modelo montado"], acao: "Montar" };
  return { linhas: [`Último: ${dataCurta(d.ultimo.quando)}, ${d.ultimo.pocos} poço(s)`, `${d.n} modelo(s) no projeto`],
           acao: "Abrir" };
}

function desenharModulos(r) {
  const grade = limpar($("ini-modulos"));
  for (const [k, num, nome] of MODULOS) {
    const e = estadoModulo(k, r);
    const c = el("div", "mod");
    c.dataset.modulo = k;
    const topo = el("div", "mod-topo");
    const ic = el("span", "mod-ic");
    ic.innerHTML = svgIcone(ICONES_MODULO[k]);
    topo.append(ic, el("span", "mod-num", num), el("strong", "", nome));
    const ul = el("ul", "mod-linhas");
    e.linhas.forEach((t, i) => ul.appendChild(el("li", i === 1 && e.alerta ? "alerta" : "", t)));
    const b = el("button", "btn secundario pequeno", e.acao);
    b.type = "button";
    b.onclick = () => trocarAba(e.ir || k);
    c.append(topo, ul, b);
    grade.appendChild(c);
  }
  const extras = limpar($("ini-extras"));
  for (const [k, nome, linha] of EXTRAS) {
    const b = el("button", "mod-extra");
    b.type = "button";
    b.append(el("strong", "", nome), el("span", "", linha));
    b.onclick = () => trocarAba(k);
    extras.appendChild(b);
  }
}

// ---------------------------------------------------------------- projetos
let projetosConhecidos = [];

async function carregarProjetos() {
  const r = await chamar(null, "projetos");
  if (!r.ok) return;
  projetosConhecidos = r.projetos;
  const aberto = r.projetos.find((p) => p.aberto);
  if (aberto) {
    $("ini-nome").textContent = aberto.nome;
    $("ini-rotulo").textContent = aberto.bacias.length ? `Projeto · ${aberto.bacias.join(", ")}` : "Projeto";
    mostrarProjetoNoTopo(aberto.pasta, aberto.nome);
  }
  const grade = limpar($("ini-projetos"));
  for (const p of r.projetos) grade.appendChild(cartaoProjeto(p));
  const novo = el("button", "proj proj-novo");
  novo.type = "button";
  novo.id = "ini-novo";
  novo.append(el("span", "proj-mais", "+"), el("strong", "", "Novo projeto"),
              el("span", "ajuda", "Uma pasta separada, com as suas bacias, arquivos e modelos."));
  novo.onclick = novoProjeto;
  grade.appendChild(novo);
}

// Minimapa: os poços do projeto (amostra) num retângulo, sem fundo: dá a forma da área de trabalho.
function miniMapa(pontos) {
  if (!pontos || !pontos.length) return '<svg viewBox="0 0 160 76" aria-hidden="true"></svg>';
  const xs = pontos.map((p) => p[0]), ys = pontos.map((p) => p[1]);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const kx = Math.cos(((y0 + y1) / 2) * Math.PI / 180);          // graus de longitude encolhem com a latitude
  let w = Math.max((x1 - x0) * kx, 0.02), h = Math.max(y1 - y0, 0.02);
  const esc = Math.min(144 / w, 64 / h);
  const ox = 8 + (144 - w * esc) / 2, oy = 6 + (64 - h * esc) / 2;
  const pts = pontos.map(([x, y]) =>
    `<circle cx="${(ox + (x - x0) * kx * esc).toFixed(1)}" cy="${(oy + (y1 - y) * esc).toFixed(1)}" r="1.8"/>`).join("");
  return `<svg viewBox="0 0 160 76" aria-hidden="true"><g class="mm-pocos">${pts}</g></svg>`;
}

function cartaoProjeto(p) {
  const c = el("div", "proj" + (p.aberto ? " aberto" : "") + (p.existe ? "" : " sumido"));
  c.dataset.pasta = p.pasta;
  const mapa = el("div", "proj-mapa");
  mapa.innerHTML = miniMapa(p.pontos);
  if (p.aberto) mapa.appendChild(el("span", "proj-selo", "aberto"));
  const corpo = el("div", "proj-corpo");
  const nome = el("div", "proj-nome");
  nome.append(el("strong", "", p.nome));
  const ren = el("button", "link proj-renomear", "renomear");
  ren.type = "button";
  ren.title = "Mudar o nome do projeto (a pasta continua a mesma)";
  ren.onclick = (ev) => { ev.stopPropagation(); renomearProjeto(p); };
  nome.appendChild(ren);
  const bacias = el("div", "proj-bacias");
  for (const b of p.bacias.slice(0, 4)) bacias.appendChild(el("span", "proj-chip", b));
  if (!p.bacias.length) bacias.appendChild(el("span", "ajuda", "sem bacia ainda"));
  const nums = el("dl", "proj-n");
  for (const [v, rot] of [[p.pocos, "poços"], [p.arquivos, "arquivos"], [p.documentos, "documentos"], [p.perfis, "perfis"]]) {
    nums.append(el("dt", "", numInicio(v)), el("dd", "", rot));
  }
  corpo.append(nome, bacias, nums);
  if (!p.existe) corpo.appendChild(el("p", "ajuda", "Pasta não encontrada: foi movida ou apagada?"));
  c.append(mapa, corpo);
  c.title = p.pasta;
  if (!p.aberto && p.existe) {
    c.classList.add("clicavel");
    c.tabIndex = 0;
    c.setAttribute("role", "button");
    c.onclick = () => trocarProjeto(p);
    c.onkeydown = (ev) => { if (ev.key === "Enter") trocarProjeto(p); };
  }
  return c;
}

async function trocarProjeto(p) {
  if (!projetoAberto) {
    inicioAbertura();
    const r = await chamar(null, "projeto_abrir", p.pasta);
    fimAbertura();
    if (r.ok) { liberarProjeto(r); status(`Projeto aberto: ${p.nome}.`, "ok"); }
    return;
  }
  const corpo = el("div");
  corpo.append(el("p", "", `O SIAPP fecha e abre de novo, já em “${p.nome}”. Downloads e leituras em andamento precisam terminar antes.`));
  abrirDialogo(`Abrir ${p.nome}?`, corpo, [
    botaoDialogo("Cancelar", "btn secundario", fecharDialogo),
    botaoDialogo("Abrir este projeto", "btn", async (ev) => {
      const r = await chamar(ev.currentTarget, "projeto_abrir", p.pasta);
      if (r.ok) { fecharDialogo(); status(`Abrindo ${p.nome}…`, "trab"); }
    }),
  ]);
}

function novoProjeto() {
  const f = el("form", "form-projeto");
  const rotNome = el("label", "", "Nome do projeto");
  const nome = el("input");
  nome.id = "np-nome";
  nome.maxLength = 60;
  nome.placeholder = "ex.: Guamaré — modelo 3D";
  rotNome.appendChild(nome);
  const caixa = el("fieldset", "np-bacias");
  caixa.appendChild(el("legend", "", "Bacias (pode mudar depois)"));
  for (const o of $("sel-bacia").options) {
    const r = el("label", "opcao");
    const c = el("input");
    c.type = "checkbox";
    c.value = o.value;
    r.append(c, el("span", "", o.value));
    caixa.appendChild(r);
  }
  f.append(rotNome, caixa, el("p", "ajuda", "Fica numa pasta própria, em projetos\\ ao lado do SIAPP: arquivos, banco e modelos separados dos outros projetos."));
  const criar = async (ev) => {
    if (ev) ev.preventDefault();
    const bacias = [...caixa.querySelectorAll("input:checked")].map((c) => c.value);
    const r = await chamar($("dlg-pe").querySelector(".btn:not(.secundario)"), "projeto_criar", nome.value, bacias);
    if (!r.ok) return;
    fecharDialogo();
    await carregarProjetos();
    const p = projetosConhecidos.find((x) => x.pasta === r.pasta);
    status(`Projeto “${r.nome}” criado.`, "ok");
    if (p) trocarProjeto(p);
  };
  f.onsubmit = criar;
  abrirDialogo("Novo projeto", f, [botaoDialogo("Cancelar", "btn secundario", fecharDialogo),
                                   botaoDialogo("Criar", "btn", criar)]);
  nome.focus();
}

function renomearProjeto(p) {
  const f = el("form");
  const inp = el("input");
  inp.id = "rp-nome";
  inp.value = p.nome;
  inp.maxLength = 60;
  f.appendChild(inp);
  const salvar = async (ev) => {
    if (ev) ev.preventDefault();
    const r = await chamar(null, "projeto_renomear", p.pasta, inp.value);
    if (!r.ok) return;
    fecharDialogo();
    carregarProjetos();
  };
  f.onsubmit = salvar;
  abrirDialogo("Renomear o projeto", f, [botaoDialogo("Cancelar", "btn secundario", fecharDialogo),
                                         botaoDialogo("Salvar", "btn", salvar)]);
  inp.select();
}

function ligarInicio() {}
