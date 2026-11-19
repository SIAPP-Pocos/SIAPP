// SIAPP — visor ampliado: página em tela cheia, com zoom e arraste.
// Serve a qualquer PDF, TIF ou imagem baixada, processada ou não. A página vem
// em faixas, pedidas ao motor só quando aparecem na tela: um perfil escaneado
// em TIF pode ter dezenas de metros de papel.
"use strict";

const vs = {
  rel: null, pagina: 1, n_paginas: 1,
  largura: 0, altura: 0, altura_faixa: 0, faixas: 0,   // em pixels renderizados
  zoom: 1, pedido: 0, obs: null, arraste: null,
};
const ZOOM_MAX = 3;

async function abrirVisor(rel, pagina = 1) {
  const meu = ++vs.pedido;
  $("visor").hidden = false;
  $("v-num").textContent = "carregando…";
  const r = await chamar(null, "visor_pagina", rel, pagina);
  if (meu !== vs.pedido) return;
  if (!r.ok) { fecharVisor(); return; }
  Object.assign(vs, { rel: r.rel, pagina: r.pagina, n_paginas: r.n_paginas, largura: r.largura,
                      altura: r.altura, altura_faixa: r.altura_faixa, faixas: r.faixas });
  $("v-nome").textContent = r.nome;
  $("v-nome").title = r.rel;
  $("v-num").textContent = `${r.pagina} / ${r.n_paginas}`;
  $("v-ant").disabled = r.pagina <= 1;
  $("v-prox").disabled = r.pagina >= r.n_paginas;
  montarFaixas(meu);
  definirZoom(zoomLargura());
  $("v-area").scrollTop = 0;
  $("v-area").scrollLeft = 0;
  $("v-area").focus();
}

// ← → no visor (1.2): trocam a página. Com a página ampliada além da largura, as setas continuam rolando
// para os lados (devolve false e a tecla segue o caminho normal).
function paginaVisor(passo) {
  const area = $("v-area");
  if (area.scrollWidth > area.clientWidth + 1) return false;
  const nova = vs.pagina + passo;
  if (nova >= 1 && nova <= vs.n_paginas) abrirVisor(vs.rel, nova);
  return true;
}

function fecharVisor() {
  vs.pedido++;
  if (vs.obs) vs.obs.disconnect();
  vs.obs = null;
  limpar($("v-folha"));
  $("visor").hidden = true;
}

function visorAberto() { return !$("visor").hidden; }

// Cada faixa reserva o espaço certo (aspect-ratio) antes da imagem chegar:
// a barra de rolagem já mostra o comprimento real da página.
function montarFaixas(meu) {
  const folha = limpar($("v-folha"));
  if (vs.obs) vs.obs.disconnect();
  vs.obs = new IntersectionObserver((entradas) => {
    for (const e of entradas) if (e.isIntersecting) carregarFaixa(e.target, meu);
  }, { root: $("v-area"), rootMargin: "1200px 0px" });
  for (let i = 0; i < vs.faixas; i++) {
    const h = Math.min(vs.altura_faixa, vs.altura - i * vs.altura_faixa);
    const f = el("div", "v-faixa");
    f.dataset.i = i;
    f.style.aspectRatio = `${vs.largura} / ${h}`;
    folha.appendChild(f);
    vs.obs.observe(f);
  }
}

async function carregarFaixa(div, meu) {
  if (div.dataset.estado) return;
  div.dataset.estado = "pedido";
  vs.obs && vs.obs.unobserve(div);
  const r = await chamar(null, "visor_faixa", vs.rel, vs.pagina, Number(div.dataset.i));
  if (meu !== vs.pedido) return;
  if (!r.ok) { div.dataset.estado = ""; return; }
  const img = el("img");
  img.alt = `Faixa ${r.indice + 1} de ${vs.faixas}`;
  img.draggable = false;
  img.src = r.imagem;
  div.appendChild(img);
  div.dataset.estado = "ok";
}

// ------------------------------------------------------------------- zoom
// zoom 1 = um pixel renderizado por pixel de tela ("1:1").
function zoomLargura() {
  const area = $("v-area");
  return Math.min(ZOOM_MAX, Math.max(0.02, (area.clientWidth - 32) / (vs.largura || 1)));
}

// Mantém parado o ponto da imagem que está sob (cx, cy) — o cursor, no zoom pela roda.
function definirZoom(z, cx, cy) {
  const area = $("v-area"), folha = $("v-folha");
  z = Math.min(ZOOM_MAX, Math.max(Math.min(0.05, zoomLargura()), z));
  if (cx === undefined) { cx = area.clientWidth / 2; cy = area.clientHeight / 2; }
  const antigo = vs.zoom;
  const px = (area.scrollLeft + cx - folha.offsetLeft) / antigo;
  const py = (area.scrollTop + cy - folha.offsetTop) / antigo;
  vs.zoom = z;
  folha.style.width = `${Math.round(vs.largura * z)}px`;
  area.scrollLeft = px * z + folha.offsetLeft - cx;
  area.scrollTop = py * z + folha.offsetTop - cy;
  $("v-zoom").textContent = `${Math.round(z * 100)}%`;
}

function ligarVisor() {
  const area = $("v-area");
  area.tabIndex = -1;
  ligar("v-fechar", "onclick", fecharVisor);
  ligar("v-ant", "onclick", () => abrirVisor(vs.rel, vs.pagina - 1));
  ligar("v-prox", "onclick", () => abrirVisor(vs.rel, vs.pagina + 1));
  ligar("v-mais", "onclick", () => definirZoom(vs.zoom * 1.25));
  ligar("v-menos", "onclick", () => definirZoom(vs.zoom / 1.25));
  ligar("v-largura", "onclick", () => definirZoom(zoomLargura()));
  ligar("v-real", "onclick", () => definirZoom(1));

  area.addEventListener("wheel", (ev) => {
    if (!ev.ctrlKey) return;              // roda sem Ctrl: rolagem normal
    ev.preventDefault();
    const r = area.getBoundingClientRect();
    definirZoom(vs.zoom * Math.exp(-ev.deltaY * 0.0015), ev.clientX - r.left, ev.clientY - r.top);
  }, { passive: false });

  area.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    vs.arraste = { x: ev.clientX, y: ev.clientY, l: area.scrollLeft, t: area.scrollTop };
    area.setPointerCapture(ev.pointerId);
    area.classList.add("arrastando");
  });
  area.addEventListener("pointermove", (ev) => {
    if (!vs.arraste) return;
    area.scrollLeft = vs.arraste.l - (ev.clientX - vs.arraste.x);
    area.scrollTop = vs.arraste.t - (ev.clientY - vs.arraste.y);
  });
  const soltar = () => { vs.arraste = null; area.classList.remove("arrastando"); };
  area.addEventListener("pointerup", soltar);
  area.addEventListener("pointercancel", soltar);

  document.addEventListener("keydown", (ev) => {
    if (!visorAberto()) return;
    if (ev.key === "+" || ev.key === "=") definirZoom(vs.zoom * 1.25);
    else if (ev.key === "-") definirZoom(vs.zoom / 1.25);
    else if (ev.key === "PageDown" && ev.ctrlKey && vs.pagina < vs.n_paginas) abrirVisor(vs.rel, vs.pagina + 1);
    else if (ev.key === "PageUp" && ev.ctrlKey && vs.pagina > 1) abrirVisor(vs.rel, vs.pagina - 1);
  });
}
