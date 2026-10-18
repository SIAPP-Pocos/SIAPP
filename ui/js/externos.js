// SIAPP — dados de fora do REATE: produção da ANP por campo (aba Bloco 3D) e camadas geográficas
// do IBGE, EPE e ANP (aba Mapa). Aqui só se baixa e se mostra o que veio; as contas ficam para depois.
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
