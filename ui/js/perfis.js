// SIAPP — aba Perfis: inventário de DLIS/LIS/LAS, gráfico em trilhas, intervalo-alvo e exportação.
"use strict";

const pf = {
  rel: null, poco: "", inv: null, familias: {}, fatos: [],
  selecao: [],              // [{quadro, mnemonico, familia, unidade}]
  topo: null, base: null,   // janela visível (m)
  limites: [0, 0],          // intervalo total do arquivo
  dados: [],                // última resposta do motor
};

// ------------------------------------------------------------------ lista
async function carregarPerfis() {
  if (!projetoAberto) { $("pf-resumo").textContent = "Abra o projeto primeiro (aba Projeto)."; return; }
  const r = await chamar(null, "perfis");
  if (!r.ok) return;
  const ul = limpar($("lista-perfis"));
  $("pf-resumo").textContent = r.perfis.length
    ? `${r.perfis.length} arquivo(s) de perfil baixado(s).`
    : "Nenhum DLIS, LIS ou LAS baixado ainda. Baixe na aba Dados › Catálogo do REATE (pasta de perfis do poço).";
  for (const p of r.perfis) {
    const b = el("button");
    b.dataset.rel = p.rel;
    if (pf.rel === p.rel) b.classList.add("ativo");
    const info = el("span", "d-info");
    info.append(el("span", "", p.poco || "—"), el("span", "", tamanho(p.bytes)));
    if (p.formato && extensao(p.nome) !== "." + p.formato) {
      const s = el("span", "selo conv", `conteúdo ${p.formato.toUpperCase()}`);
      s.title = `O nome termina em ${extensao(p.nome)}, mas o conteúdo do arquivo é ${p.formato.toUpperCase()}.`;
      info.appendChild(s);
    }
    const sc = seloCorrida(p.corrida);
    if (sc) info.appendChild(sc);
    info.append(
      el("span", "selo" + (p.inventariado ? " ok" : ""),
         p.inventariado ? `${p.n_curvas} curvas · ${numero(p.topo_m, 0)}–${numero(p.base_m, 0)} m` : "não lido"));
    b.append(el("span", "d-nome", p.nome), info);
    b.title = p.rel;
    b.onclick = () => abrirPerfil(p);
    const li = el("li");
    li.appendChild(b);
    ul.appendChild(li);
  }
}

async function abrirPerfil(p) {
  pf.rel = p.rel;
  document.querySelectorAll("#lista-perfis button").forEach((b) => b.classList.toggle("ativo", b.dataset.rel === p.rel));
  let r = await chamar(null, "curvas_perfil", p.rel);
  if (!r.ok) return;
  if (!r.inventario) {
    status(`Lendo ${p.nome}… arquivos grandes levam alguns segundos.`, "trab");
    const botao = document.querySelector(`#lista-perfis button[data-rel="${CSS.escape(p.rel)}"]`);
    r = await chamar(botao, "inventariar_perfil", p.rel);
    if (!r.ok) return;
    carregarPerfis();
  }
  mostrarPerfil(r);
}

function mostrarPerfil(r) {
  pf.poco = r.poco;
  pf.inv = r.inventario;
  pf.familias = { ...(r.familias || pf.familias), ...FAMILIAS_AV };
  pf.fatos = r.fatos || [];
  pf.toposAgp = r.topos_agp || [];
  pf.form = r.formularios || { topos: [], canhoneados: [] };
  pf.litoAgp = r.litologia_agp || [];
  pf.litoFonte = "AGP";
  // sem litologia no AGP: a descrição de calha do PAG (geólogo de poço) faz a trilha
  if (!pf.litoAgp.length && (pf.form.litologia_calha || []).length) { pf.litoAgp = pf.form.litologia_calha; pf.litoFonte = "calha"; }
  pf.selecao = r.padrao.slice();
  pf.limites = [r.inventario.topo_m, r.inventario.base_m];
  pf.topo = pf.limites[0];
  pf.base = pf.limites[1];
  $("pf-vazio").hidden = true;
  $("pf-painel").hidden = false;
  $("pf-curvas-box").hidden = false;
  const c = r.inventario.cabecalho || {};
  $("pf-titulo").textContent = `${r.poco || c.poco || "—"} · ${r.inventario.arquivo}`;
  $("pf-sub").textContent = [c.empresa, c.campo, c.produtor && `perfilagem: ${c.produtor}`,
    // o campo UWI às vezes traz o nome do poço ("5PX  0011  RN"), não o nº de cadastro
    c.cadastro && (/^\d{6,}$/.test(c.cadastro.trim()) ? `cadastro ANP ${c.cadastro}` : `UWI ${c.cadastro}`),
    `${numero(pf.limites[0], 1)} a ${numero(pf.limites[1], 1)} m`,
    `${r.inventario.quadros.length} quadro(s)`].filter(Boolean).join(" · ");
  const co = r.corrida;
  $("pf-corrida").hidden = !(co && co.rotulo);
  $("pf-corrida").textContent = co && co.rotulo
    ? `Corrida: ${co.rotulo}` + (co.ferramentas && co.ferramentas.length ? ` · ferramentas: ${co.ferramentas.join(" ")}` : "") +
      (co.esquemas && co.esquemas.length ? ` (esquema ${co.esquemas.join(", ")})` : ` (pelo ${co.fonte})`)
    : "";
  $("pf-aviso").hidden = !r.aviso;
  $("pf-aviso").textContent = r.aviso || "";
  const so = $("pf-objetivo"), atualO = so.value;
  limpar(so).appendChild(new Option("— escolha um objetivo —", ""));
  for (const [k, n] of Object.entries(r.objetivos || {})) so.appendChild(new Option(n, k));
  so.value = atualO && (r.objetivos || {})[atualO] ? atualO : "";
  $("pf-sugestao").hidden = true;
  $("pf-nota-agp").hidden = !(pf.toposAgp || []).length;
  if ((pf.toposAgp || []).length) notaFonteAgp($("pf-nota-agp").querySelector(".nota-agp-texto"));
  const principal = r.inventario.quadros.find((q) => q.curvas.some((x) => x.familia === "GR")) || r.inventario.quadros[0];
  $("pf-passo").value = principal && principal.passo_m ? String(principal.passo_m).replace(".", ",") : "";
  desenharListaCurvas();
  desenharFatosPerfil();
  carregarAvaliacao();
  atualizarGrafico();
  status(`${r.inventario.arquivo}: ${pf.selecao.length} curva(s) na visão padrão.`, "ok");
}

