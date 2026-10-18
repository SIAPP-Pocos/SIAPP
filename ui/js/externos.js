// SIAPP — dados de fora do REATE: produção da ANP por campo (aba Bloco 3D), camadas geográficas
// do IBGE, EPE e ANP (aba Mapa), o campo diante da infraestrutura e a viabilidade econômica.
"use strict";

const ext = { campos: [], camadas: [], fontes: {} };

// ---------------------------------------------------------------- produção
async function carregarProducao() {
  if (!projetoAberto) return;
  const r = await chamar(null, "producao_campos");
  if (!r.ok) return;
  ext.campos = r.campos;
  const dl = limpar($("pr-lista-campos"));
  for (const c of r.campos) {
    const o = document.createElement("option");
    o.value = c;
    if (r.guardados.includes(c)) o.label = "produção guardada";
    dl.appendChild(o);
  }
  if (!$("pr-campo").value && $("bl-campo").value) {
    $("pr-campo").value = $("bl-campo").value;
    $("pr-campo").dataset.doBloco = "1";                // segue o campo do bloco até ser trocado à mão
  }
  if ($("pr-campo").value) mostrarResumoProducao();
}

async function mostrarResumoProducao() {
  const campo = $("pr-campo").value.trim();
  if (!campo) { limpar($("pr-resumo")); $("pr-csv").hidden = true; return; }
  const r = await chamar(null, "producao_resumo", campo);
  if (r.ok) desenharResumoProducao(r.resumo);
}

const n0 = (v) => (v == null ? "—" : numero(v, 0));
const n1 = (v) => (v == null ? "—" : numero(v, v < 10 ? 2 : 1));
const mes = (p) => (p ? `${p.slice(5, 7)}/${p.slice(0, 4)}` : "—");

function tabelaPares(pares) {
  const t = document.createElement("table");
  for (const [rot, val] of pares) {
    if (val == null || val === "—") continue;
    const tr = document.createElement("tr");
    tr.append(el("th", "", rot), el("td", "", String(val)));
    t.appendChild(tr);
  }
  return t;
}

function desenharResumoProducao(r) {
  const box = limpar($("pr-resumo"));
  const p = r.poco, f = r.ficha || {}, pd = f.pd, fi = f.ficha;
  $("pr-csv").hidden = !p && !r.zona;
  if (!p && !pd && !fi) {
    box.appendChild(el("p", "ajuda", `Nada guardado de ${r.campo} ainda.`));
    return;
  }
  if (fi) {
    box.appendChild(el("h4", "", `${fi.nome} — ${fi.bacia || ""}${fi.estado ? ", " + fi.estado : ""}`));
    box.appendChild(el("p", "ajuda", [fi.operador, fi.ambiente, fi.situacao,
      fi.inicio_producao ? `produz desde ${fi.inicio_producao}` : "",
      f.poligono ? `polígono com ${f.poligono.length} vértices` : ""].filter(Boolean).join(" · ")));
  }
  if (p) {
    box.appendChild(el("h4", "", `Produção por poço, ${mes(p.de)} a ${mes(p.ate)} (soma do período)`));
    box.appendChild(tabelaPares([
      ["poços com registro", n0(p.pocos)],
      ["óleo (m³)", n0(p.oleo_m3)], ["condensado (m³)", p.condensado_m3 ? n0(p.condensado_m3) : null],
      ["gás associado (mil m³)", n0(p.gas_assoc_mil_m3)],
      ["gás não associado (mil m³)", p.gas_nassoc_mil_m3 ? n0(p.gas_nassoc_mil_m3) : null],
      ["água produzida (m³)", n0(p.agua_m3)],
      ["água injetada, recuperação (m³)", p.inj_agua_rec_m3 ? n0(p.inj_agua_rec_m3) : null],
      ["água injetada, descarte (m³)", p.inj_agua_desc_m3 ? n0(p.inj_agua_desc_m3) : null],
      ["vapor injetado (t)", p.inj_vapor_t ? n0(p.inj_vapor_t) : null],
      ["gás injetado (mil m³)", p.inj_gas_mil_m3 ? n0(p.inj_gas_mil_m3) : null],
      ["CO₂ injetado (mil m³)", p.inj_co2_mil_m3 ? n0(p.inj_co2_mil_m3) : null],
    ]));
    const u = r.ultimo_mes;
    if (u) {
      box.appendChild(el("h4", "", `Último mês publicado: ${mes(u.periodo)}`));
      box.appendChild(tabelaPares([["poços produzindo", n0(u.produtores)], ["poços injetando", n0(u.injetores)],
        ["óleo (m³)", n0(u.oleo_m3)], ["gás (mil m³)", n1((u.gas_assoc_mil_m3 || 0) + (u.gas_nassoc_mil_m3 || 0))],
        ["água (m³)", n0(u.agua_m3)]]));
    }
  }
  if (r.zona) {
    box.appendChild(el("h4", "", `Por zona produtora: ${r.zona.zonas} zona(s), ${mes(r.zona.de)} a ${mes(r.zona.ate)}`));
    box.appendChild(el("p", "ajuda", r.zonas.slice(0, 6).map((z) => `${z.zona} (${n0(z.oleo_m3)} m³ de óleo)`).join(" · ") +
      (r.zonas.length > 6 ? ` · e mais ${r.zonas.length - 6}` : "")));
  }
  if (pd) {
    const vip = pd.in_place || {}, acu = pd.acumulada || {};
    const gas = (d) => d.gas_total_milhoes_m3 ?? ((d.gas_associado_milhoes_m3 || 0) + (d.gas_nao_associado_milhoes_m3 || 0) || null);
    box.appendChild(el("h4", "", `Plano de Desenvolvimento ${pd.ano || ""}${pd.fonte ? " (" + pd.fonte + ")" : ""}`));
    box.appendChild(tabelaPares([
      [`óleo in place, ${vip.data || ""} (milhões de m³)`, vip.oleo_milhoes_m3 != null ? n1(vip.oleo_milhoes_m3) : null],
      [`gás in place, ${vip.data || ""} (milhões de m³)`, gas(vip) != null ? n1(gas(vip)) : null],
      [`óleo produzido até ${acu.data || ""} (milhões de m³)`, acu.oleo_milhoes_m3 != null ? n1(acu.oleo_milhoes_m3) : null],
      [`gás produzido até ${acu.data || ""} (milhões de m³)`, gas(acu) != null ? n1(gas(acu)) : null],
      ["área (km²)", pd.area_km2 != null ? n1(pd.area_km2) : null],
      [`poços perfurados (${(pd.pocos || {}).data || ""})`, (pd.pocos || {}).perfurados != null ? n0(pd.pocos.perfurados) : null],
      ["produtores / injetores", pd.pocos ? `${n0(pd.pocos.produtores)} / ${n0(pd.pocos.injetores)}` : null],
    ]));
    if (pd.reservatorios) box.appendChild(el("p", "ajuda", pd.reservatorios));
  }
}

