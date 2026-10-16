// SIAPP — aba Mapa: cadastro da ANP, poços no mapa, filtros e ficha do poço.
"use strict";

let mapa = null;            // L.Map
let camadaPocos = null;     // L.LayerGroup com os marcadores
let pocosMapa = [];         // [{id, lat, lon, ...}] da última consulta
let fichaAberta = null;

const CORES = { cad: "#9aa3a8", reate: "#0e5a62", baixado: "#c26a1b" };

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
}

async function carregarMapa() {
  if (!projetoAberto) {
    $("cad-info").textContent = "Abra o projeto primeiro (aba Início).";
    return;
  }
  criarMapa();
  setTimeout(() => mapa && mapa.invalidateSize(), 50);   // a aba estava oculta
  const r = await chamar(null, "cadastro_info");
  if (!r.ok) return;
  desenharCadastroInfo(r);
  preencherBacias(r.bacias);
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
  $("mapa-resumo").textContent = `${numero(pocosMapa.length, 0)} poço(s) com coordenadas` +
    (nReate ? ` · ${numero(nReate, 0)} com pasta no REATE` : "") +
    (nBaix ? ` · ${numero(nBaix, 0)} com arquivos baixados` : "") +
    (r.truncado ? " · lista cortada: refine os filtros" : "");
  desenharListaMapa();
}

function corPoco(p) { return p.baixados ? CORES.baixado : p.reate ? CORES.reate : CORES.cad; }

function desenharMarcadores(enquadrar) {
  camadaPocos.clearLayers();
  const pontos = [];
  for (const p of pocosMapa) {
    const destaque = p.reate || p.baixados;
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
}

function desenharListaMapa() {
  const ul = limpar($("lista-mapa"));
  const ordem = [...pocosMapa].sort((a, b) => (b.baixados - a.baixados) || (b.reate - a.reate) ||
                                              a.id.localeCompare(b.id));
  for (const p of ordem.slice(0, 300)) {
    const b = el("button");
    b.append(el("i", "bola", ""), el("span", "mono", p.id),
             el("span", "ajuda", [p.campo, p.situacao].filter(Boolean).join(" · ")));
    b.firstChild.style.background = corPoco(p);
    b.onclick = () => { abrirFicha(p.id); mapa.setView([p.lat, p.lon], Math.max(mapa.getZoom(), 12)); };
    const li = el("li");
    li.appendChild(b);
    ul.appendChild(li);
  }
  if (pocosMapa.length > 300) ul.appendChild(el("li", "vazio-lista", `… e mais ${numero(pocosMapa.length - 300, 0)}. Refine os filtros.`));
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

  corpo.appendChild(el("h3", "", "No portal REATE"));
  if (!r.reate.length) corpo.appendChild(el("p", "ajuda", "Nenhuma pasta encontrada nas categorias já listadas. Use “Catalogar a bacia conectada”."));
  for (const x of r.reate) {
    const linha = el("div", "linha ficha-reate");
    linha.append(el("span", "", `${x.bacia} · ${x.categoria}${x.parte ? " · " + x.parte : ""}`));
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

function fecharFicha() {
  $("ficha").hidden = true;
  fichaAberta = null;
  setTimeout(() => mapa && mapa.invalidateSize(), 50);
}

// Leva o usuário à árvore de arquivos do poço na aba Catálogo.
async function abrirPocoNoCatalogo(x) {
  trocarAba("catalogo");
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
  for (const id of ["f-bacia", "f-terra", "f-tipo", "f-reate", "f-baixados"]) $(id).onchange = () => consultarMapa(id === "f-bacia");
  let espera = null;
  $("f-texto").oninput = () => { clearTimeout(espera); espera = setTimeout(() => consultarMapa(), 350); };
}
