// SIAPP — avaliação de formação (aba Perfis): Vsh, φ, Sw e net pay no intervalo-alvo.
// O cálculo é do motor (motor/avaliacao.py); aqui ficam o formulário, o resumo
// e as trilhas calculadas no gráfico.
"use strict";

const av = { info: null, id: null, ultimo: null };

const PARAMS_AV = ["vsh_metodo", "gr_limpo", "gr_argila", "phi_metodo", "rho_matriz", "rho_fluido", "dt_matriz",
                   "dt_fluido", "phi_argila", "sw_metodo", "rw", "rsh", "a", "m", "n", "corte_vsh", "corte_phi",
                   "corte_sw", "qc_cali_pol", "qc_drho", "bs_pol", "passo"];
const NOMES_PAPEL = { GR: "GR", RHOB: "RHOB", NPHI: "NPHI", DT: "DT", RT: "Rt", CALI: "Cáliper", BS: "Broca", DRHO: "DRHO" };

// Trilhas calculadas: escala, cor e posição (depois das trilhas medidas).
const FAMILIAS_AV = {
  AV_VSH: { nome: "Volume de argila", escala: [0, 1], cor: "#7a4a1f", trilha: 6 },
  AV_PHI: { nome: "Porosidade", escala: [0.5, 0], cor: "#2f6fa3", trilha: 7 },
  AV_SW: { nome: "Saturação de água", escala: [1, 0], cor: "#0e5a62", trilha: 8 },
  AV_RES: { nome: "Reservatório", escala: [0, 1], cor: "#d9b44a", trilha: 8.5, faixa: 0 },
  AV_PAY: { nome: "Net pay", escala: [0, 1], cor: "#2f7d4f", trilha: 8.5, faixa: 1 },
  AV_QC: { nome: "Qualidade suspeita", escala: [0, 1], cor: "#a3342b", trilha: 8.5, faixa: 2 },
};

function textoParam(v) { return v === null || v === undefined ? "" : String(v).replace(".", ","); }

async function carregarAvaliacao() {
  if (!pf.rel) return;
  const r = await chamar(null, "avaliacao_info", pf.rel);
  if (!r.ok) return;
  av.info = r;
  av.id = null;
  desenharIntervalosAv();
  desenharCurvasAv();
  if (r.ultima) preencherParametros(r.ultima.parametros, r.ultima.parametros_automaticos || {});
  else preencherParametros(r.padrao);
  limpar($("av-resultado"));
  $("av-acoes").hidden = true;
  desenharHistoricoAv();
  if (r.ultima) mostrarResultadoAv({ id: r.ultima.id, intervalos: r.ultima.intervalos,
                                     automaticos: r.ultima.parametros_automaticos,
                                     registro: `execucoes/${r.ultima.id}.json` }, true);
}

function caixaIntervalo(f, marcado) {
  const l = el("label", "opcao");
  const cb = el("input");
  cb.type = "checkbox";
  cb.checked = marcado;
  cb.value = f.id;
  cb.className = "av-int";
  l.append(cb, document.createTextNode(` ${f.nome || "sem nome"} · ${numero(f.prof_topo, 1)}–${numero(f.prof_base, 1)} m`));
  return l;
}

function desenharIntervalosAv() {
  const box = limpar($("av-intervalos"));
  const ints = av.info ? av.info.intervalos : [];
  const doAgp = av.info ? (av.info.intervalos_agp || []) : [];
  if (!ints.length) {
    box.appendChild(el("p", "ajuda", doAgp.length
      ? "Nenhum intervalo marcado por você. Use uma unidade do AGP abaixo ou arraste sobre o gráfico."
      : "Nenhum intervalo-alvo neste poço. Arraste na vertical sobre o gráfico e salve como “Intervalo-alvo”."));
  }
  for (const f of ints) box.appendChild(caixaIntervalo(f, true));
  if (doAgp.length) {
    const t = el("p", "ajuda av-sub", "Do AGP (topos interpretados pela operadora):");
    box.appendChild(t);
    for (const f of doAgp) box.appendChild(caixaIntervalo(f, false));
  }
  desenharLamaAv();
}