async function baixarProducao() {
  const campo = $("pr-campo").value.trim();
  if (!campo) { status("Escolha o campo.", "erro"); return; }
  $("pr-cancelar").hidden = false;
  status(`Baixando a produção de ${campo} da ANP…`, "trab");
  const r = await chamar($("pr-baixar"), "producao_baixar", campo, $("pr-periodo").value, $("pr-zona").checked);
  $("pr-cancelar").hidden = true;
  if (!r.ok) return;
  desenharResumoProducao(r.resumo);
  const f = r.feito;
  const avisos = f.avisos.length ? ` Avisos: ${f.avisos.join(" ")}` : "";
  status(`Produção de ${campo}: ${numero(f.linhas_poco, 0)} linhas por poço, ${numero(f.linhas_zona, 0)} por zona, ` +
         `de ${f.arquivos} arquivo(s) da ANP (${numero(f.mb_baixados, 0)} MB baixados agora).${avisos}`, "ok");
  carregarProducao();
}

async function exportarProducao() {
  const r = await chamar($("pr-csv"), "producao_exportar_csv", $("pr-campo").value.trim());
  if (r.ok) status(`Salvo em ambiente_teste/${r.arquivos.join(" e ")}`, "ok");
}

// ---------------------------------------------------------------- camadas
async function carregarCamadas() {
  const r = await chamar(null, "camadas_catalogo");
  if (!r.ok) return;
  ext.camadas = r.camadas;
  ext.fontes = r.fontes;
  desenharCamadas();
  desenharListaMapaCamadas();
  if (!$("vb-campo").value && $("pr-campo").value) $("vb-campo").value = $("pr-campo").value;
  carregarAreas();
}