// busca por mnemônico, descrição, unidade ou família ("densidade" acha RHOB)
function curvaCasa(c, termo) {
  if (!termo) return true;
  const fam = c.familia && pf.familias[c.familia] ? pf.familias[c.familia].nome : "";
  return norm([c.mnemonico, c.descricao, c.unidade, c.familia, fam].filter(Boolean).join(" ")).includes(termo);
}

function desenharListaCurvas() {
  const box = limpar($("pf-curvas"));
  const marcadas = new Set(pf.selecao.map((s) => s.quadro + "|" + s.mnemonico));
  const termo = norm($("pf-busca").value.trim());
  let achadas = 0;
  for (const q of pf.inv.quadros) {
    const reconhecidas = q.curvas.filter((c) => c.familia).length;
    const visiveis = q.curvas.filter((c) => curvaCasa(c, termo));
    achadas += visiveis.length;
    if (termo && !visiveis.length) continue;
    const det = el("details", "pf-quadro");
    det.open = termo ? true : q.curvas.some((c) => marcadas.has(q.nome + "|" + c.mnemonico));
    const sum = el("summary");
    sum.append(el("strong", "mono", q.nome),
      el("span", "ajuda", ` ${q.curvas.length} curvas · passo ${numero(q.passo_m, 4)} m${reconhecidas ? ` · ${reconhecidas} reconhecida(s)` : ""}`));
    det.appendChild(sum);
    const ul = el("ul", "pf-lista-curvas");
    for (const c of visiveis) {
      const li = el("li");
      const lab = el("label");
      const cb = el("input");
      cb.type = "checkbox";
      cb.disabled = c.dimensao !== 1 || !c.n_validas;
      cb.checked = marcadas.has(q.nome + "|" + c.mnemonico);
      cb.onchange = () => alternarCurva(q.nome, c, cb.checked);
      const nome = el("span", "mono", c.mnemonico);
      if (c.familia && pf.familias[c.familia]) nome.style.color = pf.familias[c.familia].cor;
      lab.append(cb, nome, el("span", "ajuda", [c.unidade, c.familia && pf.familias[c.familia] ? pf.familias[c.familia].nome : "", c.dimensao !== 1 ? `matriz ${c.dimensao}` : "", !c.n_validas ? "sem dados" : ""].filter(Boolean).join(" · ")));
      lab.title = [c.descricao, c.topo_m !== null ? `${numero(c.topo_m, 1)}–${numero(c.base_m, 1)} m` : ""].filter(Boolean).join("\n");
      li.appendChild(lab);
      ul.appendChild(li);
    }
    det.appendChild(ul);
    box.appendChild(det);
  }
  $("pf-busca-n").hidden = !termo;
  $("pf-busca-n").textContent = termo ? (achadas ? `${achadas} curva(s) para “${$("pf-busca").value.trim()}”.`
    : `Nenhuma curva com “${$("pf-busca").value.trim()}” neste arquivo.`) : "";
  $("pf-n-sel").textContent = pf.selecao.length;
}