// Referência para o Rw: o que o AGP registra da lama de cada corrida (°F).
function desenharLamaAv() {
  const p = $("av-lama");
  if (!p) return;
  const cs = (av.info && av.info.lama_agp) || [];
  const ts = (av.info && av.info.temperaturas_agp) || [];
  if (!cs.length && !ts.length) { p.hidden = true; return; }
  const partes = cs.map((c) => [`corrida ${c.corrida || "?"}`,
    c.rm != null ? `Rm ${numero(c.rm, 3)} a ${numero(c.t_rm, 1)} °F` : "",
    c.rmf != null ? `Rmf ${numero(c.rmf, 3)} a ${numero(c.t_rmf, 1)} °F` : "",
    c.bht != null ? `BHT ${numero(c.bht, 0)} °F` : "",
    c.prof_alcancada != null ? `até ${numero(c.prof_alcancada, 0)} m` : ""].filter(Boolean).join(", "));
  for (const t of ts) partes.push(`gradiente ${numero(t.gradiente_f_m, 3)} °F/m (corrida ${t.corrida})`);
  p.textContent = "No AGP: " + partes.join(" · ") + ". Referência para escolher o Rw — o SIAPP não converte.";
  p.hidden = false;
}

async function atualizarIntervalosAv() {
  if (!pf.rel || !av.info) return;
  const r = await chamar(null, "avaliacao_info", pf.rel);
  if (r.ok) { av.info.intervalos = r.intervalos; desenharIntervalosAv(); }
}

function desenharCurvasAv() {
  const box = limpar($("av-curvas"));
  for (const [papel, d] of Object.entries(av.info.papeis)) {
    const rot = el("span", d.obrigatorio ? "obrig" : "", NOMES_PAPEL[papel] || papel);
    rot.title = d.obrigatorio ? "obrigatória" : "opcional";
    const sel = el("select");
    sel.dataset.papel = papel;
    sel.className = "av-curva";
    if (!d.obrigatorio || !d.opcoes.length) sel.appendChild(new Option(d.opcoes.length ? "— não usar —" : "— não há no arquivo —", ""));
    for (const o of d.opcoes) {
      const op = new Option(`${o.mnemonico} (${o.unidade || "—"}) · ${o.quadro}`, JSON.stringify(o));
      if (d.padrao && d.padrao.quadro === o.quadro && d.padrao.mnemonico === o.mnemonico) op.selected = true;
      sel.appendChild(op);
    }
    box.append(rot, sel);
  }
}

// Parâmetros estimados pelo motor (GR limpo, Rsh…) voltam como "auto: valor" no
// placeholder, não como valor fixo: mudando o intervalo, são estimados de novo.
function preencherParametros(p, automaticos = {}) {
  for (const k of PARAMS_AV) {
    const campo = $("av-" + k);
    if (!campo) continue;
    const auto = k in automaticos;
    if (campo.dataset.ph === undefined) campo.dataset.ph = campo.placeholder || "";
    campo.placeholder = campo.dataset.ph;
    if (campo.tagName === "SELECT") {
      campo.value = auto ? "auto" : (p[k] || campo.options[0].value);
      if (!campo.value) campo.value = campo.options[0].value;
    } else if (auto) {
      campo.value = "";
      campo.placeholder = `auto: ${textoParam(p[k])}`;
    } else {
      campo.value = textoParam(p[k]);
    }
  }
}

function lerParametros() {
  const p = {};
  for (const k of PARAMS_AV) {
    const campo = $("av-" + k);
    if (!campo) continue;
    const v = campo.value.trim();
    p[k] = v === "" ? null : (campo.tagName === "SELECT" ? v : v.replace(",", "."));
  }
  return p;
}

async function calcularAvaliacao() {
  const curvas = {};
  for (const s of document.querySelectorAll(".av-curva")) if (s.value) curvas[s.dataset.papel] = JSON.parse(s.value);
  const ints = [...document.querySelectorAll(".av-int:checked")].map((c) => c.value);
  const r = await chamar($("av-calcular"), "avaliar_formacao", pf.rel, curvas, ints, lerParametros());
  if (!r.ok) return;
  mostrarResultadoAv(r);
  preencherParametros(r.parametros, r.automaticos || {});   // mostra os automáticos que o motor escolheu
  const pay = r.intervalos.reduce((t, i) => t + i.net_pay_m, 0);
  status(`Avaliação calculada: net pay ${numero(pay, 1)} m em ${r.intervalos.length} intervalo(s). Registro em ${r.registro}.`, "ok");
  const h = await chamar(null, "avaliacao_info", pf.rel);
  if (h.ok) { av.info.historico = h.historico; desenharHistoricoAv(); }
}