function desenharCamadas() {
  const box = $("cm-lista");
  const marcadas = new Set([...box.querySelectorAll("input:checked")].map((c) => c.value));
  const primeira = !box.querySelector("input");
  limpar(box);
  for (const fonte of ["EPE", "ANP", "IBGE"]) {
    box.appendChild(el("h4", "", ext.fontes[fonte] || fonte));
    for (const c of ext.camadas.filter((x) => x.fonte === fonte)) {
      const lab = el("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = c.id;
      cb.checked = primeira ? (c.padrao && !c.baixada) : marcadas.has(c.id);
      lab.title = c.desc;
      const b = c.baixada;
      lab.append(cb, el("span", "", c.nome),
                 el("small", b ? "ok" : "", b ? `baixada em ${(b.baixado_em || "").slice(0, 10)} · ${numero(b.feicoes, 0)} feições` +
                                                   (b.sem_coordenadas ? ` (${b.sem_coordenadas} sem coordenadas na fonte)` : "")
                                               : c.desc));
      box.appendChild(lab);
    }
  }
}

async function baixarCamadas() {
  const ids = [...$("cm-lista").querySelectorAll("input:checked")].map((c) => c.value);
  if (!ids.length) { status("Marque ao menos uma camada.", "erro"); return; }
  status(`Baixando ${ids.length} camada(s)…`, "trab");
  const r = await chamar($("cm-baixar"), "camadas_baixar", ids);
  if (!r.ok) return;
  ext.camadas = r.camadas;
  for (const cb of $("cm-lista").querySelectorAll("input")) cb.checked = false;
  desenharCamadas();
  desenharListaMapaCamadas();
  carregarAreas();
  const ul = limpar($("cm-erros"));
  for (const e of r.erros) ul.appendChild(el("li", "", `${e.nome || e.id}: ${e.erro}`));
  status(`${r.feitos.length} camada(s) guardada(s) em ambiente_teste/sig` +
         (r.erros.length ? `; ${r.erros.length} com erro (veja a lista).` : "."), r.erros.length ? "erro" : "ok");
}

function ligarExternos() {
  ligar("pr-baixar", "onclick", baixarProducao);
  ligar("pr-cancelar", "onclick", () => chamar(null, "producao_cancelar"));
  ligar("pr-csv", "onclick", exportarProducao);
  ligar("pr-campo", "onchange", () => { $("pr-campo").dataset.doBloco = "0"; mostrarResumoProducao(); });
  ligar("cm-baixar", "onclick", baixarCamadas);
  ligar("cm-pasta", "onclick", () => chamar(null, "abrir_pasta_sig"));
  ligar("vb-medir", "onclick", medirDistancias);
  ligar("vb-csv", "onclick", exportarViabilidade);
  ligar("vb-campo", "onchange", () => {
    $("vb-eco").hidden = true;
    limpar($("vb-eco-resultado"));
    $("vb-mem-caixa").hidden = true;
  });
  ligar("vb-avaliar", "onclick", avaliarViabilidade);
  ligar("vb-eco-csv", "onclick", exportarEconomia);
  ligar("vb-fonte-custo", "onchange", aplicarReferenciaCusto);
  ligar("vb-custo", "oninput", () => { $("vb-fonte-custo").value = "manual"; ajudaCustoVb(); });
  ligar("vb-diametro", "oninput", ajudaCustoVb);
  ligar("vb-fluido", "onchange", ajudaCustoVb);
  ligar("ba-medir", "onclick", medirAreas);
  ligar("ba-csv", "onclick", async () => {
    const r = await chamar($("ba-csv"), "areas_csv");
    if (r.ok) status(`Salvo em ambiente_teste/${r.arquivo}`, "ok");
  });
  ligar("ba-filtro", "oninput", () => ba.resultado && desenharAreas(ba.resultado));
  ligar("vb-eq-padrao", "onclick", () => preencherParametrosVb({ ...lerParametrosVb(), constantes: {}, equacoes: {} }));
  ligar("vb-mem-abrir", "onclick", () => vbEco.memoria && chamar($("vb-mem-abrir"), "viabilidade_abrir_memoria", vbEco.memoria.html));
}

// ---------------------------------------------------------------- camadas no mapa
// cor e traço por camada (gasoduto de transporte em vermelho, escoamento em laranja, H₂ em verde…)
const ESTILO_CAMADA = {
  epe_gasodutos_transporte: { cor: "#c0392b", peso: 3 },
  epe_dutos_escoamento: { cor: "#e67e22", peso: 2, traco: "6 4" },
  epe_gasodutos_distribuicao: { cor: "#8e44ad", peso: 1.5 },
  epe_upgn: { cor: "#1b1f23", raio: 6 },
  epe_compressao: { cor: "#7f8c8d", raio: 5 },
  epe_citygates: { cor: "#c0392b", raio: 4 },
  epe_terminais_gnl: { cor: "#2471a3", raio: 6 },
  epe_termeletricas_fosseis: { cor: "#4d4d4d", raio: 6 },
  epe_h2_projetos: { cor: "#1e9e5a", raio: 7 },
  anp_campos_producao: { cor: "#1f6fb2", peso: 1.5, preench: 0.12 },
  anp_blocos_exploratorios: { cor: "#9a6a2f", peso: 1.2, traco: "4 3", preench: 0.05 },
  ibge_dutos: { cor: "#95a5a6", peso: 2 },
  ibge_termeletricas: { cor: "#4d4d4d", raio: 4 },
  ibge_linhas_transmissao: { cor: "#f1c40f", peso: 1 },
  ibge_subestacoes: { cor: "#b7950b", raio: 3 },
  ibge_portos: { cor: "#1a3d6d", raio: 5 },
  ibge_cidades: { cor: "#555", raio: 2.5 },
  ibge_estados: { cor: "#555", peso: 1, preench: 0 },
  ibge_ferrovias: { cor: "#5d4037", peso: 1.5, traco: "2 3" },
  ibge_rodovias: { cor: "#b0b0b0", peso: 1 },
};
const sig = { camadas: {}, vb: null };

function desenharListaMapaCamadas() {
  const box = limpar($("cm-mapa"));
  const baixadas = ext.camadas.filter((c) => c.baixada);
  if (!baixadas.length) return;
  box.appendChild(el("h4", "", "Mostrar no mapa"));
  for (const c of baixadas) {
    const e = ESTILO_CAMADA[c.id] || { cor: "#333", peso: 1 };
    const lab = el("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.dataset.camada = c.id;
    cb.checked = Boolean(sig.camadas[c.id]);
    cb.onchange = () => mostrarCamadaSig(c.id, cb.checked);
    const amostra = el("i", `cm-amostra ${c.tipo === "ponto" ? "ponto" : c.tipo === "poligono" ? "poligono" : ""}`);
    amostra.style.borderColor = e.cor;
    if (e.traco && c.tipo === "linha") amostra.style.borderTopStyle = "dashed";
    lab.append(cb, amostra, el("span", "", c.nome));
    box.appendChild(lab);
  }
}

function popupSig(props, nome) {
  const linhas = Object.entries(props || {}).filter(([, v]) => v !== null && v !== "" && v !== " ").slice(0, 10)
    .map(([k, v]) => `<tr><th>${escaparHtml(k)}</th><td>${escaparHtml(String(v))}</td></tr>`).join("");
  return `<strong>${escaparHtml(nome)}</strong><table class="pp-tabela">${linhas}</table>`;
}

function escaparHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c]));
}

async function mostrarCamadaSig(id, ligar) {
  if (!mapa) return;
  if (!ligar) {
    if (sig.camadas[id]) { mapa.removeLayer(sig.camadas[id]); delete sig.camadas[id]; }
    return;
  }
  const r = await chamar(null, "sig_camada", id);
  if (!r.ok) return;
  const e = ESTILO_CAMADA[id] || { cor: "#333", peso: 1 };
  const nome = r.camada.nome;
  const camada = L.geoJSON(r.geojson, {
    style: () => ({ color: e.cor, weight: e.peso || 1.5, dashArray: e.traco || null,
                    fillColor: e.cor, fillOpacity: e.preench ?? 0 }),
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: e.raio || 4, color: "#fff", weight: 1,
                                                  fillColor: e.cor, fillOpacity: 0.95 }),
    onEachFeature: (f, l) => l.bindPopup(popupSig(f.properties, nome)),
  });
  sig.camadas[id] = camada.addTo(mapa);
  $("mapa-vazio").hidden = true;                 // as camadas valem mesmo sem o cadastro de poços
  status(`${nome}: ${numero(r.geojson.features.length, 0)} feições no mapa.`, "ok");
}

