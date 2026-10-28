// SIAPP — aba Mapa (e o cadastro da ANP, em Dados): poços no mapa, filtros e ficha do poço.
"use strict";

let mapa = null;            // L.Map
let camadaPocos = null;     // L.LayerGroup com os marcadores
let pocosMapa = [];         // [{id, lat, lon, ...}] da última consulta
let fichaAberta = null;

const CORES = { cad: "#9aa3a8", reate: "#0e5a62", baixado: "#c26a1b" };
// legenda clicável (Bloco 6 do teste da 0.29): categorias escondidas em cada modo de cor
const legenda = { ocultas: { pasta: new Set(), acervo: new Set() }, soFatos: false };
const destaques = new Map();         // id → {cor, lat, lon, campo}
let camadaDestaques = null;

function criarMapa() {
  if (mapa || typeof L === "undefined") return;
  mapa = L.map("mapa", { preferCanvas: true, zoomControl: true }).setView([-8.5, -38.5], 6);
  const ruas = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "© colaboradores do OpenStreetMap" });
  const satelite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 18, attribution: "Imagens © Esri, Maxar, Earthstar Geographics" });
  ruas.addTo(mapa);
  mapa.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  L.control.layers({ "Mapa": ruas, "Satélite": satelite }, null, { position: "topright" }).addTo(mapa);
  L.control.scale({ imperial: false }).addTo(mapa);
  camadaPocos = L.layerGroup().addTo(mapa);
  camadaDestaques = L.layerGroup().addTo(mapa);
  mapa.on("click", cliqueLinha);
  mapa.on("mousemove", moverLinha);
  mapa.on("dblclick", (ev) => { if (linhaMapa.desenhando) { L.DomEvent.stop(ev); concluirLinha(); } });
}

async function carregarMapa() {
  if (!projetoAberto) {
    $("cad-info").textContent = "Abra o projeto primeiro (aba Projeto).";
    return;
  }
  criarMapa();
  setTimeout(() => mapa && mapa.invalidateSize(), 50);   // a aba estava oculta
  const r = await chamar(null, "cadastro_info");
  if (!r.ok) return;
  desenharCadastroInfo(r);
  preencherBacias(r.bacias);
  preencherBaciasLevantamento([...$("sel-bacia").options].map((o) => o.value));
  carregarLevantamento();
  if (r.cadastro) await consultarMapa(true);
}

function desenharCadastroInfo(r) {
  const c = r.cadastro;
  $("cad-info").textContent = c
    ? `${numero(c.pocos, 0)} poços, importado em ${dataCurta(c.importado_em)}. ` +
      "A ANP atualiza a tabela todo mês."
    : "Ainda não importado. Baixe a Tabela de Poços dos dados abertos da ANP (~12 MB).";
  $("mapa-vazio").hidden = Boolean(c);
  $("btn-cadastro").textContent = c ? "Atualizar da ANP" : "Baixar da ANP";
}

function preencherBacias(bacias) {
  const sel = $("f-bacia");
  const atual = sel.value;
  limpar(sel);
  sel.appendChild(new Option("todas", ""));
  for (const b of bacias) {
    const txt = `${b.bacia} (${numero(b.pocos, 0)}${b.no_reate ? ` · ${numero(b.no_reate, 0)} no REATE` : ""})`;
    sel.appendChild(new Option(txt, b.bacia));
  }
  // a bacia já escolhida; senão a do catálogo; senão a que tem mais poços no REATE
  const candidatas = [atual, baciaConectada, baciaAnterior].filter((b) => b && bacias.some((x) => x.bacia === b));
  const melhor = [...bacias].sort((a, b) => (b.no_reate - a.no_reate) || (b.pocos - a.pocos))[0];
  sel.value = candidatas[0] || (melhor ? melhor.bacia : "");
}

function filtrosMapa() {
  return {
    bacia: $("f-bacia").value, texto: $("f-texto").value.trim(), terra_mar: $("f-terra").value,
    tipo: $("f-tipo").value ? Number($("f-tipo").value) : null,
    so_reate: $("f-reate").checked, so_baixados: $("f-baixados").checked,
    acervo: $("f-acervo").value, familia: $("f-familia").value,
  };
}