async function sugerirCurvas() {
  const ob = $("pf-objetivo").value;
  if (!ob || !pf.rel) { $("pf-sugestao").hidden = true; return; }
  const r = await chamar($("pf-objetivo"), "sugerir_curvas", pf.rel, ob);
  if (!r.ok) return;
  const p = limpar($("pf-sugestao"));
  p.append(el("strong", "", `${r.nome}: `), document.createTextNode(r.porque + " "));
  if (r.curvas.length) {
    p.append(document.createTextNode("Marcadas: "), el("span", "mono", r.curvas.map((c) => c.mnemonico).join(", ")), document.createTextNode(". "));
  }
  if (r.faltam.length) p.append(el("em", "", `Este arquivo não tem: ${r.faltam.map((f) => f.nome).join(", ")}.`));
  p.hidden = false;
  if (!r.curvas.length) { status("Nenhuma curva deste objetivo no arquivo.", "erro"); return; }
  pf.selecao = r.curvas.slice();
  $("pf-busca").value = "";
  desenharListaCurvas();
  atualizarGrafico();
  status(`${r.curvas.length} curva(s) marcada(s) para: ${r.nome}.`, "ok");
}

function alternarCurva(quadro, c, marcar) {
  pf.selecao = pf.selecao.filter((s) => !(s.quadro === quadro && s.mnemonico === c.mnemonico));
  if (marcar) pf.selecao.push({ quadro, mnemonico: c.mnemonico, familia: c.familia, unidade: c.unidade });
  $("pf-n-sel").textContent = pf.selecao.length;
  atualizarGrafico();
}

// ----------------------------------------------------------------- gráfico
let pedidoGrafico = 0;
let esperaGrafico = null;
function atualizarGrafico(imediato = true) {
  clearTimeout(esperaGrafico);
  esperaGrafico = setTimeout(buscarGrafico, imediato ? 0 : 120);
}

async function buscarGrafico() {
  if (!pf.rel) return;
  $("pf-topo").value = numero(pf.topo, 1);
  $("pf-base").value = numero(pf.base, 1);
  const meu = ++pedidoGrafico;
  const r = await chamar(null, "grafico_perfil", pf.rel, pf.selecao, pf.topo, pf.base);
  if (!r.ok || meu !== pedidoGrafico) return;
  const calculadas = await curvasAvaliacaoGrafico();
  if (meu !== pedidoGrafico) return;
  pf.dados = r.curvas.concat(calculadas);
  desenharTrilhas();
}

function trilhasDe(curvas) {
  const grupos = new Map();
  for (const c of curvas) {
    const fam = pf.familias[c.familia] || {};
    const chave = fam.trilha ? "t" + fam.trilha : "c" + c.quadro + c.mnemonico;
    if (!grupos.has(chave)) grupos.set(chave, { ordem: fam.trilha || 9, curvas: [] });
    grupos.get(chave).curvas.push(c);
  }
  return [...grupos.values()].sort((a, b) => a.ordem - b.ordem);
}

function escalaDe(c) {
  const fam = pf.familias[c.familia] || {};
  let esc = fam.escala ? fam.escala.slice() : null;
  const vals = c.valores.filter((v) => v !== null);
  if (c.familia === "NPHI" && vals.length && vals.sort((a, b) => a - b)[Math.floor(vals.length / 2)] > 1.5) esc = [45, -15];
  if (!esc) {   // sem escala fixa: do 2º ao 98º percentil dos dados visíveis
    const v = c.valores.filter((x) => x !== null).sort((a, b) => a - b);
    esc = v.length ? [v[Math.floor(v.length * 0.02)], v[Math.ceil(v.length * 0.98) - 1]] : [0, 1];
    if (esc[0] === esc[1]) esc = [esc[0] - 1, esc[1] + 1];
  }
  return { min: esc[0], max: esc[1], log: Boolean(fam.log), cor: fam.cor || "#1c2227", tracejado: Boolean(fam.tracejado) };
}

function xDe(v, e, largura) {
  if (v === null) return null;
  let t;
  if (e.log) {
    if (v <= 0) return null;
    t = (Math.log10(v) - Math.log10(e.min)) / (Math.log10(e.max) - Math.log10(e.min));
  } else {
    t = (v - e.min) / (e.max - e.min);
  }
  return Math.max(-2, Math.min(largura + 2, t * largura));
}

function passoGrade(faixa) {
  const alvo = faixa / 8;
  const p = Math.pow(10, Math.floor(Math.log10(alvo)));
  return [1, 2, 5, 10].map((m) => m * p).find((x) => x >= alvo);
}

const ALTURA_TRILHAS = 560;