// ---------------------------------------------------------------- campo × infraestrutura
async function medirDistancias() {
  const campo = $("vb-campo").value.trim();
  if (!campo) { status("Escolha o campo.", "erro"); return; }
  const r = await chamar($("vb-medir"), "viabilidade_relatorio", campo);
  if (!r.ok) return;
  desenharViabilidade(r.relatorio);
  $("vb-csv").hidden = false;
  if (await carregarOpcoesViabilidade()) {
    preencherParametrosVb(r.parametros);
    limpar($("vb-eco-resultado"));
    $("vb-eco-csv").hidden = true;
    $("vb-eco").hidden = false;
  }
  status(`Distâncias de ${campo} medidas (polígono: ${r.relatorio.fonte_poligono}).`, "ok");
}

function desenharViabilidade(rel) {
  const box = limpar($("vb-resultado"));
  box.appendChild(el("p", "ajuda", `Polígono: ${rel.fonte_poligono}.`));
  const t = document.createElement("table");
  const faltam = [];
  for (const d of rel.distancias) {
    if (!d.baixada) { faltam.push(d.rotulo); continue; }
    if (d.distancia_km == null) continue;
    const tr = document.createElement("tr");
    const th = el("th", "", d.rotulo);
    const desc = Object.values(d.feicao || {}).slice(0, 3).join(" · ");
    if (desc) th.appendChild(el("span", "vb-sub", desc));
    const km = d.toca_o_campo ? "no campo" : `${numero(d.distancia_km, d.distancia_km < 10 ? 1 : 0)} km`;
    tr.append(th, el("td", "vb-km", km));
    t.appendChild(tr);
  }
  box.appendChild(t);
  if (faltam.length) box.appendChild(el("p", "ajuda", `Sem a camada (baixe acima para medir): ${faltam.join(", ")}.`));
  const dep = rel.deplecao;
  if (dep) {
    box.appendChild(el("h4", "", `Depleção — ${dep.fonte || "Plano de Desenvolvimento"}${dep.data_pd ? ", " + dep.data_pd : ""}`));
    const t2 = document.createElement("table");
    for (const [nome, rot] of [["oleo", "óleo"], ["gas", "gás"]]) {
      const d = dep[nome];
      if (!d) continue;
      const tr = document.createElement("tr");
      const th = el("th", "", `${rot}: produzido / in place`);
      th.appendChild(el("span", "vb-sub", `${numero(d.produzido_pd_milhoes_m3, 2)} de ${numero(d.in_place_milhoes_m3, 2)} milhões de m³`));
      tr.append(th, el("td", "vb-km", d.fracao_pd != null ? `${numero(d.fracao_pd * 100, 1)}%` : "—"));
      t2.appendChild(tr);
      if (d.fracao_atual_estimada != null) {
        const tr2 = document.createElement("tr");
        const th2 = el("th", "", `${rot}: estimativa até ${d.ate.slice(5, 7)}/${d.ate.slice(0, 4)}`);
        th2.appendChild(el("span", "vb-sub", `+ ${numero(d.produzido_depois_milhoes_m3, 3)} milhões de m³ na produção mensal da ANP`));
        tr2.append(th2, el("td", "vb-km", `${numero(d.fracao_atual_estimada * 100, 1)}%`));
        t2.appendChild(tr2);
      }
    }
    box.appendChild(t2);
  } else {
    box.appendChild(el("p", "ajuda", "Depleção: baixe a produção do campo (aba Bloco 3D) para ter o sumário do PD."));
  }
  desenharViabilidadeNoMapa(rel);
}

function desenharViabilidadeNoMapa(rel) {
  if (!mapa) return;
  if (sig.vb) mapa.removeLayer(sig.vb);
  const g = L.layerGroup();
  const poli = L.polygon(rel.poligono, { color: "#f1c40f", weight: 3, fillOpacity: 0.08 }).bindTooltip(rel.campo);
  g.addLayer(poli);
  const pontos = rel.poligono.slice();
  for (const d of rel.distancias) {
    if (!d.baixada || d.distancia_km == null || d.toca_o_campo) continue;
    const e = ESTILO_CAMADA[d.id] || { cor: "#333" };
    const linha = L.polyline([d.ponto_campo, d.ponto_feicao], { color: e.cor, weight: 1.5, dashArray: "4 4" });
    linha.bindTooltip(`${d.rotulo}: ${numero(d.distancia_km, 1)} km`, { className: "vb-rotulo" });
    g.addLayer(linha);
    g.addLayer(L.circleMarker(d.ponto_feicao, { radius: 4, color: e.cor, fillOpacity: 1 }));
    if (d.distancia_km < 150) pontos.push(d.ponto_feicao);
  }
  sig.vb = g.addTo(mapa);
  $("mapa-vazio").hidden = true;
  mapa.fitBounds(L.latLngBounds(pontos).pad(0.1));
}

async function exportarViabilidade() {
  const r = await chamar($("vb-csv"), "viabilidade_csv", $("vb-campo").value.trim());
  if (r.ok) status(`Salvo em ambiente_teste/${r.arquivo}`, "ok");
}

// ---------------------------------------------------------------- viabilidade econômica (0.26)
const vbEco = { opcoes: null, memoria: null };
const semEspaco = (f) => String(f || "").replace(/\s+/g, "").replace(/\^/g, "**");
const num6 = (v) => (v == null ? "—" : typeof v === "string" ? v
  : Number(v).toLocaleString("pt-BR", { maximumSignificantDigits: 6 }));

function numeroBr(s) {
  const t = String(s == null ? "" : s).trim();
  if (!t) return null;
  const n = Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t);
  return Number.isFinite(n) ? n : null;
}