let pedidoMapa = 0;
async function consultarMapa(enquadrar = false) {
  const meu = ++pedidoMapa;
  const r = await chamar(null, "pocos_mapa", filtrosMapa());
  if (!r.ok || meu !== pedidoMapa) return;
  pocosMapa = r.linhas.map((l) => Object.fromEntries(r.colunas.map((c, i) => [c, l[i]])));
  desenharMarcadores(enquadrar);
  const nReate = pocosMapa.filter((p) => p.reate).length;
  const nBaix = pocosMapa.filter((p) => p.baixados).length;
  const nDig = pocosMapa.filter((p) => p.acervo === "digital").length;
  $("mapa-resumo").textContent = `${numero(pocosMapa.length, 0)} poço(s) com coordenadas` +
    (nReate ? ` · ${numero(nReate, 0)} com pasta no REATE` : "") +
    (nBaix ? ` · ${numero(nBaix, 0)} com arquivos baixados` : "") +
    (nDig ? ` · ${numero(nDig, 0)} com perfil digital` : "") +
    (r.truncado ? " · lista cortada: refine os filtros" : "");
  desenharListaMapa();
}

function corPorAcervo() { return $("f-cor").value === "acervo"; }

function corPoco(p) {
  if (corPorAcervo()) return CORES_ACERVO[p.acervo] || CORES.cad;
  return p.baixados ? CORES.baixado : p.reate ? CORES.reate : CORES.cad;
}

function destaquePoco(p) { return corPorAcervo() ? Boolean(p.acervo) : Boolean(p.reate || p.baixados); }

function trocarCorMapa() {
  $("legenda-pasta").hidden = corPorAcervo();
  $("legenda-acervo").hidden = !corPorAcervo();
  if (pocosMapa.length) { desenharMarcadores(false); desenharListaMapa(); }
}

// ------------------------------------------------ legenda clicável
function categoriaPoco(p) {
  if (corPorAcervo()) return p.acervo || "nao";
  return p.baixados ? "baixado" : p.reate ? "reate" : "cad";
}

function pocoVisivel(p) {
  const ocultas = legenda.ocultas[corPorAcervo() ? "acervo" : "pasta"];
  return !ocultas.has(categoriaPoco(p)) && (!legenda.soFatos || p.fatos);
}

function desenharLegendaMapa() {
  const modo = corPorAcervo() ? "acervo" : "pasta";
  const cont = {};
  for (const p of pocosMapa) { const c = categoriaPoco(p); cont[c] = (cont[c] || 0) + 1; }
  const nFatos = pocosMapa.filter((p) => p.fatos).length;
  for (const b of document.querySelectorAll(`#legenda-${modo} [data-cat]`)) {
    const cat = b.dataset.cat;
    const n = cat === "fatos" ? nFatos : cont[cat] || 0;
    b.querySelector(".n").textContent = pocosMapa.length ? `(${numero(n, 0)})` : "";
    const desligado = cat === "fatos" ? false : legenda.ocultas[modo].has(cat);
    b.classList.toggle("desligado", desligado);
    b.classList.toggle("ligado", cat === "fatos" && legenda.soFatos);
    b.setAttribute("aria-pressed", String(cat === "fatos" ? legenda.soFatos : !desligado));
  }
}

function alternarCategoria(modo, cat, so) {
  if (cat === "fatos") { legenda.soFatos = !legenda.soFatos; }
  else if (so) {
    const todas = [...document.querySelectorAll(`#legenda-${modo} [data-cat]`)].map((b) => b.dataset.cat).filter((c) => c !== "fatos");
    const ja = legenda.ocultas[modo].size === todas.length - 1 && !legenda.ocultas[modo].has(cat);
    legenda.ocultas[modo] = ja ? new Set() : new Set(todas.filter((c) => c !== cat));   // de novo: mostra todas
  } else if (legenda.ocultas[modo].has(cat)) legenda.ocultas[modo].delete(cat);
  else legenda.ocultas[modo].add(cat);
  desenharMarcadores(false);
  desenharListaMapa();
}

function ligarLegendaMapa() {
  for (const modo of ["pasta", "acervo"]) {
    for (const b of document.querySelectorAll(`#legenda-${modo} [data-cat]`)) {
      let espera = null;
      b.onclick = () => {          // um clique: liga/desliga; dois cliques: só esta (o 1º clique espera o 2º)
        clearTimeout(espera);
        espera = setTimeout(() => alternarCategoria(modo, b.dataset.cat, false), 220);
      };
      b.ondblclick = () => { clearTimeout(espera); alternarCategoria(modo, b.dataset.cat, b.dataset.cat !== "fatos"); };
    }
  }
}