function desenharTrilhas() {
  const box = limpar($("pf-trilhas"));
  const trilhas = trilhasDe(pf.dados);
  if (!trilhas.length) { box.appendChild(el("p", "ajuda", "Marque curvas ao lado para ver o gráfico.")); return; }
  const faixa = pf.base - pf.topo;
  const yDe = (prof) => ((prof - pf.topo) / faixa) * ALTURA_TRILHAS;
  const grade = passoGrade(faixa);

  // eixo de profundidade
  const eixo = el("div", "pf-trilha pf-eixo");
  eixo.appendChild(el("div", "pf-cab-trilha", "Prof. (m)"));
  const ce = document.createElement("canvas");
  eixo.appendChild(ce);
  box.appendChild(eixo);
  const telas = [[ce, null]];
  // litologia descrita no AGP (amostras de calha): o gabarito para o GR
  let cvLito = null;
  if ((pf.litoAgp || []).length) {
    const dl = el("div", "pf-trilha pf-trilha-lito");
    const cabL = el("div", "pf-cab-trilha");
    cabL.appendChild(el("div", "pf-legenda", `Litol. (${pf.litoFonte})`));
    cabL.title = pf.litoFonte === "AGP" ? "Litologia descrita nas amostras de calha (AGP da ANP). Passe o mouse para ver a rocha."
      : "Litologia da descrição das amostras de calha (PAG, geólogo de poço): a rocha principal de cada amostra.";
    dl.appendChild(cabL);
    cvLito = document.createElement("canvas");
    dl.appendChild(cvLito);
    box.appendChild(dl);
  }
  for (const t of trilhas) {
    const div = el("div", "pf-trilha");
    if (t.curvas.every((c) => (pf.familias[c.familia] || {}).faixa !== undefined)) div.classList.add("pf-trilha-flags");
    const cab = el("div", "pf-cab-trilha");
    for (const c of t.curvas) {
      const e = escalaDe(c);
      c._e = e;
      const fam = pf.familias[c.familia] || {};
      if (fam.faixa !== undefined) {          // trilha de indicadores (reservatório, pay, QC)
        const linha = el("div", "pf-legenda");
        linha.style.color = e.cor;
        linha.style.borderBottom = `6px solid ${e.cor}`;
        linha.append(el("strong", "", fam.nome));
        cab.appendChild(linha);
        continue;
      }
      // nome em cima (quebra a linha em vez de cortar), escala embaixo
      const linha = el("div", "pf-legenda");
      linha.style.color = e.cor;
      linha.style.borderBottom = `2px ${e.tracejado ? "dashed" : "solid"} ${e.cor}`;
      linha.title = [`${c.mnemonico} (${c.unidade || "—"})`, (pf.familias[c.familia] || {}).nome,
                     `escala ${numero(e.min, 2)} a ${numero(e.max, 2)}${e.log ? " (log)" : ""}`].filter(Boolean).join(" · ");
      const esc = el("div", "pf-escala");
      esc.append(el("span", "", numero(e.min, 2)), el("span", "", numero(e.max, 2)));
      linha.append(el("strong", "", `${c.mnemonico} (${c.unidade || "—"})`), esc);
      cab.appendChild(linha);
    }
    div.appendChild(cab);
    const cv = document.createElement("canvas");
    div.appendChild(cv);
    box.appendChild(div);
    telas.push([cv, t]);
  }
  // cabeçalhos da mesma altura: senão as trilhas começam em alturas diferentes e a profundidade desalinha
  const cabs = [...box.querySelectorAll(".pf-cab-trilha")];
  const altura = Math.max(64, ...cabs.map((c) => c.scrollHeight));
  for (const c of cabs) c.style.height = altura + "px";
  const dpr = window.devicePixelRatio || 1;
  if (cvLito) desenharLitologia(cvLito, yDe, dpr);
  desenharLegendaLitologia();
  for (const [cv, t] of telas) {
    const w = cv.parentElement.clientWidth;
    cv.width = w * dpr; cv.height = ALTURA_TRILHAS * dpr;
    cv.style.width = w + "px"; cv.style.height = ALTURA_TRILHAS + "px";
    const g = cv.getContext("2d");
    g.scale(dpr, dpr);
    g.fillStyle = "#fff"; g.fillRect(0, 0, w, ALTURA_TRILHAS);
    // linhas de profundidade
    g.strokeStyle = "#e6e4dd"; g.fillStyle = "#5f6b73"; g.font = "11px Consolas, monospace"; g.lineWidth = 1;
    for (let p = Math.ceil(pf.topo / grade) * grade; p <= pf.base; p += grade) {
      const y = Math.round(yDe(p)) + 0.5;
      g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
      if (!t) g.fillText(numero(p, grade < 1 ? 1 : 0), 4, y - 2);
    }
    if (!t) {          // eixo: nome das unidades do AGP no topo de cada uma
      g.fillStyle = "#2f7d4f"; g.font = "600 10px Segoe UI, system-ui, sans-serif";
      for (const u of pf.toposAgp || []) {
        if (u.tip !== "L" || u.topo < pf.topo || u.topo > pf.base) continue;
        g.fillText(String(u.nome).slice(0, 10), 2, Math.round(yDe(u.topo)) + 10);
      }
      // sem AGP: os topos constatados do RFP (só os que têm nome) dão nome às unidades
      if (!(pf.toposAgp || []).some((u) => u.tip === "L")) {
        g.fillStyle = "#8a5a2b";
        for (const u of (pf.form && pf.form.topos) || []) {
          if (!u.com_nome || u.topo < pf.topo || u.topo > pf.base) continue;
          g.fillText(String(u.nome).replace(/^FM\.?\s*/i, "").slice(0, 10), 2, Math.round(yDe(u.topo)) + 10);
        }
      }
      continue;
    }
    // linhas verticais (décadas nas escalas logarítmicas)
    const e0 = t.curvas[0]._e;
    g.strokeStyle = "#efede7";
    if (e0.log) {
      for (let d = Math.ceil(Math.log10(e0.min)); d <= Math.log10(e0.max); d++) {
        const x = Math.round(xDe(Math.pow(10, d), e0, w)) + 0.5;
        g.beginPath(); g.moveTo(x, 0); g.lineTo(x, ALTURA_TRILHAS); g.stroke();
      }
    } else {
      for (let i = 1; i < 4; i++) { const x = Math.round((w * i) / 4) + 0.5; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, ALTURA_TRILHAS); g.stroke(); }
    }
    desenharFatosNaTrilha(g, w, yDe);
    for (const c of t.curvas) {
      const fam = pf.familias[c.familia] || {};
      if (fam.faixa !== undefined) {          // 1 = pinta a faixa da coluna
        const col = w / 3, x0 = fam.faixa * col;
        g.fillStyle = c._e.cor;
        for (let i = 0; i < c.prof.length - 1; i++) {
          if (c.valores[i] !== 1) continue;
          const y0 = yDe(c.prof[i]), y1 = yDe(c.prof[i + 1]);
          g.fillRect(x0 + 1, y0, col - 2, Math.max(1, y1 - y0));
        }
        continue;
      }
      g.strokeStyle = c._e.cor; g.lineWidth = 1.2;
      g.setLineDash(c._e.tracejado ? [5, 3] : []);
      g.beginPath();
      let aberto = false;
      for (let i = 0; i < c.prof.length; i++) {
        const x = xDe(c.valores[i], c._e, w);
        if (x === null) { aberto = false; continue; }
        const y = yDe(c.prof[i]);
        if (aberto) g.lineTo(x, y); else { g.moveTo(x, y); aberto = true; }
      }
      g.stroke();
      g.setLineDash([]);
    }
    desenharReferenciaGr(g, w, yDe, t);
  }
  ligarInteracao(box, yDe);
}