async function carregarOpcoesViabilidade() {
  if (vbEco.opcoes) return vbEco.opcoes;
  const r = await chamar(null, "viabilidade_opcoes");
  if (!r.ok) return null;
  vbEco.opcoes = r;
  const fl = limpar($("vb-fluido"));
  for (const f of r.fluidos) {
    const o = el("option", "", f.rotulo);
    o.value = f.id;
    fl.appendChild(o);
  }
  const fc = limpar($("vb-fonte-custo"));
  for (const f of r.fontes_custo) {
    const o = el("option", "", `${f.rotulo} — R$ ${numero(f.r_mil_pol_km, 0)} mil/pol·km`);
    o.value = f.id;
    fc.appendChild(o);
  }
  const m = el("option", "", "informado por mim");
  m.value = "manual";
  fc.appendChild(m);
  montarConstantesVb(r.constantes);
  montarEquacoesVb(r.equacoes, r.simbolos);
  return r;
}

function montarConstantesVb(lista) {
  const box = limpar($("vb-constantes"));
  let grupo = null, grade = null;
  for (const c of lista) {
    if (c.grupo !== grupo) {
      grupo = c.grupo;
      box.appendChild(el("div", "vb-const-grupo", grupo));
      grade = el("div", "filtros vb-form");
      box.appendChild(grade);
    }
    const lab = el("label", "", `${c.rotulo}${c.unidade && c.unidade !== "—" ? " (" + c.unidade + ")" : ""}`);
    lab.title = `Padrão ${num6(c.valor)} — ${c.fonte}. Aceito: ${num6(c.faixa[0])} a ${num6(c.faixa[1])}.`;
    const inp = el("input", "curto");
    inp.type = "text";
    inp.inputMode = "decimal";
    inp.placeholder = num6(c.valor);
    inp.dataset.vbc = c.id;
    inp.oninput = () => { inp.classList.toggle("alterada", inp.value.trim() !== ""); ajudaCustoVb(); };
    lab.appendChild(inp);
    grade.appendChild(lab);
  }
}

function montarEquacoesVb(lista, simbolos) {
  const box = limpar($("vb-equacoes"));
  for (const q of lista) {
    const d = el("div", "vb-eq");
    d.appendChild(el("b", "", `${q.titulo} → ${q.resultado} (${q.unidade})`));
    const sel = document.createElement("select");
    sel.dataset.vbeSel = q.id;
    const op = (rot, val) => { const o = el("option", "", rot); o.value = val; sel.appendChild(o); };
    op(`padrão: ${q.padrao}`, "__padrao");
    q.alternativas.forEach((a, i) => op(`${a.nome}: ${a.formula}`, String(i)));
    op("a minha fórmula", "__propria");
    const inp = el("input");
    inp.type = "text";
    inp.dataset.vbe = q.id;
    inp.spellcheck = false;
    inp.value = q.padrao;
    sel.onchange = () => {
      if (sel.value === "__padrao") inp.value = q.padrao;
      else if (sel.value !== "__propria") inp.value = q.alternativas[Number(sel.value)].formula;
      else inp.focus();
      sincronizarEquacaoVb(q, sel, inp);
    };
    inp.oninput = () => sincronizarEquacaoVb(q, sel, inp);
    const vars = q.variaveis.map((v) => `${v} = ${(simbolos[v] || {}).descricao || v}` +
      ((simbolos[v] || {}).unidade ? ` (${simbolos[v].unidade})` : "")).join("; ");
    d.append(sel, inp, el("p", "ajuda", q.explicacao), el("p", "ajuda", `Variáveis: ${vars}.`));
    box.appendChild(d);
  }
  const t = limpar($("vb-simbolos"));
  for (const [k, v] of Object.entries(simbolos)) {
    const tr = document.createElement("tr");
    tr.append(el("td", "", k), el("td", "", `${v.descricao}${v.unidade ? " (" + v.unidade + ")" : ""}`));
    t.appendChild(tr);
  }
}

function sincronizarEquacaoVb(q, sel, inp) {
  const f = semEspaco(inp.value);
  if (f === semEspaco(q.padrao)) sel.value = "__padrao";
  else {
    const i = q.alternativas.findIndex((a) => semEspaco(a.formula) === f);
    sel.value = i >= 0 ? String(i) : "__propria";
  }
  inp.classList.toggle("alterada", sel.value !== "__padrao");
}

function preencherParametrosVb(guardados) {
  const g = guardados || {};
  const v = { ...vbEco.opcoes.padroes, ...g };
  for (const e of document.querySelectorAll("[data-vb]")) {
    const x = v[e.dataset.vb];
    e.value = x == null ? "" : typeof x === "number" ? String(x).replace(".", ",") : String(x);
  }
  if (g.custo_mil_pol_km == null || g.custo_mil_pol_km === "") aplicarReferenciaCusto();
  const cs = g.constantes || {};
  for (const e of document.querySelectorAll("[data-vbc]")) {
    const x = cs[e.dataset.vbc];
    e.value = x == null ? "" : String(x).replace(".", ",");
    e.classList.toggle("alterada", e.value !== "");
  }
  const eqs = g.equacoes || {};
  for (const q of vbEco.opcoes.equacoes) {
    const inp = document.querySelector(`[data-vbe="${q.id}"]`), sel = document.querySelector(`[data-vbe-sel="${q.id}"]`);
    inp.value = eqs[q.id] || q.padrao;
    sincronizarEquacaoVb(q, sel, inp);
  }
  ajudaCustoVb();
}

function aplicarReferenciaCusto() {
  const f = vbEco.opcoes.fontes_custo.find((x) => x.id === $("vb-fonte-custo").value);
  if (f) $("vb-custo").value = String(f.r_mil_pol_km);
  ajudaCustoVb();
}