function desenharMarcadores(enquadrar) {
  camadaPocos.clearLayers();
  desenharLegendaMapa();
  const pontos = [];
  for (const p of pocosMapa) {
    if (!pocoVisivel(p)) continue;
    const destaque = destaquePoco(p);
    const m = L.circleMarker([p.lat, p.lon], {
      radius: destaque ? 5 : 3, weight: p.fatos ? 2.5 : 0.6, color: p.fatos ? "#5b2f8f" : "#ffffff",
      fillColor: corPoco(p), fillOpacity: destaque ? 0.95 : 0.6,
    });
    m.bindTooltip(`${p.id}${p.campo ? " · " + p.campo : ""}`, { direction: "top" });
    m.on("click", () => abrirFicha(p.id));
    m.addTo(camadaPocos);
    pontos.push([p.lat, p.lon]);
  }
  if (enquadrar && pontos.length) mapa.fitBounds(L.latLngBounds(pontos).pad(0.05), { maxZoom: 12 });
  const ocultos = pocosMapa.length - pontos.length;
  $("mapa-resumo").dataset.ocultos = ocultos;
  const dl = limpar($("dq-lista-pocos"));
  for (const p of pocosMapa.slice(0, 3000)) dl.appendChild(new Option(p.campo || "", p.id));
}

// ------------------------------------------------ destacar poços
function desenharDestaques() {
  if (!camadaDestaques) return;
  camadaDestaques.clearLayers();
  for (const [id, d] of destaques) {
    const m = L.circleMarker([d.lat, d.lon], { radius: 8, weight: 2.5, color: "#1c2227", fillColor: d.cor, fillOpacity: 1 });
    m.bindTooltip(id, { permanent: true, direction: "right", className: "rot-destaque", offset: [8, 0] });
    m.on("click", () => abrirFicha(id));
    m.addTo(camadaDestaques);
  }
  const chips = limpar($("dq-chips"));
  for (const [id, d] of destaques) {
    const c = el("span", "chip-dic");
    const bola = el("i", "bola");
    bola.style.background = d.cor;
    const x = el("button", "x", "×");
    x.type = "button";
    x.title = "Tirar o destaque";
    x.onclick = () => { destaques.delete(id); desenharDestaques(); };
    const nome = el("button", "link mono", id);
    nome.type = "button";
    nome.onclick = () => { mapa.setView([d.lat, d.lon], Math.max(mapa.getZoom(), 12)); abrirFicha(id); };
    c.append(bola, nome, x);
    chips.appendChild(c);
  }
  $("dq-acoes").hidden = !destaques.size;
}

async function destacarPocos(nomes, cor) {
  const ids = (nomes || []).map((x) => String(x).trim()).filter(Boolean);
  if (!ids.length) return;
  const r = await chamar(null, "pocos_posicoes", ids);
  if (!r.ok) return;
  for (const p of r.pocos) destaques.set(p.id, { cor, lat: p.lat, lon: p.lon, campo: p.campo });
  desenharDestaques();
  if (r.faltam.length) status(`Sem coordenadas no cadastro: ${r.faltam.join(", ")}.`, "erro");
  else status(`${r.pocos.length} poço(s) destacado(s).`, "ok");
  return r.pocos;
}

function enquadrarDestaques() {
  const pts = [...destaques.values()].map((d) => [d.lat, d.lon]);
  if (pts.length === 1) mapa.setView(pts[0], Math.max(mapa.getZoom(), 12));
  else if (pts.length) mapa.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 13 });
}

// ------------------------------------------------ seção por uma linha desenhada no mapa
const linhaMapa = { desenhando: false, pontos: [], camada: null, provisoria: null, resultado: null };

function iniciarLinhaMapa() {
  criarMapa();
  if (!linhaMapa.camada) linhaMapa.camada = L.layerGroup().addTo(mapa);
  linhaMapa.camada.clearLayers();
  linhaMapa.pontos = [];
  linhaMapa.resultado = null;
  linhaMapa.desenhando = true;
  mapa.doubleClickZoom.disable();
  $("mapa").classList.add("desenhando");
  $("mapa-linha").hidden = false;
  $("ml-instrucao").hidden = false;
  $("ml-resumo").textContent = "";
  limpar($("ml-lista"));
  $("ml-abrir").disabled = true;
  status("Clique no mapa para marcar o ponto A da linha.");
}

function fecharLinhaMapa() {
  linhaMapa.desenhando = false;
  if (mapa) mapa.doubleClickZoom.enable();
  $("mapa").classList.remove("desenhando");
  if (linhaMapa.camada) linhaMapa.camada.clearLayers();
  linhaMapa.provisoria = null;
  $("mapa-linha").hidden = true;
}