const CORES_ROCHA = [
  [/ARENITO|AREIA|CONGLOMERADO/, "#f2d16b", "Arenito, conglomerado"],
  [/FOLHELHO|ARGILITO|SILTITO|MARGA/, "#8fa58a", "Folhelho, argilito, siltito"],
  [/CALC|DOLOMIT|COQUINA/, "#8fb8d9", "Calcário, dolomito"], [/EVAPORIT|HALITA|ANIDRITA|SAL/, "#d9a3c9", "Evaporito"],
  [/GRANITO|GNAISSE|EMBASAMENTO|BASALTO|DIABASIO/, "#c98f7a", "Embasamento, ígnea"], [/CARVAO|LINHITO/, "#3d3d3d", "Carvão"],
];
const ROCHA_OUTRA = ["#d5d3cc", "Outra / não classificada"];

function classeRocha(rocha) {
  const r = (rocha || "").toUpperCase();
  for (const [re, cor, nome] of CORES_ROCHA) if (re.test(r)) return [cor, nome];
  return ROCHA_OUTRA;
}

function corRocha(rocha) { return classeRocha(rocha)[0]; }

// Legenda da trilha de litologia: só as classes que aparecem no trecho visível, com as rochas do AGP de cada uma.
function desenharLegendaLitologia() {
  const box = $("pf-lito-legenda");
  if (!box) return;
  const vis = (pf.litoAgp || []).filter((c) => c.topo != null && c.base != null && c.base >= pf.topo && c.topo <= pf.base);
  box.hidden = !vis.length;
  limpar(box);
  if (!vis.length) return;
  box.appendChild(el("strong", "", `Litologia (${pf.litoFonte || "AGP"}):`));
  const classes = new Map();
  for (const c of vis) {
    const [cor, nome] = classeRocha(c.rocha);
    if (!classes.has(nome)) classes.set(nome, { cor, rochas: new Set() });
    classes.get(nome).rochas.add(String(c.rocha || "?").trim());
  }
  const ordem = [...CORES_ROCHA.map((x) => x[2]), ROCHA_OUTRA[1]];
  for (const nome of ordem) {
    const k = classes.get(nome);
    if (!k) continue;
    const s = el("span");
    const i = el("i");
    i.style.background = k.cor;
    s.append(i, document.createTextNode(nome));
    s.title = (pf.litoFonte === "calha" ? "Na calha: " : "No AGP: ") + [...k.rochas].slice(0, 12).join(", ");
    box.appendChild(s);
  }
}