function ajudaCustoVb() {
  if (!vbEco.opcoes) return;
  const fl = vbEco.opcoes.fluidos.find((x) => x.id === $("vb-fluido").value);
  const custo = numeroBr($("vb-custo").value), d = numeroBr($("vb-diametro").value);
  if (!fl || custo == null || d == null) { $("vb-custo-ajuda").textContent = ""; return; }
  const alt = document.querySelector(`[data-vbc="f_${fl.id}"]`);
  const fator = (alt && numeroBr(alt.value)) || fl.fator;
  $("vb-custo-ajuda").textContent = `Duto de ${numero(d, 1)}″ para ${fl.rotulo}: R$ ${numero(custo * d * fator / 1000, 2)} ` +
    `milhões por km pela equação padrão (×${numero(fator, 2)}` + (fator === fl.fator ? ` — ${fl.motivo}).` : ", alterado por você).");
}

function lerParametrosVb() {
  const p = {};
  for (const e of document.querySelectorAll("[data-vb]")) {
    if (e.value.trim() !== "") p[e.dataset.vb] = e.value.trim();
  }
  p.constantes = {};
  for (const e of document.querySelectorAll("[data-vbc]")) {
    if (e.value.trim() !== "") p.constantes[e.dataset.vbc] = e.value.trim();
  }
  p.equacoes = {};
  for (const q of (vbEco.opcoes || { equacoes: [] }).equacoes) {
    const f = document.querySelector(`[data-vbe="${q.id}"]`).value.trim();
    if (f && semEspaco(f) !== semEspaco(q.padrao)) p.equacoes[q.id] = f;
  }
  return p;
}

async function avaliarViabilidade() {
  const campo = $("vb-campo").value.trim();
  if (!campo) { status("Escolha o campo.", "erro"); return; }
  const r = await chamar($("vb-avaliar"), "viabilidade_economia", campo, lerParametrosVb());
  if (!r.ok) return;
  desenharEconomia(r.avaliacao);
  vbEco.memoria = r.memoria;
  desenharMemoria(r.avaliacao, r.memoria);
  $("vb-eco-csv").hidden = false;
  const feitos = Object.values(r.avaliacao.metodos).filter((m) => m.valor).length;
  status(`Viabilidade de ${campo}: ${feitos} de 3 métodos com dados suficientes.`, "ok");
}

const reais = (v) => (v == null ? "—" : numero(v, v < 1 ? 3 : v < 100 ? 2 : 0));

function textoCapacidade(m) {
  if (m.valor == null) return null;
  if (m.metodo === "molecula") {
    if (m.massa_mt != null) return `${numero(m.massa_mt, m.massa_mt < 1 ? 3 : 2)} Mt de CO₂`;
    if (m.energia_util_mwh != null) return `${numero(m.valor, 0)} t de H₂ úteis`;
    return `${numero(m.volume_padrao_util_milhoes_m3, 1)} milhões de m³ úteis`;
  }
  return m.valor >= 1e6 ? `${numero(m.valor / 1e6, 3)} milhões de ${m.unidade}` : `${numero(m.valor, 0)} ${m.unidade}`;
}

function detalheCapacidade(m) {
  if (m.falta) return `falta: ${m.falta.join(", ")}`;
  if (m.metodo === "molecula") {
    const c = m.condicoes;
    let t = `ρ = ${numero(m.densidade_kg_m3, 1)} kg/m³ a ${numero(c.pressao_bar, 0)} bar e ${numero(c.temperatura_c, 0)} °C ` +
      `(${c.origem_pressao === "informada" && c.origem_temperatura === "informada" ? "P e T informadas"
        : `${c.origem_pressao}; ${c.origem_temperatura}`}` + (c.origem_profundidade && c.origem_profundidade !== "informada"
        ? `; ${numero(c.profundidade_m, 0)} m pela ${c.origem_profundidade}` : "") + ")";
    if (m.energia_util_mwh != null) t += ` · ${numero(m.energia_util_mwh / 1000, 1)} GWh (PCI)`;
    if (m.colchao != null) t += ` · colchão ${numero(m.colchao * 100, 0)}%`;
    return t;
  }
  return m.formula;
}

function desenharEconomia(av) {
  const box = limpar($("vb-eco-resultado"));
  const c = av.custo;
  box.appendChild(el("p", "ajuda", `Duto: R$ ${numero(c.r_por_km / 1e6, 2)} milhões por km — ${c.referencia}` +
    `${c.data_base ? ", data-base " + c.data_base : ""}; ${numero(c.diametro_pol, 1)}″, ×${numero(c.fator_fluido, 2)} pelo fluido` +
    `${av.parametros.fator_tracado !== 1 ? `, traçado ×${numero(av.parametros.fator_tracado, 2)}` : ""}.`));
  box.appendChild(el("p", "ajuda", `Produção acumulada: ${av.acumulados.fonte}.`));

  box.appendChild(el("h4", "", "Capacidade de injeção"));
  const t = document.createElement("table");
  for (const k of ["simples", "poroso", "molecula"]) {
    const m = av.metodos[k];
    const tr = document.createElement("tr");
    const th = el("th", "", m.rotulo);
    th.appendChild(el("span", "vb-sub", detalheCapacidade(m)));
    const v = textoCapacidade(m);
    tr.append(th, el("td", v ? "vb-km" : "vb-falta", v || "sem dados"));
    t.appendChild(tr);
  }
  box.appendChild(t);

  box.appendChild(el("h4", "", "Custo do duto ÷ capacidade"));
  const temMwh = av.linhas.some((l) => l.r_por_mwh != null);
  const t2 = document.createElement("table");
  t2.className = "vb-ind";
  const cab = document.createElement("tr");
  for (const h of ["Até", "Duto R$ mi", "R$/m³ oe", "R$/m³ res", `R$/t ${vbEco.opcoes.fluidos.find((f) => f.id === av.parametros.fluido).rotulo}`]
    .concat(temMwh ? ["R$/MWh"] : [])) cab.appendChild(el("th", "", h));
  t2.appendChild(cab);
  for (const l of av.linhas) {
    const tr = document.createElement("tr");
    if (l.origem_tipica) tr.className = "vb-origem";
    const th = el("th", "", (l.origem_tipica ? "★ " : "") + l.rotulo);
    th.appendChild(el("span", "vb-sub", l.toca_o_campo ? "no campo" : `${numero(l.distancia_km, 1)} km`));
    tr.append(th, el("td", "", numero(l.custo_r / 1e6, l.custo_r < 1e7 ? 2 : 0)));
    for (const k of ["simples", "poroso", "molecula"]) tr.appendChild(el("td", "vb-km", reais(l.indicadores[k])));
    if (temMwh) tr.appendChild(el("td", "vb-km", reais(l.r_por_mwh)));
    t2.appendChild(tr);
  }
  box.appendChild(t2);
  box.appendChild(el("p", "ajuda", "★ origem natural do fluido escolhido. Menor = mais viável: menos investimento em duto " +
    "por unidade de espaço. É triagem para comparar campos — pressão e injetividade só a simulação responde."));
  if (av.avisos.length) {
    const ul = el("ul", "vb-avisos");
    for (const a of av.avisos) ul.appendChild(el("li", "", a));
    box.appendChild(ul);
  }
}