function desenharTracado() {
  linhaMapa.camada.clearLayers();
  const pts = linhaMapa.pontos;
  if (pts.length > 1) L.polyline(pts, { color: "#1c2227", weight: 2.5 }).addTo(linhaMapa.camada);
  pts.forEach((q, i) => {
    const rot = i === 0 ? "A" : i === pts.length - 1 && !linhaMapa.desenhando ? "B" : String(i);
    L.marker(q, { icon: L.divIcon({ className: "ml-ponto", html: `<span>${rot}</span>`, iconSize: [20, 20] }) })
      .addTo(linhaMapa.camada);
  });
}

function cliqueLinha(ev) {
  if (!linhaMapa.desenhando) return;
  linhaMapa.pontos.push([ev.latlng.lat, ev.latlng.lng]);
  desenharTracado();
  status(linhaMapa.pontos.length === 1 ? "Agora o ponto B (ou pontos intermediários). Dois cliques terminam."
    : `${linhaMapa.pontos.length} pontos. Dois cliques ou "Concluir" terminam.`);
}

function moverLinha(ev) {
  if (!linhaMapa.desenhando || !linhaMapa.pontos.length) return;
  const ult = linhaMapa.pontos[linhaMapa.pontos.length - 1];
  if (linhaMapa.provisoria) linhaMapa.provisoria.setLatLngs([ult, ev.latlng]);
  else linhaMapa.provisoria = L.polyline([ult, ev.latlng], { color: "#1c2227", weight: 1.5, dashArray: "4 4" }).addTo(linhaMapa.camada);
}

// faixa de `km` em volta da linha (retângulos nos trechos e círculos nas juntas)
function desenharFaixa(km) {
  const pts = linhaMapa.pontos, estilo = { color: "#e0218a", weight: 0, fillColor: "#e0218a", fillOpacity: 0.1 };
  for (let k = 0; k < pts.length - 1; k++) {
    const [a, b] = [pts[k], pts[k + 1]];
    const lat0 = (a[0] + b[0]) / 2, kx = 111.32 * Math.cos(lat0 * Math.PI / 180), ky = 110.57;
    const dx = (b[1] - a[1]) * kx, dy = (b[0] - a[0]) * ky, comp = Math.hypot(dx, dy) || 1;
    const nx = -dy / comp * km, ny = dx / comp * km;          // normal em km
    const desl = (q, s) => [q[0] + s * ny / ky, q[1] + s * nx / kx];
    L.polygon([desl(a, 1), desl(b, 1), desl(b, -1), desl(a, -1)], estilo).addTo(linhaMapa.camada);
  }
  for (const q of pts) L.circle(q, { radius: km * 1000, ...estilo }).addTo(linhaMapa.camada);
}

async function concluirLinha() {
  if (linhaMapa.pontos.length < 2) { status("Marque ao menos os pontos A e B.", "erro"); return; }
  linhaMapa.desenhando = false;
  mapa.doubleClickZoom.enable();
  $("mapa").classList.remove("desenhando");
  linhaMapa.provisoria = null;
  // dois cliques no fim marcam o mesmo ponto duas vezes: fica um
  const pts = linhaMapa.pontos;
  while (pts.length > 2 && Math.abs(pts[pts.length - 1][0] - pts[pts.length - 2][0]) < 1e-7 &&
         Math.abs(pts[pts.length - 1][1] - pts[pts.length - 2][1]) < 1e-7) pts.pop();
  await buscarPocosLinha();
}

async function buscarPocosLinha() {
  if (linhaMapa.pontos.length < 2) return;
  const km = Number($("ml-largura").value.replace(",", ".")) || 2;
  const r = await chamar($("ml-concluir"), "secao_linha", linhaMapa.pontos, km);
  if (!r.ok) return;
  linhaMapa.resultado = r;
  desenharTracado();
  desenharFaixa(km);
  const escolhidos = new Set(r.pocos.map((p) => p.id));
  for (const p of r.todos) {
    if (escolhidos.has(p.id)) continue;
    L.circleMarker([p.lat, p.lon], { radius: 4, weight: 1.5, color: "#e0218a", fillOpacity: 0 }).addTo(linhaMapa.camada);
  }
  r.pocos.forEach((p, i) => {
    L.marker([p.lat, p.lon], { icon: L.divIcon({ className: "ml-poco", html: `<span>${i + 1}</span>`, iconSize: [18, 18] }) })
      .bindTooltip(`${i + 1}. ${p.id} · ${numero(p.t_km, 1)} km da ponta A`).addTo(linhaMapa.camada);
  });
  $("ml-instrucao").hidden = true;
  $("ml-resumo").textContent = r.encontrados
    ? `${r.encontrados} poço(s) com topos no AGP a até ${numero(km, 1)} km da linha de ${numero(r.comprimento_km, 1)} km` +
      (r.encontrados > r.pocos.length ? `; ${r.pocos.length} escolhidos, espaçados por igual (a seção aceita até 20).` : ".")
    : `Nenhum poço com topos no AGP a até ${numero(km, 1)} km da linha. Aumente a distância ou leia os AGPs (Dados › Levantamento).`;
  const ol = limpar($("ml-lista"));
  for (const p of r.pocos) {
    ol.appendChild(el("li", "", `${p.id} · ${numero(p.t_km, 1)} km da ponta A · a ${numero(p.dist_linha_km, 1)} km da linha`));
  }
  $("ml-abrir").disabled = r.pocos.length < 2;
  status(r.pocos.length >= 2 ? `${r.pocos.length} poço(s) na linha. "Abrir na Seção" monta a seção.` : "Poucos poços na linha.",
         r.pocos.length >= 2 ? "ok" : "erro");
}