function desenharLitologia(cv, yDe, dpr) {
  const w = cv.parentElement.clientWidth;
  cv.width = w * dpr; cv.height = ALTURA_TRILHAS * dpr;
  cv.style.width = w + "px"; cv.style.height = ALTURA_TRILHAS + "px";
  const g = cv.getContext("2d");
  g.scale(dpr, dpr);
  g.fillStyle = "#fff"; g.fillRect(0, 0, w, ALTURA_TRILHAS);
  for (const c of pf.litoAgp) {
    if (c.topo == null || c.base == null || c.base < pf.topo || c.topo > pf.base) continue;
    const y0 = Math.max(0, yDe(c.topo)), y1 = Math.min(ALTURA_TRILHAS, yDe(c.base));
    g.fillStyle = corRocha(c.rocha);
    g.fillRect(0, y0, w, Math.max(1, y1 - y0));
  }
  cv.onmousemove = (ev) => {
    const prof = pf.topo + (ev.offsetY / ALTURA_TRILHAS) * (pf.base - pf.topo);
    const c = pf.litoAgp.find((x) => x.topo <= prof && prof <= x.base);
    cv.title = c ? `${numero(c.topo, 1)}–${numero(c.base, 1)} m: ${c.rocha} ${c.descricao || ""}${c.formacao ? ` (${c.formacao})` : ""}` : "";
  };
}

// GR limpo e GR da argila da avaliação mostrada: linhas tracejadas na trilha do GR, na janela usada.
function desenharReferenciaGr(g, w, yDe, t) {
  const r = pf.grRef;
  const mostrar = $("av-mostrar") ? $("av-mostrar").checked : true;
  const c = t.curvas.find((x) => x.familia === "GR");
  if (!r || !mostrar || !c) return;
  const y0 = Math.max(0, r.topo != null ? yDe(r.topo) : 0);
  const y1 = Math.min(ALTURA_TRILHAS, r.base != null ? yDe(r.base) : ALTURA_TRILHAS);
  if (y1 <= y0) return;
  g.save();
  g.lineWidth = 1.4;
  g.setLineDash([6, 4]);
  g.font = "600 10px Segoe UI, system-ui, sans-serif";
  for (const [v, cor, rot] of [[r.limpo, "#b8860b", "limpo"], [r.argila, "#4f6b4a", "argila"]]) {
    const x = xDe(v, c._e, w);
    if (x === null) continue;
    g.strokeStyle = cor; g.fillStyle = cor;
    g.beginPath(); g.moveTo(x + 0.5, y0); g.lineTo(x + 0.5, y1); g.stroke();
    g.fillText(`${rot} ${numero(v, 0)}`, Math.min(Math.max(2, x + 3), w - 52), y0 + 12);
  }
  g.restore();
}

function desenharFatosNaTrilha(g, w, yDe) {
  // topos do AGP (ANP): verde tracejado; marcos mais claros
  for (const u of pf.toposAgp || []) {
    if (u.topo < pf.topo || u.topo > pf.base) continue;
    g.strokeStyle = u.tip === "L" ? "#2f7d4f" : "#9bbfa7";
    g.setLineDash([2, 3]); g.lineWidth = 1;
    const y = Math.round(yDe(u.topo)) + 0.5;
    g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
    g.setLineDash([]);
  }
  // topos constatados do RFP: marrom tracejado; canhoneados (RFCP): faixa vermelha na borda direita
  const form = pf.form || { topos: [], canhoneados: [] };
  for (const u of form.topos) {
    if (u.topo < pf.topo || u.topo > pf.base) continue;
    g.strokeStyle = "#b08050"; g.setLineDash([1, 3]); g.lineWidth = 1;
    const y = Math.round(yDe(u.topo)) + 0.5;
    g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
    g.setLineDash([]);
  }
  for (const c of form.canhoneados) {
    if (c.base < pf.topo || c.topo > pf.base) continue;
    g.fillStyle = "rgba(192, 57, 43, .55)";
    g.fillRect(w - 5, yDe(c.topo), 5, Math.max(2, yDe(c.base) - yDe(c.topo)));
  }
  for (const f of pf.fatos) {
    if (f.prof_topo === null) continue;
    if (f.tipo === "intervalo_alvo" && f.prof_base !== null) {
      g.fillStyle = "rgba(255, 210, 60, .22)";
      g.fillRect(0, yDe(f.prof_topo), w, yDe(f.prof_base) - yDe(f.prof_topo));
    } else {
      g.strokeStyle = f.tipo === "contato_fluido" ? "#2f6fa3" : "#5b2f8f";
      g.setLineDash([4, 3]); g.lineWidth = 1;
      const y = yDe(f.prof_topo);
      g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
      g.setLineDash([]);
    }
  }
}