async function exportarEconomia() {
  const r = await chamar($("vb-eco-csv"), "viabilidade_economia_csv", $("vb-campo").value.trim(), lerParametrosVb());
  if (r.ok) status(`Salvo em ambiente_teste/${r.arquivo}`, "ok");
}

// memória de cálculo na tela (a mesma que vai para o HTML e o JSON em execucoes/viabilidade)
const NOMES_METODO = { custo: "Custo do duto por km", simples: "Método simples (PIBIC)", poroso: "Espaço poroso",
  molecula: "Pela molécula", condicoes: "Condições do reservatório", pvt: "Propriedades dos fluidos (correlações)" };

function passoMemoria(s, curto) {
  const d = el("div", "passo");
  if (s.id === "nota") {
    d.appendChild(el("b", "", s.titulo));
    d.appendChild(el("div", "ajuda", s.explicacao));
    if (s.detalhes && s.detalhes.length) {
      const t = document.createElement("table");
      for (const x of s.detalhes) {
        const tr = document.createElement("tr");
        tr.append(el("td", "", x.grandeza), el("td", "", x.expressao), el("td", "", num6(x.valor)));
        t.appendChild(tr);
      }
      d.appendChild(t);
    }
    d.appendChild(el("div", "res", `= ${num6(s.resultado)} ${s.unidade || ""}`));
    return d;
  }
  const tit = el("b", "", s.titulo + (curto && s.metodo !== "linha" ? ` (${NOMES_METODO[s.metodo] || s.metodo})` : ""));
  d.appendChild(tit);
  if (s.alterada) {
    d.appendChild(document.createTextNode(" "));
    d.appendChild(el("span", "tag", s.alternativa ? `alternativa: ${s.alternativa}` : "fórmula do usuário"));
  }
  d.appendChild(el("code", s.alterada ? "alt" : "", `${s.resultado_simbolo} = ${s.equacao}`));
  d.appendChild(el("code", "", `${s.resultado_simbolo} = ${s.substituida}`));
  d.appendChild(el("div", "res", `${s.resultado_simbolo} = ${num6(s.resultado)} ${s.unidade}`));
  return d;
}

function desenharMemoria(av, arquivos) {
  const box = limpar($("vb-memoria"));
  const m = av.memoria;
  $("vb-mem-caixa").hidden = false;
  $("vb-mem-arquivo").textContent = arquivos ? `Gravada em ambiente_teste/${arquivos.html} (e .json ao lado), com ` +
    `todos os dados, equações e resultados desta execução.` : "";
  box.appendChild(el("h5", "", "Dados de entrada e de onde vieram"));
  const t = document.createElement("table");
  for (const x of m.entradas) {
    const tr = document.createElement("tr");
    const th = el("td", "", x.simbolo);
    th.title = x.descricao;
    const fonte = el("td", "", x.fonte);
    tr.append(th, el("td", "", `${num6(x.valor)} ${x.unidade || ""}`), fonte);
    t.appendChild(tr);
  }
  box.appendChild(t);
  let atual = null;
  for (const s of m.passos) {
    if (s.metodo !== atual) { atual = s.metodo; box.appendChild(el("h5", "", NOMES_METODO[atual] || atual)); }
    box.appendChild(passoMemoria(s, false));
  }
  for (const l of av.linhas) {
    const det = el("details");
    det.appendChild(el("summary", "", `${l.rotulo}: duto e indicadores`));
    det.appendChild(el("div", "ajuda", l.fonte_distancia));
    for (const s of l.memoria) det.appendChild(passoMemoria(s, true));
    box.appendChild(det);
  }
}

// ---------------------------------------------------------------- blocos e campos × infraestrutura (0.28)
const ba = { resultado: null, camada: null };
const CLASSES_DIST = [[0, "toca ou atravessa", "#1a7f37"], [10, "até 10 km", "#4caf50"], [50, "10–50 km", "#c9b800"],
  [100, "50–100 km", "#e67e22"], [Infinity, "mais de 100 km", "#c0392b"]];

function classeDist(km) {
  if (km == null) return null;
  if (km === 0) return CLASSES_DIST[0];
  return CLASSES_DIST.slice(1).find(([lim]) => km <= lim);
}