function desenharListaMapa() {
  const ul = limpar($("lista-mapa"));
  const visiveis = pocosMapa.filter(pocoVisivel);
  const ordem = visiveis.sort((a, b) => (b.baixados - a.baixados) || (b.reate - a.reate) ||
                                        a.id.localeCompare(b.id));
  if (visiveis.length < pocosMapa.length) {
    ul.appendChild(el("li", "vazio-lista", `${numero(pocosMapa.length - visiveis.length, 0)} poço(s) escondido(s) pela legenda ` +
                                           "do mapa — clique nela para mostrar."));
  }
  for (const p of ordem.slice(0, 300)) {
    const b = el("button");
    b.append(el("i", "bola", ""), el("span", "mono", p.id),
             el("span", "ajuda", [p.campo, corPorAcervo() ? NOMES_SITUACAO[p.acervo] : p.situacao]
                                   .filter(Boolean).join(" · ")));
    b.firstChild.style.background = corPoco(p);
    b.onclick = () => { abrirFicha(p.id); mapa.setView([p.lat, p.lon], Math.max(mapa.getZoom(), 12)); };
    const li = el("li");
    li.appendChild(b);
    ul.appendChild(li);
  }
  if (ordem.length > 300) ul.appendChild(el("li", "vazio-lista", `… e mais ${numero(ordem.length - 300, 0)}. Refine os filtros.`));
}

// -------------------------------------------------------------- ficha
function linhaFicha(tabela, rotulo, valor) {
  if (valor === null || valor === undefined || valor === "") return;
  const tr = el("tr");
  tr.append(el("th", "", rotulo), el("td", "", String(valor)));
  tabela.appendChild(tr);
}

function profundidade(m) { return m === null || m === undefined ? "" : `${numero(m, 1)} m`; }

