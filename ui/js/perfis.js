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
  if (!projetoAberto) { $("pf-resumo").textContent = "Abra o projeto primeiro (aba Início)."; return; }
  const r = await chamar(null, "perfis");
  if (!r.ok) return;
  const ul = limpar($("lista-perfis"));
  $("pf-resumo").textContent = r.perfis.length
    ? `${r.perfis.length} arquivo(s) de perfil baixado(s).`
    : "Nenhum DLIS, LIS ou LAS baixado ainda. Baixe na aba Catálogo (pasta de perfis do poço).";
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
  pf.familias = r.familias || pf.familias;
  pf.fatos = r.fatos || [];
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
  $("pf-aviso").hidden = !r.aviso;
  $("pf-aviso").textContent = r.aviso || "";
  const principal = r.inventario.quadros.find((q) => q.curvas.some((x) => x.familia === "GR")) || r.inventario.quadros[0];
  $("pf-passo").value = principal && principal.passo_m ? String(principal.passo_m).replace(".", ",") : "";
  desenharListaCurvas();
  desenharFatosPerfil();
  atualizarGrafico();
  status(`${r.inventario.arquivo}: ${pf.selecao.length} curva(s) na visão padrão.`, "ok");
}

function desenharListaCurvas() {
  const box = limpar($("pf-curvas"));
  const marcadas = new Set(pf.selecao.map((s) => s.quadro + "|" + s.mnemonico));
  for (const q of pf.inv.quadros) {
    const reconhecidas = q.curvas.filter((c) => c.familia).length;
    const det = el("details", "pf-quadro");
    det.open = q.curvas.some((c) => marcadas.has(q.nome + "|" + c.mnemonico));
    const sum = el("summary");
    sum.append(el("strong", "mono", q.nome),
      el("span", "ajuda", ` ${q.curvas.length} curvas · passo ${numero(q.passo_m, 4)} m${reconhecidas ? ` · ${reconhecidas} reconhecida(s)` : ""}`));
    det.appendChild(sum);
    const ul = el("ul", "pf-lista-curvas");
    for (const c of q.curvas) {
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
  $("pf-n-sel").textContent = pf.selecao.length;
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
  pf.dados = r.curvas;
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
  for (const t of trilhas) {
    const div = el("div", "pf-trilha");
    const cab = el("div", "pf-cab-trilha");
    for (const c of t.curvas) {
      const e = escalaDe(c);
      c._e = e;
      const linha = el("div", "pf-legenda");
      linha.style.color = e.cor;
      linha.style.borderBottom = `2px ${e.tracejado ? "dashed" : "solid"} ${e.cor}`;
      linha.append(el("span", "", numero(e.min, 2)), el("strong", "", `${c.mnemonico} (${c.unidade || "—"})`), el("span", "", numero(e.max, 2)));
      cab.appendChild(linha);
    }
    div.appendChild(cab);
    const cv = document.createElement("canvas");
    div.appendChild(cv);
    box.appendChild(div);
    telas.push([cv, t]);
  }
  const dpr = window.devicePixelRatio || 1;
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
    if (!t) continue;
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
  }
  ligarInteracao(box, yDe);
}

function desenharFatosNaTrilha(g, w, yDe) {
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
    cv.onmousedown = (ev) => { arraste = { y0: ev.offsetY }; };
    cv.onmouseup = (ev) => {
      if (arraste && Math.abs(ev.offsetY - arraste.y0) > 6) {
        const a = profDe(Math.min(arraste.y0, ev.offsetY)), b = profDe(Math.max(arraste.y0, ev.offsetY));
        $("pf-int-topo").value = numero(a, 2);
        $("pf-int-base").value = numero(b, 2);
        $("pf-int-nome").focus();
        status(`Intervalo ${numero(a, 2)}–${numero(b, 2)} m marcado: dê um nome e salve.`, "ok");
      }
      arraste = null;
    };
    cv.onmouseleave = () => { leitura.hidden = true; };
    cv.onmousemove = (ev) => {
      const prof = profDe(ev.offsetY);
      const partes = [`${numero(prof, 2)} m`];
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
    if (r.ok) { pf.fatos = pf.fatos.filter((x) => x.id !== f.id); desenharFatosPerfil(); desenharTrilhas(); }
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
  status(`${TIPOS_FATO[r.fato.tipo]} “${r.fato.nome}” salvo no poço ${r.fato.poco_id}.`, "ok");
}

async function exportarCurvas(formato, botao) {
  const r = await chamar(botao, "exportar_perfil", pf.rel, pf.selecao, formato, $("pf-passo").value.trim());
  if (!r.ok) return;
  $("pf-exportado").textContent = `${r.arquivo}: ${r.curvas} curva(s), ${numero(r.amostras, 0)} profundidades, passo ${numero(r.passo_m, 4)} m.`;
  status("Curvas exportadas.", "ok");
}

function ligarPerfis() {
  $("pf-padrao").onclick = async () => {
    const r = await chamar(null, "curvas_perfil", pf.rel);
    if (r.ok && r.inventario) { pf.selecao = r.padrao.slice(); desenharListaCurvas(); atualizarGrafico(); }
  };
  $("pf-limpar").onclick = () => { pf.selecao = []; desenharListaCurvas(); atualizarGrafico(); };
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