async function carregarAreas() {
  if (!projetoAberto) return;
  const r = await chamar(null, "areas_opcoes");
  if (!r.ok) return;
  for (const [id, lista, padrao] of [["ba-areas", r.areas, "anp_blocos_exploratorios"],
    ["ba-alvo", r.alvos, "epe_gasodutos_transporte"]]) {
    const sel = $(id), atual = sel.value;
    limpar(sel);
    for (const a of lista) {
      const o = el("option", "", a.baixada ? a.rotulo : `${a.rotulo} (baixe acima)`);
      o.value = a.id;
      o.disabled = !a.baixada;
      sel.appendChild(o);
    }
    const ok = (v) => lista.some((a) => a.id === v && a.baixada);
    sel.value = ok(atual) ? atual : ok(padrao) ? padrao : (lista.find((a) => a.baixada) || {}).id || "";
  }
}

async function medirAreas() {
  const areas = $("ba-areas").value, alvo = $("ba-alvo").value;
  if (!areas || !alvo) { status("Baixe a camada de áreas e a de infraestrutura no quadro Camadas geográficas.", "erro"); return; }
  const parametros = vbEco.opcoes ? lerParametrosVb() : {};
  status("Medindo as distâncias de todas as áreas…", "trab");
  const r = await chamar($("ba-medir"), "areas_distancias", areas, alvo, parametros);
  if (!r.ok) return;
  ba.resultado = r.resultado;
  $("ba-csv").hidden = false;
  $("ba-filtro-caixa").hidden = false;
  desenharAreas(r.resultado);
  await desenharAreasNoMapa(r.resultado);
  status(`${r.resultado.linhas.length} áreas medidas até ${r.resultado.rotulo_alvo}.`, "ok");
}

function desenharAreas(res) {
  const box = limpar($("ba-resultado"));
  const c = res.custo;
  box.appendChild(el("p", "ajuda", `${res.rotulo_areas} até ${res.rotulo_alvo}. Duto: R$ ${numero(c.r_por_km / 1e6, 2)} ` +
    `milhões por km (${c.referencia}${c.data_base ? ", " + c.data_base : ""}; ${numero(c.diametro_pol, 1)}″, ` +
    `×${numero(c.fator_fluido, 2)} pelo fluido). ${res.formulas.comprimento}; ${res.formulas.custo_duto}.`));
  const cont = CLASSES_DIST.map(() => 0);
  for (const l of res.linhas) {
    const k = classeDist(l.distancia_km);
    if (k) cont[CLASSES_DIST.indexOf(k)]++;
  }
  const leg = el("p", "ajuda");
  CLASSES_DIST.forEach(([, rot, cor], i) => {
    const sp = el("span", "cm-amostra ponto");
    sp.style.borderColor = cor;
    sp.style.background = cor;
    leg.append(sp, document.createTextNode(` ${rot}: ${cont[i]}  `));
  });
  box.appendChild(leg);
  const filtro = $("ba-filtro").value.trim().toLowerCase();
  const casa = (l) => !filtro || [l.nome, ...Object.values(l.atributos || {})].join(" ").toLowerCase().includes(filtro);
  const lista = res.linhas.filter((l) => l.distancia_km != null && casa(l))
    .sort((a, b) => a.distancia_km - b.distancia_km);
  const t = document.createElement("table");
  t.className = "vb-ind";
  const cab = document.createElement("tr");
  for (const h of ["Área", "km", "Duto R$ mi"]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const l of lista.slice(0, 40)) {
    const tr = document.createElement("tr");
    const th = el("th", "", l.nome);
    const a = l.atributos || {};
    th.appendChild(el("span", "vb-sub", [a.NOM_BACIA, a.OPERADOR_C, Object.values(l.feicao || {})[0]].filter(Boolean).join(" · ")));
    th.style.cursor = "pointer";
    th.onclick = () => { if (mapa && l.ponto_area) mapa.setView(l.ponto_area, 9); };
    tr.append(th, el("td", "vb-km", l.toca ? "toca" : numero(l.distancia_km, l.distancia_km < 10 ? 1 : 0)),
      el("td", "", numero(l.custo_r / 1e6, l.custo_r < 1e7 ? 2 : 0)));
    t.appendChild(tr);
  }
  box.appendChild(t);
  box.appendChild(el("p", "ajuda", `${lista.length} área(s)${filtro ? " no filtro" : ""}; a tabela mostra as 40 mais ` +
    `próximas (clique no nome para ir até ela). O CSV traz todas, com as fórmulas e as entradas. Gravado em ` +
    `ambiente_teste/${res.arquivo}.`));
}

async function desenharAreasNoMapa(res) {
  if (!mapa) return;
  const r = await chamar(null, "sig_camada", res.areas);
  if (!r.ok) return;
  if (ba.camada) mapa.removeLayer(ba.camada);
  const porIndice = new Map(res.linhas.map((l) => [l.indice, l]));
  const pos = new Map(r.geojson.features.map((f, k) => [f, k]));
  ba.camada = L.geoJSON(r.geojson, {
    style: (f) => {
      const l = porIndice.get(pos.get(f)), k = l ? classeDist(l.distancia_km) : null;
      return { color: k ? k[2] : "#999", weight: 1, fillColor: k ? k[2] : "#999", fillOpacity: 0.35 };
    },
    onEachFeature: (f, camada) => {
      const l = porIndice.get(pos.get(f));
      if (l) camada.bindTooltip(`${l.nome}: ${l.toca ? "toca ou atravessa" : numero(l.distancia_km, 1) + " km"}` +
        ` até ${res.rotulo_alvo} · R$ ${numero(l.custo_r / 1e6, 1)} mi`);
    },
  }).addTo(mapa);
  $("mapa-vazio").hidden = true;
  mapa.fitBounds(ba.camada.getBounds().pad(0.05));
}