async function abrirFicha(id) {
  fichaAberta = id;
  $("ficha").hidden = false;
  $("fi-titulo").textContent = id;
  $("fi-sub").textContent = "carregando…";
  const corpo = limpar($("fi-corpo"));
  const r = await chamar(null, "ficha_poco", id);
  if (!r.ok || fichaAberta !== id) return;
  const p = r.poco;
  $("fi-sub").textContent = [p.bacia, p.campo, p.operador].filter(Boolean).join(" · ") ||
                            (r.no_cadastro ? "" : "fora do cadastro da ANP");
  setTimeout(() => mapa && mapa.invalidateSize(), 50);

  if (r.no_cadastro) {
    corpo.appendChild(el("h3", "", "Cadastro ANP"));
    const t = el("table", "tabela ficha");
    linhaFicha(t, "Categoria", [p.tipo, p.categoria].filter(Boolean).join(" · "));
    linhaFicha(t, "Reclassificação", p.reclassificacao);
    linhaFicha(t, "Situação", p.situacao);
    linhaFicha(t, "Ambiente", p.terra_mar === "T" ? "terra" : p.terra_mar === "M" ? "mar" : p.terra_mar);
    linhaFicha(t, "Perfuração", [p.inicio, p.termino].filter(Boolean).map(dataCurta).join(" → "));
    linhaFicha(t, "Prof. sondador", profundidade(p.prof_sondador));
    linhaFicha(t, "Prof. vertical", profundidade(p.prof_vertical));
    linhaFicha(t, "Mesa rotativa", p.mesa_rotativa !== null ? `${numero(p.mesa_rotativa, 2)} m (acima do nível do mar)` : "");
    linhaFicha(t, "Cota", profundidade(p.cota_altimetrica));
    linhaFicha(t, "Direção", p.direcao);
    linhaFicha(t, "Formação final", p.formacao_final);
    linhaFicha(t, "Coordenadas", p.lat !== null ? `${numero(p.lat, 5)}, ${numero(p.lon, 5)} (${p.datum || "SIRGAS2000"})` : "");
    linhaFicha(t, "Nº de cadastro", p.cadastro);
    const flags = Object.entries(p.dados_anp || {})
      .filter(([k, v]) => v === "S" && /PERFI|CDPE|AGP|TESTE|TESTEMUNHO|AMOSTRA|SISMICA|DIRECION|GEOQUIM|CANHONEIO|PAG$|^PC$/.test(k))
      .map(([k]) => k.toLowerCase().replaceAll("_", " "));
    linhaFicha(t, "A ANP registra", flags.join(", "));
    corpo.appendChild(t);
  }

  const bd = el("button", "btn secundario pequeno", "Destacar no mapa");
  bd.onclick = () => destacarPocos([id], $("dq-cor").value);
  corpo.appendChild(bd);
  secaoProducaoFicha(corpo, r.producao, p.campo);

  corpo.appendChild(el("h3", "", "No portal REATE"));
  if (!r.reate.length) corpo.appendChild(el("p", "ajuda", "Nenhuma pasta encontrada nas categorias já listadas. Use “Catalogar a bacia conectada”."));
  for (const x of r.reate) {
    const linha = el("div", "linha ficha-reate");
    linha.append(el("span", "", `${x.bacia} · ${x.categoria}${x.parte ? " · " + x.parte : ""}`));
    // pasta num compartilhamento de outra bacia: pode ser real, mas vale conferir
    if (r.no_cadastro && r.poco.bacia && x.bacia !== r.poco.bacia)
      linha.append(el("span", "ajuda", ` (o cadastro da ANP põe o poço na bacia ${r.poco.bacia})`));
    const b = el("button", "btn secundario pequeno", "Ver arquivos");
    b.onclick = () => abrirPocoNoCatalogo(x);
    linha.appendChild(b);
    corpo.appendChild(linha);
  }

  corpo.appendChild(el("h3", "", `Arquivos baixados (${r.arquivos.length})`));
  if (!r.arquivos.length) corpo.appendChild(el("p", "ajuda", "Nenhum."));
  const ul = el("ul", "dic-lista");
  for (const a of r.arquivos) {
    const li = el("li");
    li.append(el("span", "", `${a.rel.split("/").slice(3).join("/")} · ${tamanho(a.bytes)}`), botaoAbrir(a.rel, a.tipo));
    ul.appendChild(li);
  }
  corpo.appendChild(ul);

  secaoAgpFicha(corpo, r.agp);
  secaoEsquemasFicha(corpo, r.esquemas, id);
  secaoAcervoFicha(corpo, r.acervo, (r.esquemas || {}).perfis);

  if (r.curvas.length) {
    corpo.appendChild(el("h3", "", "Curvas disponíveis"));
    const t = el("table", "tabela");
    for (const c of r.curvas) linhaFicha(t, c.familia, `${c.n} curva(s) · ${profundidade(c.topo)} a ${profundidade(c.base)}`);
    corpo.appendChild(t);
  }

  corpo.appendChild(el("h3", "", `Dados transcritos (${r.fatos.length})`));
  if (!r.fatos.length) corpo.appendChild(el("p", "ajuda", "Nenhum ainda. Transcreva na aba Documentos, a partir da página do documento."));
  else corpo.appendChild(tabelaFatos(r.fatos));

  if (r.apelidos.length) corpo.appendChild(el("p", "ajuda", "Também escrito como: " + r.apelidos.join(", ")));
}

// ------------------------------------------------ produção do poço (dados abertos da ANP)
const FLUIDOS_PROD = [
  ["oleo_m3", "Óleo", "m³", "#2f7d4f"], ["gas", "Gás", "mil m³", "#c0392b"], ["agua_m3", "Água", "m³", "#2a78d6"],
];

function valorFluido(m, k) {
  if (k === "gas") {
    const a = m.gas_assoc_mil_m3, b = m.gas_nassoc_mil_m3;
    return a == null && b == null ? null : (a || 0) + (b || 0);
  }
  return m[k];
}