function mostrarResultadoAv(r, anterior = false) {
  av.id = r.id;
  av.ultimo = r;
  const box = limpar($("av-resultado"));
  if (anterior) box.appendChild(el("p", "ajuda", `Última avaliação deste arquivo (${r.id.split("_").slice(-1)[0]}):`));
  const t = el("table");
  const cab = el("tr");
  for (const h of ["Intervalo", "Bruto (m)", "Reserv. (m)", "Net pay (m)", "N/G", "φ pay", "Sw pay", "Vsh médio", "HPV (m)", "QC (m)"]) cab.appendChild(el("th", "", h));
  const thead = el("thead");
  thead.appendChild(cab);
  t.appendChild(thead);
  const tb = el("tbody");
  for (const i of r.intervalos) {
    const tr = el("tr");
    const nome = el("td", "", `${i.nome || "—"} (${numero(i.topo, 1)}–${numero(i.base, 1)})`);
    const celulas = [nome, el("td", "", numero(i.bruto_m, 1)), el("td", "", numero(i.reservatorio_m, 1)),
      el("td", "destaque", numero(i.net_pay_m, 1)), el("td", "", i.ntg === null ? "—" : numero(i.ntg, 2)),
      el("td", "", numero(i.phi_media_pay, 3)), el("td", "", numero(i.sw_media_pay, 2)),
      el("td", "", numero(i.vsh_medio, 2)), el("td", "", numero(i.hpv_m, 2)),
      el("td", "", numero(i.qc_arrombado_m + i.qc_drho_m, 1))];
    celulas[9].title = `arrombado: ${numero(i.qc_arrombado_m, 1)} m · DRHO alto: ${numero(i.qc_drho_m, 1)} m · ` +
                       `net pay com QC suspeito: ${numero(i.pay_com_qc_m, 1)} m`;
    if (i.com_dados_m < i.bruto_m - 0.5) nome.title = `Só ${numero(i.com_dados_m, 1)} m do intervalo têm todas as curvas.`;
    tr.append(...celulas);
    tb.appendChild(tr);
  }
  t.appendChild(tb);
  box.appendChild(t);
  const auto = Object.entries(r.automaticos || {});
  if (auto.length) {
    const p = el("p", "ajuda av-auto", "Estimado automaticamente: ");
    p.append(auto.map(([k, v]) => `${k} (${v})`).join("; "));
    box.appendChild(p);
  }
  $("av-acoes").hidden = false;
  $("av-registro").textContent = `Registro: ${r.registro}`;
  if ($("av-mostrar").checked) atualizarGrafico();
}

function desenharHistoricoAv() {
  const h = (av.info && av.info.historico) || [];
  $("av-historico").hidden = !h.length;
  const ul = limpar($("av-hist-lista"));
  for (const x of h) {
    const li = el("li");
    const pay = x.intervalos.reduce((t, i) => t + i.net_pay_m, 0);
    li.appendChild(el("span", "", `${dataCurta(x.criado_em)} · ${NOMES_METODO_AV(x.metodos)} · net pay ${numero(pay, 1)} m`));
    li.title = "Clique para ver no gráfico e retomar os parâmetros";
    li.onclick = () => {
      mostrarResultadoAv({ id: x.id, intervalos: x.intervalos, automaticos: x.parametros_automaticos,
                           registro: `execucoes/${x.id}.json` });
      preencherParametros(x.parametros, x.parametros_automaticos || {});
    };
    ul.appendChild(li);
  }
}

function NOMES_METODO_AV(m) {
  const n = (av.info && av.info.nomes) || {};
  return [n[m.vsh] || m.vsh, n[m.phi] || m.phi, n[m.sw] || m.sw].join(" / ");
}

async function curvasAvaliacaoGrafico() {
  if (!av.id || !$("av-mostrar").checked) return [];
  const r = await chamar(null, "grafico_avaliacao", av.id, pf.topo, pf.base);
  return r.ok ? r.curvas : [];
}

async function exportarAvaliacao(formato, botao) {
  if (!av.id) return;
  const r = await chamar(botao, "exportar_avaliacao", av.id, formato);
  if (r.ok) status(`Avaliação exportada: ${r.arquivo} (${numero(r.amostras, 0)} profundidades).`, "ok");
}

function ligarAvaliacao() {
  ligar("av-calcular", "onclick", calcularAvaliacao);
  ligar("av-padrao", "onclick", () => av.info && preencherParametros(av.info.padrao));
  ligar("av-mostrar", "onchange", () => atualizarGrafico());
  ligar("av-csv", "onclick", () => exportarAvaliacao("csv", $("av-csv")));
  ligar("av-las", "onclick", () => exportarAvaliacao("las", $("av-las")));
}