// rolar, aproximar, ler valores e marcar intervalo com o mouse
function ligarInteracao(box, yDe) {
  const faixa = pf.base - pf.topo;
  const profDe = (y) => pf.topo + (y / ALTURA_TRILHAS) * faixa;
  let leitura = $("pf-leitura");
  if (!leitura) { leitura = el("div", "pf-leitura"); leitura.id = "pf-leitura"; document.body.appendChild(leitura); }
  let arraste = null;
  // faixa marcada enquanto arrasta (todas as trilhas), com as profundidades
  const yNa = (ev) => {
    const cv0 = box.querySelector("canvas");
    return Math.max(0, Math.min(ALTURA_TRILHAS, ev.clientY - cv0.getBoundingClientRect().top));
  };
  const faixaSel = () => {
    let f = $("pf-faixa-sel");
    if (!f) {
      f = el("div", "pf-faixa-sel");
      f.id = "pf-faixa-sel";
      f.appendChild(el("span", "pf-faixa-rotulo"));
    }
    if (f.parentElement !== box) box.appendChild(f);
    return f;
  };
  const mostrarFaixa = (y0, y1) => {
    const f = faixaSel(), cv0 = box.querySelector("canvas");
    const topoCv = cv0.getBoundingClientRect().top - box.getBoundingClientRect().top;
    const a = Math.min(y0, y1), b = Math.max(y0, y1);
    f.style.top = topoCv + a + "px";
    f.style.height = Math.max(1, b - a) + "px";
    f.style.width = box.scrollWidth + "px";
    f.hidden = false;
    f.firstChild.textContent = `${numero(profDe(a), 2)} – ${numero(profDe(b), 2)} m (${numero(profDe(b) - profDe(a), 2)} m)`;
  };
  const esconderFaixa = () => { const f = $("pf-faixa-sel"); if (f) f.hidden = true; };
  box.onmouseleave = () => { if (arraste) { arraste = null; esconderFaixa(); } };
  for (const cv of box.querySelectorAll("canvas")) {
    cv.onwheel = (ev) => {
      ev.preventDefault();
      const yRel = ev.offsetY / ALTURA_TRILHAS;
      if (ev.ctrlKey || ev.metaKey) {
        const fator = ev.deltaY > 0 ? 1.25 : 0.8;
        const centro = profDe(ev.offsetY);
        definirJanela(centro - (centro - pf.topo) * fator, centro + (pf.base - centro) * fator);
      } else {
        const d = faixa * 0.15 * Math.sign(ev.deltaY);
        definirJanela(pf.topo + d, pf.base + d, yRel);
      }
    };
    cv.onmousedown = (ev) => { ev.preventDefault(); arraste = { y0: yNa(ev) }; };
    cv.onmouseup = (ev) => {
      const y = yNa(ev);
      esconderFaixa();
      if (arraste && Math.abs(y - arraste.y0) > 6) {
        const a = profDe(Math.min(arraste.y0, y)), b = profDe(Math.max(arraste.y0, y));
        $("pf-int-topo").value = numero(a, 2);
        $("pf-int-base").value = numero(b, 2);
        $("pf-int-nome").focus();
        status(`Intervalo ${numero(a, 2)}–${numero(b, 2)} m marcado: dê um nome e salve.`, "ok");
      }
      arraste = null;
    };
    cv.onmouseleave = () => { leitura.hidden = true; };
    cv.onmousemove = (ev) => {
      if (arraste && Math.abs(yNa(ev) - arraste.y0) > 2) mostrarFaixa(arraste.y0, yNa(ev));
      const prof = profDe(yNa(ev));
      const partes = [`${numero(prof, 2)} m`];
      const twt = twtNaProf(prof);
      if (twt !== null) partes[0] += ` · TWT ${numero(twt, 1)} ms`;
      // perto de um topo do AGP: nome, fonte e qualidade
      const tol = (4 / ALTURA_TRILHAS) * faixa;
      const topoAgp = (pf.toposAgp || []).find((u) => Math.abs(u.topo - prof) <= tol);
      if (topoAgp) {
        partes.push(`topo AGP: ${topoAgp.nome}` + [topoAgp.fonte, topoAgp.qualidade].filter(Boolean).map((x) => ` · ${x}`).join(""));
      }
      for (const c of pf.dados) {
        let i = 0, melhor = Infinity, v = null;
        for (; i < c.prof.length; i++) { const d = Math.abs(c.prof[i] - prof); if (d < melhor) { melhor = d; v = c.valores[i]; } }
        if (v !== null) partes.push(`${c.mnemonico} ${numero(v, 3)}`);
      }
      leitura.textContent = partes.join(" · ");
      leitura.hidden = false;
      leitura.style.left = ev.clientX + 14 + "px";
      leitura.style.top = ev.clientY + 12 + "px";
    };
  }
}

