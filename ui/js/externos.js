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
                 el("small", b ? "ok" : "", b ? `baixada em ${(b.baixado_em || "").slice(0, 10)} · ${numero(b.feicoes, 0)} feições`
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
}