// linha mensal pequena (papel: fundo branco), com o máximo e o período
function sparkProducao(meses, k, cor) {
  const w = 300, h = 46, vals = meses.map((m) => valorFluido(m, k));
  const max = Math.max(0, ...vals.filter((v) => v != null));
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("class", "spark");
  if (max <= 0) return svg;
  let d = "";
  vals.forEach((v, i) => {
    if (v == null) return;
    const x = meses.length > 1 ? (i / (meses.length - 1)) * (w - 2) + 1 : w / 2;
    const y = h - 2 - (v / max) * (h - 6);
    d += `${d ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", cor);
  path.setAttribute("stroke-width", "1.4");
  svg.appendChild(path);
  return svg;
}

function mesAno(p) { return p ? `${p.slice(5, 7)}/${p.slice(0, 4)}` : "—"; }

function secaoProducaoFicha(corpo, pr, campo) {
  corpo.appendChild(el("h3", "", "Produção (ANP)"));
  if (!pr || pr.situacao !== "ok") {
    const txt = !pr || pr.situacao === "sem_campo"
      ? "O cadastro da ANP não liga este poço a um campo de produção."
      : pr.situacao === "campo_sem_poco"
        ? `A produção do campo ${pr.campo} já foi baixada, mas este poço não aparece nela (não produziu no período baixado).`
        : `A produção do campo ${pr.campo} ainda não foi baixada.`;
    const p = el("p", "ajuda", txt + " ");
    if (pr && pr.campo) {
      const b = el("button", "link", pr.situacao === "campo_nao_baixado" ? "Baixar em Dados › Produção da ANP" : "Ver o campo em Dados › Produção");
      b.type = "button";
      b.onclick = () => irPara("producao", "abrirProducaoCampo", pr.campo);
      p.appendChild(b);
    }
    corpo.appendChild(p);
    return;
  }
  const a = pr.acumulado || {};
  const t = el("table", "tabela ficha");
  linhaFicha(t, "Período baixado", `${mesAno(pr.de)} a ${mesAno(pr.ate)} (${pr.n_meses} meses com registro)`);
  linhaFicha(t, "Produziu", pr.primeira_producao ? `de ${mesAno(pr.primeira_producao)} a ${mesAno(pr.ultima_producao)}` : "não (só injeção ou zeros)");
  linhaFicha(t, "Óleo acumulado", a.oleo_m3 != null ? `${numero(a.oleo_m3, 0)} m³` : "");
  linhaFicha(t, "Gás acumulado", a.gas_total_mil_m3 != null ? `${numero(a.gas_total_mil_m3, 1)} mil m³` : "");
  linhaFicha(t, "Água acumulada", a.agua_m3 != null ? `${numero(a.agua_m3, 0)} m³` : "");
  linhaFicha(t, "Condensado acumulado", a.condensado_m3 ? `${numero(a.condensado_m3, 0)} m³` : "");
  if (pr.injetor) {
    const inj = [["inj_agua_rec_m3", "água (reinjeção)", "m³"], ["inj_agua_desc_m3", "água (descarte)", "m³"],
                 ["inj_gas_mil_m3", "gás", "mil m³"], ["inj_co2_mil_m3", "CO₂", "mil m³"], ["inj_vapor_t", "vapor", "t"]]
      .filter(([k]) => a[k]).map(([k, n, u]) => `${n} ${numero(a[k], 0)} ${u}`);
    linhaFicha(t, "Injeção acumulada", inj.join(" · "));
  }
  const u = pr.ultimo_mes || {};
  linhaFicha(t, `Último mês (${mesAno(u.periodo)})`, FLUIDOS_PROD.map(([k, n, un]) => {
    const v = valorFluido(u, k);
    return v != null ? `${n.toLowerCase()} ${numero(v, k === "gas" ? 1 : 0)} ${un}` : "";
  }).filter(Boolean).join(" · "));
  if (pr.zonas && pr.zonas.length) linhaFicha(t, "Zonas", pr.zonas.map((z) => z.zona).join(", "));
  corpo.appendChild(t);
  const graf = el("div", "ficha-producao");
  for (const [k, n, un, cor] of FLUIDOS_PROD) {
    const vals = pr.meses.map((m) => valorFluido(m, k)).filter((v) => v != null);
    if (!vals.length || Math.max(...vals) <= 0) continue;
    const linha = el("div", "fp-linha");
    linha.append(el("span", "fp-nome", `${n} (${un}/mês)`), sparkProducao(pr.meses, k, cor),
                 el("span", "fp-max", `máx. ${numero(Math.max(...vals), k === "gas" ? 1 : 0)}`));
    graf.appendChild(linha);
  }
  if (graf.children.length) {
    graf.appendChild(el("p", "ajuda", `Mensal, de ${mesAno(pr.de)} a ${mesAno(pr.ate)}. Fonte: dados abertos da ANP (produção por poço).`));
    corpo.appendChild(graf);
  }
  const b = el("button", "link", `Ver o campo ${pr.campo} em Dados › Produção`);
  b.type = "button";
  b.onclick = () => irPara("producao", "abrirProducaoCampo", pr.campo);
  const pp = el("p", "ajuda");
  pp.appendChild(b);
  corpo.appendChild(pp);
}

function fecharFicha() {
  $("ficha").hidden = true;
  fichaAberta = null;
  setTimeout(() => mapa && mapa.invalidateSize(), 50);
}

// Leva o usuário à árvore de arquivos do poço (aba Dados › Catálogo do REATE).
function abrirPocoNoCatalogo(x) { irPara("catalogo", "mostrarPocoNoCatalogo", x); }

async function mostrarPocoNoCatalogo(x) {
  if ($("sel-bacia").value !== x.bacia || !document.querySelector("#lista-cat button")) {
    $("sel-bacia").value = x.bacia;
    await conectar();
  }
  const botaoCat = [...document.querySelectorAll("#lista-cat button")].find((b) => b.textContent === x.categoria);
  if (!botaoCat) { status(`Categoria ${x.categoria} não encontrada na bacia ${x.bacia}.`, "erro"); return; }
  if ($("titulo-pocos").textContent !== x.categoria || $("painel-pocos").hidden) await listarPocos(x.categoria, botaoCat);
  $("filtro").value = x.nome_pasta;
  desenharPocos();
  const botaoPoco = [...document.querySelectorAll("#grade-pocos button")].find((b) => b.textContent === x.nome_pasta);
  if (botaoPoco) botaoPoco.click();
}

async function baixarCadastro(botao, funcao) {
  const r = await chamar(botao, funcao);
  if (!r.ok || r.cancelado) return;
  status(`Cadastro importado: ${numero(r.resumo.pocos, 0)} poços, ${numero(r.resumo.com_coordenadas, 0)} com coordenadas.`, "ok");
  carregarMapa();
}

async function catalogarBacia() {
  const r = await chamar($("btn-catalogar"), "catalogar_bacia");
  if (!r.ok) return;
  status(`${r.bacia}: ${numero(r.pocos, 0)} pastas de poço registradas em ${r.categorias} categoria(s).`, "ok");
  const info = await chamar(null, "cadastro_info");
  if (info.ok) preencherBacias(info.bacias);
  consultarMapa();
}

function ligarMapa() {
  $("btn-cadastro").onclick = () => baixarCadastro($("btn-cadastro"), "atualizar_cadastro_anp");
  $("btn-cadastro-arq").onclick = () => baixarCadastro($("btn-cadastro-arq"), "importar_cadastro_arquivo");
  $("btn-catalogar").onclick = catalogarBacia;
  $("fi-fechar").onclick = fecharFicha;
  for (const id of ["f-bacia", "f-terra", "f-tipo", "f-reate", "f-baixados", "f-acervo", "f-familia"]) {
    $(id).onchange = () => consultarMapa(id === "f-bacia");
  }
  $("f-cor").onchange = trocarCorMapa;
  ligarLegendaMapa();
  $("dq-form").onsubmit = (ev) => {
    ev.preventDefault();
    destacarPocos($("dq-poco").value.split(/[,;\s]+/), $("dq-cor").value);
    $("dq-poco").value = "";
  };
  $("dq-enquadrar").onclick = enquadrarDestaques;
  $("dq-limpar").onclick = () => { destaques.clear(); desenharDestaques(); };
  $("btn-mapa-linha").onclick = iniciarLinhaMapa;
  $("ml-fechar").onclick = fecharLinhaMapa;
  $("ml-concluir").onclick = () => (linhaMapa.desenhando ? concluirLinha() : buscarPocosLinha());
  $("ml-refazer").onclick = iniciarLinhaMapa;
  $("ml-largura").onchange = () => { if (!linhaMapa.desenhando) buscarPocosLinha(); };
  $("ml-abrir").onclick = () => {
    const r = linhaMapa.resultado;
    if (r && r.pocos.length >= 2) irPara("secao", "receberPocosSecao", r.pocos.map((p) => p.id), r.comprimento_km);
  };
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && linhaMapa.desenhando) { ev.stopPropagation(); fecharLinhaMapa(); }
  }, true);
  ligarLevantamento();
  let espera = null;
  $("f-texto").oninput = () => { clearTimeout(espera); espera = setTimeout(() => consultarMapa(), 350); };
}