// TWT (ms) pelo checkshot do poço, por interpolação entre os níveis (fora deles: nada).
function twtNaProf(prof) {
  const cs = (pf.form && pf.form.checkshot) || [];
  for (let k = 1; k < cs.length; k++) {
    const a = cs[k - 1], b = cs[k];
    if (prof >= a.md && prof <= b.md) return b.md === a.md ? a.twt : a.twt + (b.twt - a.twt) * (prof - a.md) / (b.md - a.md);
  }
  return null;
}

function definirJanela(topo, base) {
  const [lo, hi] = pf.limites;
  let faixa = Math.max(1, Math.min(base - topo, hi - lo));
  topo = Math.max(lo, Math.min(topo, hi - faixa));
  pf.topo = topo;
  pf.base = topo + faixa;
  atualizarGrafico(false);
}

function lerNumero(id) {
  const v = $(id).value.trim().replace(/\./g, "").replace(",", ".");
  return v === "" ? null : Number(v);
}

// ------------------------------------------------------ fatos e exportação
function desenharFatosPerfil() {
  const box = limpar($("pf-fatos"));
  if (!pf.fatos.length) { box.appendChild(el("p", "ajuda", "Nenhum intervalo ou topo marcado neste poço.")); return; }
  box.appendChild(tabelaFatos(pf.fatos, async (f) => {
    const r = await chamar(null, "remover_fato", f.id);
    if (r.ok) { pf.fatos = pf.fatos.filter((x) => x.id !== f.id); desenharFatosPerfil(); desenharTrilhas(); atualizarIntervalosAv(); }
  }));
}

async function salvarIntervalo(ev) {
  ev.preventDefault();
  const dados = { tipo: $("pf-int-tipo").value, nome: $("pf-int-nome").value,
                  prof_topo: $("pf-int-topo").value.replace(/\./g, ""),
                  prof_base: $("pf-int-base").value.replace(/\./g, "") };
  const r = await chamar(null, "salvar_intervalo", pf.rel, dados);
  if (!r.ok) return;
  pf.fatos.push(r.fato);
  pf.fatos.sort((a, b) => (a.prof_topo ?? 1e12) - (b.prof_topo ?? 1e12));
  $("pf-int-nome").value = $("pf-int-topo").value = $("pf-int-base").value = "";
  desenharFatosPerfil();
  desenharTrilhas();
  atualizarIntervalosAv();
  status(`${TIPOS_FATO[r.fato.tipo]} “${r.fato.nome}” salvo no poço ${r.fato.poco_id}.`, "ok");
}

async function exportarCurvas(formato, botao) {
  const r = await chamar(botao, "exportar_perfil", pf.rel, pf.selecao, formato, $("pf-passo").value.trim());
  if (!r.ok) return;
  $("pf-exportado").textContent = `${r.arquivo}: ${r.curvas} curva(s), ${numero(r.amostras, 0)} profundidades, passo ${numero(r.passo_m, 4)} m.`;
  status("Curvas exportadas.", "ok");
}

function ligarPerfis() {
  ligarAvaliacao();
  $("pf-padrao").onclick = async () => {
    const r = await chamar(null, "curvas_perfil", pf.rel);
    if (r.ok && r.inventario) { pf.selecao = r.padrao.slice(); desenharListaCurvas(); atualizarGrafico(); }
  };
  $("pf-limpar").onclick = () => { pf.selecao = []; desenharListaCurvas(); atualizarGrafico(); };
  $("pf-busca").oninput = () => pf.inv && desenharListaCurvas();
  $("pf-objetivo").onchange = sugerirCurvas;
  $("pf-aplicar").onclick = () => {
    const a = lerNumero("pf-topo"), b = lerNumero("pf-base");
    if (a !== null && b !== null && b > a) definirJanela(a, b);
  };
  $("pf-tudo").onclick = () => definirJanela(pf.limites[0], pf.limites[1]);
  $("pf-mais").onclick = () => { const c = (pf.topo + pf.base) / 2, f = (pf.base - pf.topo) / 4; definirJanela(c - f, c + f); };
  $("pf-menos").onclick = () => { const c = (pf.topo + pf.base) / 2, f = pf.base - pf.topo; definirJanela(c - f, c + f); };
  $("pf-form-int").onsubmit = salvarIntervalo;
  $("pf-las").onclick = () => exportarCurvas("las", $("pf-las"));
  $("pf-csv").onclick = () => exportarCurvas("csv", $("pf-csv"));
  window.addEventListener("resize", () => { if (!$("vista-perfis").hidden && pf.dados.length) desenharTrilhas(); });
}
