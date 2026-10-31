// SIAPP — dados do poço lidos dos formulários da ANP (RFP, RFCP, Perfuração), na ficha do poço.
// Os números vêm como o formulário traz (profundidade medida em m, °F, kgf/cm²); as conversões
// mostradas ao lado (°C, psi) são só para leitura.

const KGF_PSI = 14.2233;

function fCelsius(f) { return f == null ? null : (f - 32) * 5 / 9; }

function tabelaSimples(cabecalho, linhas, classe = "") {
  const t = el("table", "tabela dp-tabela " + classe);
  const tr = el("tr");
  for (const h of cabecalho) tr.appendChild(el("th", "", h));
  t.appendChild(tr);
  for (const ln of linhas) {
    const r = el("tr");
    for (const c of ln) r.appendChild(el("td", "", c == null || c === "" ? "—" : String(c)));
    t.appendChild(r);
  }
  return t;
}

function intervaloM(a, b) {
  if (a == null && b == null) return "—";
  if (b == null || b === a) return numero(a, 1);
  return `${numero(a, 1)}–${numero(b, 1)}`;
}

function blocoDp(corpo, titulo, n, aberto, conteudo) {
  const d = el("details", "dp-bloco");
  d.open = aberto;
  d.appendChild(el("summary", "", n == null ? titulo : `${titulo} (${n})`));
  d.appendChild(conteudo);
  corpo.appendChild(d);
}

function secaoDadosPocoFicha(corpo, dp, id) {
  if (!dp || !dp.documentos || !dp.documentos.length) return;
  const caixa = el("div", "dp-secao");
  caixa.id = "fi-dados-poco";
  corpo.appendChild(caixa);
  desenharDadosPoco(caixa, dp, id);
}

function desenharDadosPoco(caixa, dp, id) {
  limpar(caixa);
  const docs = dp.documentos;
  caixa.appendChild(el("h3", "", "Formulários da ANP, testes e análises de laboratório"));
  const ul = el("ul", "dp-docs");
  for (const d of docs) {                       // já em ordem de prioridade (RFP primeiro)
    const li = el("li");
    const txt = el("div", "dp-doc-txt");
    txt.append(el("strong", "", d.titulo || d.documento || "documento"));
    if (d.erro) txt.append(el("span", "dp-erro", ` — não lido: ${d.erro}`));
    else txt.append(el("span", "ajuda", ` — ${d.n} dado(s)`));
    if (d.confere === 0)
      txt.append(el("div", "agp-aviso", `O formulário é do poço ${d.poco_documento}: não entra nos dados deste.`));
    txt.append(el("div", "dp-arquivo", d.rel.split("/").pop()));
    for (const a of d.avisos || []) txt.append(el("div", "agp-aviso dp-aviso", a));
    li.append(txt, botaoAbrir(d.rel, "documento"));
    ul.appendChild(li);
  }
  caixa.appendChild(ul);

  const g = dp.gerais || {};
  const t = el("table", "tabela ficha");
  linhaFicha(t, "Perfuração", [g.inicio_perfuracao, g.termino_perfuracao].filter(Boolean).join(" → "));
  linhaFicha(t, "Conclusão", g.conclusao);
  linhaFicha(t, "Completação", [g.inicio_completacao, g.termino_completacao].filter(Boolean).join(" → "));
  linhaFicha(t, "Prof. final (sondador)", g.prof_sondador != null ? `${numero(g.prof_sondador, 2)} m` : "");
  linhaFicha(t, "Prof. final (perfil)", g.prof_perfil_medida != null
    ? `${numero(g.prof_perfil_medida, 2)} m` + (g.prof_perfil_cota != null ? ` (cota ${numero(g.prof_perfil_cota, 2)} m)` : "") : "");
  linhaFicha(t, "Unidade na prof. final", g.unidade_prof_final);
  linhaFicha(t, "Mesa rotativa", g.mesa_rotativa != null ? `${numero(g.mesa_rotativa, 2)} m` : "");
  linhaFicha(t, "Elevação do terreno", g.elevacao != null ? `${numero(g.elevacao, 2)} m` : "");
  linhaFicha(t, "Prof. prevista", g.prof_prevista != null ? `${numero(g.prof_prevista, 1)} m` : "");
  linhaFicha(t, "Descobridor de campo", g.descobridor === "S" ? "sim" : g.descobridor === "N" ? "não" : g.descobridor);
  linhaFicha(t, "Fluido descoberto", g.fluido_descoberto);
  linhaFicha(t, "Abandono", [g.tipo_abandono, g.razao_abandono].filter(Boolean).join(" · "));
  linhaFicha(t, "Categoria / tipo", [g.categoria, g.tipo_poco].filter(Boolean).join(" · "));
  linhaFicha(t, "Sonda", [g.sonda, g.sonda_unidade].filter(Boolean).join(" · "));
  linhaFicha(t, "Nome na operadora", g.nome_operador);
  const co = g.coordenadas || {};
  for (const [k, rot] of [["base", "Coord. da base"], ["alvo", "Coord. do alvo"], ["fundo", "Coord. do fundo"]])
    if (co[k]) linhaFicha(t, rot, `${numero(co[k].lat, 6)}, ${numero(co[k].lon, 6)}`);
  caixa.appendChild(t);

  const it = dp.itens || {};
  const topos = it.topo || [];
  const toposCalha = it.topo_calha || [];
  // topo sem nome no formulário: a formação da calha (PAG) mais próxima, até 10 m
  const nomeCalha = (prof) => {
    let m = null;
    for (const t of toposCalha) if (Math.abs(t.prof_topo - prof) <= 10 && (!m || Math.abs(t.prof_topo - prof) < Math.abs(m.prof_topo - prof))) m = t;
    return m ? ` · ≈ ${m.nome} (calha, ${numero(m.prof_topo, 0)} m)` : "";
  };
  if (topos.length) {
    const semNome = topos.every((x) => !x.nome);
    const c = el("div");
    c.appendChild(tabelaSimples(["Unidade", "Prevista (m)", "Constatada (m)", "Cota (m)", "Diferença (m)"],
      topos.map((x) => [x.nome || `topo ${x.extra.ordem}${nomeCalha(x.prof_topo)}`, numero(x.extra.prev_medida, 1), numero(x.prof_topo, 1),
                        numero(x.cota, 1),
                        x.extra.prev_medida != null ? (x.prof_topo - x.extra.prev_medida >= 0 ? "+" : "") +
                          numero(x.prof_topo - x.extra.prev_medida, 1) : ""])));
    if (semNome) c.appendChild(el("p", "ajuda", "Este formulário não traz o nome das unidades, só as profundidades; " +
      (toposCalha.length ? "o nome ao lado é a formação que o geólogo de poço anotou na calha (PAG), quando fica a até 10 m."
        : "compare com os topos do AGP ou de um documento do poço.")));
    blocoDp(caixa, "Topos estratigráficos", topos.length, true, c);
  }

  const pr = dp.pressoes || {};
  if ((pr.pontos || []).length) blocoDp(caixa, "Pressões × profundidade", pr.pontos.length, true, secaoPressoes(pr));
  for (const t of pr.tfr || []) blocoDp(caixa, `Teste de formação ${t.nome || ""} — relatório`, null, true, secaoTfr(t, pr.series || []));
  for (const v of dp.pvt || []) blocoDp(caixa, `Análise PVT — liberação diferencial (${intervaloM(v.amostra.topo, v.amostra.base)} m)`,
                                        null, true, secaoPvt(v));
  for (const c of dp.composicao || []) blocoDp(caixa, `Composição do fluido — liberação flash`, c.componentes.length, false,
                                               secaoComposicao(c));
  secaoPag(caixa, it, topos);
  for (const ck of dp.checkshot || []) blocoDp(caixa, "Sísmica de poço — tempo × profundidade (checkshot)", ck.niveis.length, true,
                                               secaoCheckshot(ck, id));
  secaoGeoquimica(caixa, it);
  secaoPetrofisica(caixa, it);

  const testes = it.teste_formacao || [];
  if (testes.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Tipo", "Prof. (m)", "Fluido", "°API", "Vazão (m³/d)", "Pressão estática"],
      testes.map((x) => [x.nome, intervaloM(x.prof_topo, x.prof_base), x.texto, x.extra.api != null ? numero(x.extra.api, 1) : "",
                         x.extra.vazao_m3_dia != null ? numero(x.extra.vazao_m3_dia, 1) : "",
                         x.valor != null ? `${numero(x.valor, 1)} kgf/cm² (${numero(x.valor * KGF_PSI, 0)} psi)` : ""])));
    c.appendChild(el("p", "ajuda", "Siglas como o formulário traz. Os testes com uma só profundidade (PT, TC, TCA…) são " +
      "medidas pontuais, como as do teste a cabo; o TFR tem intervalo e vazão. 1 kgf/cm² = 14,22 psi."));
    blocoDp(caixa, "Testes de formação", testes.length, true, c);
  }

  const temps = it.temperatura || [];
  if (temps.length) {
    blocoDp(caixa, "Temperaturas", temps.length, true, tabelaSimples(["Temperatura", "Prof. (m)", "Lida ou extrapolada", "Origem"],
      temps.map((x) => [x.unidade === "°F" ? `${numero(x.valor, 1)} °F (${numero(fCelsius(x.valor), 1)} °C)` : `${numero(x.valor, 1)} ${x.unidade || ""}`,
                        numero(x.prof_topo, 1), x.texto, x.nome])));
  }

  const intervalos = [...(it.analise_perfil || []).map((x) => ["análise de perfis", x, x.texto]),
                      ...(it.canhoneado || []).map((x) => ["canhoneado", x, [x.texto, x.valor != null ? `${numero(x.valor, 0)} tiros/pé` : ""].filter(Boolean).join(" · ")])];
  if (intervalos.length) {
    blocoDp(caixa, "Intervalos de interesse", intervalos.length, true, tabelaSimples(["Origem", "Intervalo (m)", "Unidade", "Detalhe"],
      intervalos.map(([o, x, det]) => [o, intervaloM(x.prof_topo, x.prof_base), x.nome, det])));
  }

  const ind = it.indicio || [];
  if (ind.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Intervalo (m)", "Unidade", "Ocorr.", "Fluor.", "Corte", "Gás total"],
      ind.map((x) => [intervaloM(x.prof_topo, x.prof_base), x.nome, x.extra.ocorrencia, x.extra.fluorescencia,
                      x.extra.corte, x.extra.gas_total])));
    c.appendChild(el("p", "ajuda", "Códigos como no formulário (ocorrência C/D, fluorescência e corte)."));
    blocoDp(caixa, "Indícios de petróleo e gás", ind.length, ind.length <= 8, c);
  }

  const fases = it.fase || [];
  if (fases.length) {
    blocoDp(caixa, "Fases da perfuração e fluido", fases.length, false, tabelaSimples(
      ["Fase", "Até (m)", "Revestimento", "Fluido", "Peso (lb/gal)"],
      fases.map((x) => [x.nome, numero(x.prof_base, 1),
                        x.extra.rev_diametro ? `${x.extra.rev_diametro}" até ${numero(x.extra.rev_prof, 1)} m` : "",
                        x.texto, x.valor != null ? numero(x.valor, 2) : ""])));
  }
  const rev = it.revestimento || [];
  if (rev.length) {
    blocoDp(caixa, "Revestimento de produção", rev.length, false, tabelaSimples(["Diâmetro (pol)", "Intervalo (m)", "Peso (lb/pé)", "Grau"],
      rev.map((x) => [x.nome, intervaloM(x.prof_topo, x.prof_base), numero(x.valor, 1), x.texto])));
  }
  const tc = it.teste_completacao || [];
  if (tc.length) {
    blocoDp(caixa, "Teste na completação", tc.length, false, tabelaSimples(["Tipo", "Vazão (m³/d)", "°API", "BSW (%)", "Pressão de fluxo", "Prof. (m)"],
      tc.map((x) => [x.nome, numero(x.valor, 1), numero(x.extra.api, 1), numero(x.extra.bsw_pct, 1),
                     x.extra.pressao_fluxo_kgf_cm2 != null ? `${numero(x.extra.pressao_fluxo_kgf_cm2, 1)} kgf/cm²` : "",
                     numero(x.prof_topo, 1)])));
  }
  const am = [...(it.testemunho || []).map((x) => ["testemunho", x]), ...(it.amostra_lateral || []).map((x) => ["amostra lateral", x])];
  if (am.length) {
    blocoDp(caixa, "Testemunhos e amostras laterais", am.length, false, tabelaSimples(["Tipo", "Prof. (m)", "Unidade", "Litologia"],
      am.map(([tp, x]) => [tp, intervaloM(x.prof_topo, x.prof_base), x.nome, x.texto])));
  }
  const perf = it.perfilagem || [];
  if (perf.length) {
    const ord = [...perf].sort((a, b) => String(a.extra.data || "").split("/").reverse().join("")
      .localeCompare(String(b.extra.data || "").split("/").reverse().join("")) || (a.extra.n - b.extra.n));
    blocoDp(caixa, "Perfilagens realizadas", perf.length, false, tabelaSimples(["Data", "Tipo", "Perfis", "Intervalo (m)", "Companhia"],
      ord.map((x) => [x.extra.data, x.extra.tipo, x.nome, intervaloM(x.prof_topo, x.prof_base), x.texto])));
  }
  const calha = it.calha || [];
  if (calha.length) {
    blocoDp(caixa, "Amostragem de calha", calha.length, false, tabelaSimples(["Intervalo (m)", "Padrão"],
      calha.map((x) => [intervaloM(x.prof_topo, x.prof_base), x.texto])));
  }
  for (const d of docs) {
    const campos = d.campos || {};
    const rotulos = { data_descoberta: "Data da descoberta", fluidos: "Fluido(s)", reentrada: "Reentrada nº",
                      inicio: "Início", fim: "Fim", prof_final: "Profundidade final (m)", sonda: "Sonda",
                      estado_atual: "Estado atual", conclusao_perfilagem: "Conclusão da perfilagem final" };
    const linhas = Object.entries(rotulos).filter(([k]) => campos[k] != null && campos[k] !== "");
    if (linhas.length || (d.secoes_texto || []).length) {
      const c = el("div");
      if (linhas.length) {
        const t2 = el("table", "tabela ficha");
        for (const [k, rot] of linhas) linhaFicha(t2, rot, k === "prof_final" ? numero(campos[k], 2) : campos[k]);
        c.appendChild(t2);
      }
      for (const sx of d.secoes_texto || []) {
        c.appendChild(el("p", "dp-sub", sx.titulo));
        c.appendChild(el("p", "dp-obs", sx.texto));
      }
      const titulo = d.documento === "reentrada" && campos.reentrada ? `${d.titulo} ${campos.reentrada}` : d.titulo;
      blocoDp(caixa, titulo || d.documento, null, false, c);
    }
    if (d.observacoes) {
      const p = el("p", "dp-obs", d.observacoes);
      blocoDp(caixa, `Observações — ${d.titulo || d.documento}`, null, false, p);
    }
  }
  const b = el("button", "btn secundario pequeno", "Ler os formulários de novo");
  b.onclick = async () => {
    const r = await chamar(b, "reler_dados_poco", id);
    if (!r.ok) return;
    status(`${r.lidos} formulário(s) lido(s) de novo, ${r.itens} dado(s)` +
      (r.erros.length ? `; ${r.erros.length} sem leitura.` : "."), r.erros.length ? "erro" : "ok");
    desenharDadosPoco(caixa, r.dados_poco, id);
  };
  caixa.appendChild(b);
}


// ------------------------------------------------ pressões × profundidade e gradiente
const COR_ORIGEM = { "teste a cabo": "#2a78d6", TFR: "#c0392b" };

function svgEl(tag, attrs) {
  const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  return e;
}

function escalaLinear(d0, d1, r0, r1) {
  const f = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v) => r0 + (v - d0) * f;
}

function graficoPressoes(svg, pontos, retas) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const W = 440, H = 300, m = { e: 54, d: 12, t: 12, b: 34 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const ps = pontos.flatMap((p) => [p.pressao_kgf_cm2, p.hidrostatica_kgf_cm2]).filter((v) => v != null);
  const zs = pontos.map((p) => p.prof).filter((v) => v != null);
  if (!ps.length || !zs.length) return;
  let [p0, p1] = [Math.min(...ps), Math.max(...ps)];
  let [z0, z1] = [Math.min(...zs), Math.max(...zs)];
  const fp = Math.max(1, (p1 - p0) * 0.08), fz = Math.max(2, (z1 - z0) * 0.08);
  p0 -= fp; p1 += fp; z0 -= fz; z1 += fz;
  const x = escalaLinear(p0, p1, m.e, W - m.d), y = escalaLinear(z0, z1, m.t, H - m.b);
  const g = svgEl("g", { class: "dp-graf" });
  g.appendChild(svgEl("rect", { x: m.e, y: m.t, width: W - m.e - m.d, height: H - m.t - m.b, class: "dp-graf-area" }));
  for (let k = 0; k <= 4; k++) {
    const pv = p0 + (p1 - p0) * k / 4, zv = z0 + (z1 - z0) * k / 4;
    const tx = svgEl("text", { x: x(pv), y: H - m.b + 14, "text-anchor": "middle", class: "dp-graf-txt" });
    tx.textContent = numero(pv, 0); g.appendChild(tx);
    const ty = svgEl("text", { x: m.e - 4, y: y(zv) + 3, "text-anchor": "end", class: "dp-graf-txt" });
    ty.textContent = numero(zv, 0); g.appendChild(ty);
  }
  const rx = svgEl("text", { x: (m.e + W - m.d) / 2, y: H - 4, "text-anchor": "middle", class: "dp-graf-txt" });
  rx.textContent = "pressão (kgf/cm²)"; g.appendChild(rx);
  const ry = svgEl("text", { x: 10, y: (m.t + H - m.b) / 2, transform: `rotate(-90 10 ${(m.t + H - m.b) / 2})`,
                              "text-anchor": "middle", class: "dp-graf-txt" });
  ry.textContent = "profundidade medida (m)"; g.appendChild(ry);
  for (const r of retas || []) {
    const zA = z0, zB = z1;
    const pa = r.gradiente_kgf_cm2_m * zA + r.intercepto_kgf_cm2, pb = r.gradiente_kgf_cm2_m * zB + r.intercepto_kgf_cm2;
    g.appendChild(svgEl("line", { x1: x(pa), y1: y(zA), x2: x(pb), y2: y(zB), class: `dp-reta dp-reta-${r.grupo}` }));
  }
  if (retas && retas.contato != null) {
    g.appendChild(svgEl("line", { x1: m.e, y1: y(retas.contato), x2: W - m.d, y2: y(retas.contato), class: "dp-contato" }));
  }
  for (const p of pontos) {
    if (p.hidrostatica_kgf_cm2 != null)
      g.appendChild(svgEl("circle", { cx: x(p.hidrostatica_kgf_cm2), cy: y(p.prof), r: 3, class: "dp-pt-lama" }));
  }
  for (const p of pontos) {
    if (p.pressao_kgf_cm2 == null) continue;
    const cor = COR_ORIGEM[p.origem] || "#d68a1a";
    const c = svgEl(p.origem === "teste a cabo" ? "circle" : "rect", p.origem === "teste a cabo"
      ? { cx: x(p.pressao_kgf_cm2), cy: y(p.prof), r: 3.5, fill: cor }
      : { x: x(p.pressao_kgf_cm2) - 3, y: y(p.prof) - 3, width: 6, height: 6, fill: "none", stroke: cor, "stroke-width": 1.5 });
    const tt = svgEl("title"); tt.textContent = `${p.rotulo} · ${numero(p.prof, 1)} m · ${numero(p.pressao_kgf_cm2, 2)} kgf/cm²`;
    c.appendChild(tt); g.appendChild(c);
  }
  svg.appendChild(g);
}

function secaoPressoes(pr) {
  const c = el("div", "dp-pressoes");
  const svg = svgEl("svg", { class: "dp-svg", role: "img", "aria-label": "Pressão versus profundidade" });
  c.appendChild(svg);
  const leg = el("p", "ajuda dp-legenda");
  leg.innerHTML = '<span class="dp-lg" style="background:#2a78d6"></span> teste a cabo (lido do DLIS) · ' +
    '<span class="dp-lg dp-lg-q" style="border-color:#d68a1a"></span> formulários (RFP…) · ' +
    '<span class="dp-lg dp-lg-q" style="border-color:#c0392b"></span> TFR (estática extrapolada) · ' +
    '<span class="dp-lg dp-lg-lama"></span> lama (hidrostática)';
  c.appendChild(leg);
  if ((pr.lama || []).length)
    c.appendChild(el("p", "ajuda", "Lama na perfilagem: " + pr.lama.map((l) => `${numero(l.peso_lb_gal, 1)} lb/gal` +
      (l.tipo ? ` (${l.tipo.toLowerCase()})` : "")).join(" · ") + "."));
  const t = el("table", "tabela dp-tabela dp-tab-pressoes");
  const cab = el("tr");
  for (const h of ["Grupo", "Prof. (m)", "Pressão (kgf/cm²)", "Lama", "Origem", "Qualidade", ""]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const p of pr.pontos) {
    const tr = el("tr");
    const sel = el("select", "dp-grupo");
    for (const o of ["—", "A", "B"]) sel.appendChild(new Option(o, o === "—" ? "" : o));
    sel.dataset.id = p.id;
    const tdSel = el("td"); tdSel.appendChild(sel);
    const q = el("td", "", p.qualidade || "—");
    if (p.anterior_kgf_cm2 != null) q.title = `patamar anterior: ${numero(p.anterior_kgf_cm2, 2)} kgf/cm²`;
    if (p.inclinacao_psi_min != null) q.title = (q.title ? q.title + " · " : "") + `fim do patamar: ${numero(p.inclinacao_psi_min, 2)} psi/min`;
    const tdP = el("td", "", numero(p.pressao_kgf_cm2, 2));
    if (p.pressao_kgf_cm2 != null) tdP.title = `${numero(p.pressao_kgf_cm2 * KGF_PSI, 0)} psi`;
    const tdO = el("td", "", p.origem);
    tdO.title = p.rotulo || "";
    tr.append(tdSel, el("td", "", numero(p.prof, 2)), tdP,
              el("td", "", p.hidrostatica_kgf_cm2 != null ? numero(p.hidrostatica_kgf_cm2, 1) : "—"), tdO, q);
    const tdB = el("td");
    if (p.serie) {
      const b = el("button", "btn secundario pequeno", "curva");
      b.onclick = () => mostrarSerie(c, p.serie.rel, p.serie.qual);
      tdB.appendChild(b);
    }
    tr.appendChild(tdB);
    t.appendChild(tr);
  }
  c.appendChild(t);
  const linha = el("div", "linha dp-grad-acoes");
  const bg = el("button", "btn secundario pequeno", "Calcular gradiente");
  const res = el("div", "dp-grad-res");
  bg.onclick = async () => {
    const grupos = { A: [], B: [] };
    for (const s of t.querySelectorAll(".dp-grupo")) {
      if (!s.value) continue;
      const p = pr.pontos.find((x) => x.id === s.dataset.id);
      if (p && p.pressao_kgf_cm2 != null) grupos[s.value].push([p.prof, p.pressao_kgf_cm2]);
    }
    const r = await chamar(bg, "gradiente_pressoes", grupos);
    limpar(res);
    if (!r.ok) return;
    const retas = [];
    for (const k of ["A", "B"]) {
      const gr = r[k];
      if (!gr) continue;
      retas.push({ ...gr, grupo: k });
      res.appendChild(el("p", "", `Grupo ${k}: ${numero(gr.gradiente_kgf_cm2_m, 4)} kgf/cm²/m = ${numero(gr.gradiente_psi_ft, 3)} psi/ft → ` +
        `densidade ${numero(gr.densidade_g_cm3, 3)} g/cm³, compatível com ${gr.fluido_compativel} ` +
        `(${gr.n} pontos, ${numero(gr.topo, 1)}–${numero(gr.base, 1)} m, R² ${numero(gr.r2, 4)})`));
    }
    if (r.contato != null) {
      retas.contato = r.contato;
      res.appendChild(el("p", "dp-contato-txt", `As duas retas se cruzam a ${numero(r.contato, 1)} m — contato provável entre os fluidos dos grupos A e B.`));
    }
    graficoPressoes(svg, pr.pontos, retas);
  };
  linha.append(bg, el("span", "ajuda", "Marque A (e B) nos pontos de cada fluido: o SIAPP ajusta a reta, dá a densidade e, com dois grupos, a profundidade do contato."));
  c.append(linha, res);
  graficoPressoes(svg, pr.pontos, []);
  return c;
}

function graficoSerie(svg, s) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const W = 440, H = 200, m = { e: 50, d: 10, t: 10, b: 30 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const ys = s.y.filter((v) => v != null);
  if (!ys.length) return;
  const x = escalaLinear(Math.min(...s.x), Math.max(...s.x), m.e, W - m.d);
  const y = escalaLinear(Math.min(...ys), Math.max(...ys), H - m.b, m.t);
  const g = svgEl("g", { class: "dp-graf" });
  g.appendChild(svgEl("rect", { x: m.e, y: m.t, width: W - m.e - m.d, height: H - m.t - m.b, class: "dp-graf-area" }));
  const pts = s.x.map((xv, i) => s.y[i] == null ? null : `${x(xv).toFixed(1)},${y(s.y[i]).toFixed(1)}`).filter(Boolean).join(" ");
  g.appendChild(svgEl("polyline", { points: pts, class: "dp-serie" }));
  for (const [k, v] of Object.entries(s.linhas || {})) {
    if (v == null) continue;
    const ln = svgEl("line", { x1: m.e, x2: W - m.d, y1: y(v), y2: y(v), class: k.startsWith("hidro") ? "dp-linha-lama" : "dp-linha-p" });
    g.appendChild(ln);
  }
  for (let k = 0; k <= 3; k++) {
    const yv = Math.min(...ys) + (Math.max(...ys) - Math.min(...ys)) * k / 3;
    const t = svgEl("text", { x: m.e - 4, y: y(yv) + 3, "text-anchor": "end", class: "dp-graf-txt" }); t.textContent = numero(yv, 1); g.appendChild(t);
    const xv = Math.min(...s.x) + (Math.max(...s.x) - Math.min(...s.x)) * k / 3;
    const amp = Math.max(...s.x) - Math.min(...s.x);
    const t2 = svgEl("text", { x: x(xv), y: H - m.b + 13, "text-anchor": "middle", class: "dp-graf-txt" });
    t2.textContent = numero(xv, amp < 3 ? 2 : amp < 30 ? 1 : 0); g.appendChild(t2);
  }
  const rx = svgEl("text", { x: (m.e + W) / 2, y: H - 3, "text-anchor": "middle", class: "dp-graf-txt" });
  rx.textContent = `${s.x_rotulo} · ${s.y_rotulo}`; g.appendChild(rx);
  svg.appendChild(g);
}

async function mostrarSerie(caixa, rel, qual) {
  let box = caixa.querySelector(".dp-serie-box");
  if (!box) { box = el("div", "dp-serie-box"); caixa.appendChild(box); }
  limpar(box);
  const r = await chamar(null, "serie_pressao", rel, qual);
  if (!r.ok) return;
  box.appendChild(el("p", "dp-sub", r.titulo));
  const svg = svgEl("svg", { class: "dp-svg dp-svg-serie", role: "img", "aria-label": r.titulo });
  box.appendChild(svg);
  graficoSerie(svg, r);
  box.scrollIntoView({ block: "nearest" });
}

function secaoTfr(t, series) {
  const c = el("div", "dp-tfr");
  const tb = el("table", "tabela ficha");
  const n = (v, cs, u) => v == null ? "" : `${numero(v, cs)}${u ? " " + u : ""}`;
  linhaFicha(tb, "Intervalo", t.topo != null ? `${intervaloM(t.topo, t.base)} m` + (t.formacao ? ` · ${t.formacao}` : "") : "");
  linhaFicha(tb, "Período", [t.inicio, t.fim].filter(Boolean).join(" → "));
  linhaFicha(tb, "Pressão estática (extrapolada)", t.pressao_estatica_kgf_cm2 != null
    ? `${numero(t.pressao_estatica_kgf_cm2, 2)} kgf/cm² (${numero(t.pressao_estatica_kgf_cm2 * KGF_PSI, 0)} psi) a ${numero(t.prof_referencia || t.prof_registro_medida, 2)} m` : "");
  linhaFicha(tb, "Pressão de fluxo final", n(t.pressao_fluxo_kgf_cm2, 1, "kgf/cm²"));
  linhaFicha(tb, "Vazão", n(t.vazao_m3_dia, 1, "m³/d"));
  linhaFicha(tb, "Fluido · °API", [t.fluido_desc, t.api != null ? `${numero(t.api, 1)} °API` : ""].filter(Boolean).join(" · "));
  linhaFicha(tb, "Permeabilidade efetiva", n(t.permeabilidade_md, 0, "mD"));
  linhaFicha(tb, "Transmissibilidade (kh/μ)", n(t.transmissibilidade, 1, "mD·m/cP"));
  linhaFicha(tb, "Mobilidade (k/μ)", n(t.mobilidade, 1, "mD/cP"));
  linhaFicha(tb, "Efeito de película (skin)", n(t.skin, 1));
  linhaFicha(tb, "Índice de produtividade", n(t.ip, 2, "m³/d/(kgf/cm²)"));
  linhaFicha(tb, "Raio de investigação", n(t.raio_investigacao_m, 0, "m"));
  linhaFicha(tb, "Temperatura máxima", t.temp_max_c != null ? `${numero(t.temp_max_c, 1)} °C` : "");
  linhaFicha(tb, "Espessura · φ · Sw adotadas", [n(t.espessura_m, 1, "m"), n(t.porosidade_pct, 1, "%"), n(t.sw_pct, 1, "%")].filter(Boolean).join(" · "));
  linhaFicha(tb, "Modelo", [t.modelo, t.limites].filter(Boolean).join(" "));
  c.appendChild(tb);
  if (t.conclusao) { c.appendChild(el("p", "dp-sub", "Conclusão do intérprete")); c.appendChild(el("p", "dp-obs", t.conclusao)); }
  if ((t.fluxos || []).length) {
    c.appendChild(tabelaSimples(["Período", "Duração", "Fluido", "Abertura (1/64\")", "Vazão (m³/d)", "RGO (m³/m³)", "P. fluxo final"],
      t.fluxos.map((f) => [f.periodo, f.duracao, f.fluido, f.abertura_64 != null ? numero(f.abertura_64, 0) : "",
                           numero(f.vazao_liquido_m3_dia, 1), numero(f.rgo_m3_m3, 1), numero(f.pressao_fluxo_kgf_cm2, 1)])));
  }
  const minhas = series.filter((s) => s.rel === t.rel);
  if (minhas.length) {
    const linha = el("div", "linha dp-series");
    linha.appendChild(el("span", "ajuda", "Registros dos manômetros:"));
    for (const s of minhas) {
      const b = el("button", "btn secundario pequeno", s.rotulo + (s.interpretacao ? " (usado na interpretação)" : ""));
      b.onclick = () => mostrarSerie(c, s.rel, s.qual);
      linha.appendChild(b);
    }
    c.appendChild(linha);
  }
  if ((t.outros_arquivos || []).length)
    c.appendChild(el("p", "ajuda", `Também no ZIP: ${t.outros_arquivos.map((o) => o.arquivo.split("/").pop()).join(", ")}.`));
  return c;
}


// ------------------------------------------------ PVT
function graficoXY(svg, xs, ys, xRot, yRot, marcaX, inverterY = false) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const W = 220, H = 170, m = { e: 44, d: 8, t: 8, b: 30 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const pts = xs.map((x, i) => [x, ys[i]]).filter(([x, y]) => x != null && y != null);
  if (pts.length < 2) return;
  const vx = pts.map((p) => p[0]), vy = pts.map((p) => p[1]);
  const x = escalaLinear(Math.min(...vx), Math.max(...vx), m.e, W - m.d);
  // inverterY: profundidade crescendo para baixo
  const y = inverterY ? escalaLinear(Math.min(...vy), Math.max(...vy), m.t, H - m.b)
    : escalaLinear(Math.min(...vy), Math.max(...vy), H - m.b, m.t);
  const g = svgEl("g", { class: "dp-graf" });
  g.appendChild(svgEl("rect", { x: m.e, y: m.t, width: W - m.e - m.d, height: H - m.t - m.b, class: "dp-graf-area" }));
  if (marcaX != null) g.appendChild(svgEl("line", { x1: x(marcaX), x2: x(marcaX), y1: m.t, y2: H - m.b, class: "dp-linha-p" }));
  pts.sort((a, b) => (inverterY ? a[1] - b[1] : a[0] - b[0]));     // perfil em profundidade: na ordem da profundidade
  g.appendChild(svgEl("polyline", { points: pts.map(([a, b]) => `${x(a).toFixed(1)},${y(b).toFixed(1)}`).join(" "), class: "dp-serie" }));
  for (const [a, b] of pts) g.appendChild(svgEl("circle", { cx: x(a), cy: y(b), r: 2, fill: "#2a78d6" }));
  const amp = Math.max(...vy) - Math.min(...vy);
  for (let k = 0; k <= 2; k++) {
    const yv = Math.min(...vy) + amp * k / 2, xv = Math.min(...vx) + (Math.max(...vx) - Math.min(...vx)) * k / 2;
    const t = svgEl("text", { x: m.e - 3, y: y(yv) + 3, "text-anchor": "end", class: "dp-graf-txt" });
    t.textContent = numero(yv, amp < 1 ? 3 : 1); g.appendChild(t);
    const t2 = svgEl("text", { x: x(xv), y: H - m.b + 12, "text-anchor": "middle", class: "dp-graf-txt" });
    t2.textContent = numero(xv, 0); g.appendChild(t2);
  }
  const r = svgEl("text", { x: (m.e + W) / 2, y: H - 3, "text-anchor": "middle", class: "dp-graf-txt" });
  r.textContent = `${yRot} × ${xRot}`; g.appendChild(r);
  svg.appendChild(g);
}

function secaoPvt(v) {
  const c = el("div", "dp-pvt");
  const a = v.amostra || {}, s = v.saturacao || {};
  const t = el("table", "tabela ficha");
  linhaFicha(t, "Amostra", [a.amostragem, a.fluido && a.fluido.toLowerCase(), a.temp_c != null ? `${numero(a.temp_c, 1)} °C` : ""].filter(Boolean).join(" · "));
  linhaFicha(t, "Pressão de saturação", s.p_kgf_cm2 != null ? `${numero(s.p_kgf_cm2, 1)} kgf/cm² (${numero(s.p_bar, 1)} bar, ${numero(s.p_kgf_cm2 * KGF_PSI, 0)} psi)` : "");
  linhaFicha(t, "Na saturação", [s.bo != null ? `Bo ${numero(s.bo, 4)}` : "", s.rs != null ? `Rs ${numero(s.rs, 2)} m³/m³` : "",
                                 s.mu_o_cp != null ? `μo ${numero(s.mu_o_cp, 2)} cP` : "", s.rho_o_g_cm3 != null ? `ρo ${numero(s.rho_o_g_cm3, 4)} g/cm³` : ""].filter(Boolean).join(" · "));
  linhaFicha(t, "Compressibilidade do óleo", s.co_por_kgf_cm2 != null ? `${numero(s.co_por_kgf_cm2 * 1e6, 0)} × 10⁻⁶ (kgf/cm²)⁻¹ (acima da saturação)` : "");
  linhaFicha(t, "Tanque", [a.api_tanque != null ? `${numero(a.api_tanque, 2)} °API` : "", a.rgo_tanque != null ? `RGO ${numero(a.rgo_tanque, 2)} m³/m³` : "",
                           a.dg_tanque != null ? `gás ${numero(a.dg_tanque, 4)} (ar = 1)` : ""].filter(Boolean).join(" · "));
  linhaFicha(t, "Gás da liberação diferencial", a.dg_lib_dif != null ? `${numero(a.dg_lib_dif, 3)} (ar = 1)` : "");
  c.appendChild(t);
  const graf = el("div", "dp-pvt-graf");
  const tab = v.tabela || [];
  const ps = tab.map((r) => r.p_kgf_cm2);
  for (const [k, rot] of [["bo", "Bo (m³/m³)"], ["rs", "Rs (m³/m³)"], ["mu_o_cp", "μo (cP)"]]) {
    const svg = svgEl("svg", { class: "dp-svg dp-svg-pvt", role: "img", "aria-label": rot });
    graficoXY(svg, ps, tab.map((r) => r[k]), "p (kgf/cm²)", rot, s.p_kgf_cm2);
    graf.appendChild(svg);
  }
  c.appendChild(graf);
  c.appendChild(tabelaSimples(["p (kgf/cm²)", "Bo", "Rs", "Visc. óleo (cP)", "Massa esp. (g/cm³)", "Bg", "Z"],
    tab.map((r) => [numero(r.p_kgf_cm2, 1), numero(r.bo, 4), numero(r.rs, 2), numero(r.mu_o_cp, 2), numero(r.rho_o_g_cm3, 4),
                    r.bg != null ? numero(r.bg, 5) : "—", r.z != null ? numero(r.z, 3) : "—"]), "dp-tab-pvt"));
  c.appendChild(el("p", "ajuda", "Linha tracejada: pressão de saturação (o maior Bo). A viabilidade usa esta tabela na pressão do reservatório."));
  return c;
}

function secaoComposicao(cp) {
  return tabelaSimples(["Componente", "Óleo estabilizado (%)", "Gás (%)", "Fluido do reservatório (%)"],
    cp.componentes.map((x) => [x.componente, numero(x.oleo_pct, 2), numero(x.gas_pct, 2), numero(x.fluido_pct, 2)]));
}


// ------------------------------------------------ PAG: gás e salinidade da lama, descrição de calha
function secaoPag(caixa, it, toposRfp) {
  const tc = it.topo_calha || [], gas = it.gas_lama || [], sal = it.salinidade_lama || [];
  const lito = it.litologia_calha || [], fl = it.indicio_calha || [];
  if (tc.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Formação", "Topo pela calha (m)", "Última amostra acima (m)", "RFP constatado (m)"],
      tc.map((t) => {
        const r = (toposRfp || []).filter((x) => x.prof_topo != null && Math.abs(x.prof_topo - t.prof_topo) <= 10)
          .sort((a, b) => Math.abs(a.prof_topo - t.prof_topo) - Math.abs(b.prof_topo - t.prof_topo))[0];
        return [t.nome, numero(t.prof_topo, 0), t.extra.acima != null ? numero(t.extra.acima, 0) : "",
                r ? numero(r.prof_topo, 1) : ""];
      })));
    c.appendChild(el("p", "ajuda", "A formação muda entre a última amostra de uma e a primeira da outra: o topo real está " +
      "nesse intervalo (9 m ou 3 m, conforme a amostragem)."));
    blocoDp(caixa, "Topos pela descrição de calha (PAG)", tc.length, true, c);
  }
  if (gas.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Intervalo (m)", "Gás total máx. (ppm)", "Acima do fundo", "Razões (Haworth)"],
      gas.map((z) => [intervaloM(z.prof_topo, z.prof_base), numero(z.valor, 0), z.texto,
                      z.extra.wh != null ? `Wh ${numero(z.extra.wh, 1)} · Bh ${numero(z.extra.bh, 1)} — ${z.nome || ""}` : "sem cromatografia"])));
    c.appendChild(el("p", "ajuda", `Zona de gás: gás total acima de 3 × o fundo do poço (${numero((gas[0].extra || {}).fundo, 0)} ppm, ` +
      "a mediana), com 2 m ou mais. É indício para escolher intervalos; o perfil e o teste confirmam."));
    blocoDp(caixa, "Gás na lama (PAG)", gas.length, true, c);
  }
  if (fl.length) {
    blocoDp(caixa, "Fluorescência e corte na calha (PAG)", fl.length, fl.length <= 10, tabelaSimples(
      ["Prof. (m)", "Formação", "Rocha", "Fluorescência", "Corte"],
      fl.map((x) => {
        const f = x.extra.fluorescencia || {}, k = x.extra.corte || {};
        return [intervaloM(x.prof_topo, x.prof_base), x.nome, x.texto,
                [f.fluor_tipo, f.fluor_pct ? `${f.fluor_pct}%` : "", f.fluor_cor, f.fluor_ton].filter(Boolean).join(" "),
                [k.velocidade, k.modo].filter(Boolean).join(" ")];
      })));
  }
  if (sal.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Prof. (m)", "Salinidade (ppm)", "Rw de NaCl equivalente a 75 °F (Ω·m)"],
      sal.map((s) => [numero(s.prof_topo, 0), numero(s.valor, 0), s.extra.rw75 != null ? numero(s.extra.rw75, 4) : ""])));
    c.appendChild(el("p", "ajuda", "Resistividade de uma solução de NaCl com essa salinidade (Bateman e Konen, 1977). " +
      "Em lama base óleo, a salinidade é a da fase aquosa da emulsão e não há Rmf."));
    blocoDp(caixa, "Salinidade da lama (PAG)", sal.length, false, c);
  }
  if (lito.length) {
    const cont = new Map();
    for (const a of lito) cont.set(a.texto || "?", (cont.get(a.texto || "?") || 0) + 1);
    const linhas = [...cont.entries()].sort((a, b) => b[1] - a[1])
      .map(([r, n]) => [r, n, `${numero(100 * n / lito.length, 0)}%`]);
    const c = el("div");
    c.appendChild(tabelaSimples(["Rocha principal", "Amostras", "Das amostras"], linhas));
    c.appendChild(el("p", "ajuda", "Cada amostra de calha, com a rocha principal, vira a trilha de litologia na aba Perfis " +
      "quando o poço não tem a litologia do AGP."));
    blocoDp(caixa, "Litologia da calha (PAG)", lito.length, false, c);
  }
}


// ------------------------------------------------ checkshot: tempo × profundidade
function secaoCheckshot(ck, id) {
  const c = el("div", "dp-checkshot");
  const r = ck.referencia || {}, h = ck.cabecalho || {};
  const t = el("table", "tabela ficha");
  linhaFicha(t, "Aquisição", [h.companhia, h.data].filter(Boolean).join(" · "));
  linhaFicha(t, "Referências", [r.elev_mesa_m != null ? `mesa rotativa ${numero(r.elev_mesa_m, 1)} m` : "",
                                r.datum_sismico_m != null ? `datum sísmico ${numero(r.datum_sismico_m, 1)} m` : "",
                                r.prof_fonte_m != null ? `fonte a ${numero(r.prof_fonte_m, 1)} m de profundidade` : "",
                                r.afastamento_m != null ? `afastamento ${numero(r.afastamento_m, 1)} m` : ""].filter(Boolean).join(" · "));
  c.appendChild(t);
  const n = ck.niveis;
  const graf = el("div", "dp-pvt-graf");
  const s1 = svgEl("svg", { class: "dp-svg dp-svg-pvt", role: "img", "aria-label": "TWT × profundidade" });
  graficoXY(s1, n.map((x) => x.twt_ms), n.map((x) => x.tvdsd), "TWT (ms)", "prof. (m)", null, true);
  const s2 = svgEl("svg", { class: "dp-svg dp-svg-pvt", role: "img", "aria-label": "Velocidade intervalar" });
  graficoXY(s2, n.map((x) => x.vint_m_s), n.map((x) => x.tvdsd), "Vint (m/s)", "prof. (m)", null, true);
  graf.append(s1, s2);
  c.appendChild(graf);
  c.appendChild(tabelaSimples(["MD (m)", "TVD abaixo do datum (m)", "Tempo vertical (s)", "TWT (ms)", "Vméd (m/s)", "Vint (m/s)"],
    n.map((x) => [numero(x.md, 1), numero(x.tvdsd, 1), numero(x.tcorr_s, 4), numero(x.twt_ms, 1), numero(x.vmed_m_s, 0),
                  x.vint_m_s != null ? numero(x.vint_m_s, 0) : "—"]), "dp-tab-pvt"));
  c.appendChild(el("p", "ajuda", "Do cabeçalho de cada traço do SEG-Y: tempo vertical = tempo de chegada × componente " +
    "vertical do raio + correção da fonte ao datum; TWT = 2 × o tempo vertical. Na aba Perfis, o mouse mostra o TWT " +
    "de cada profundidade."));
  const b = el("button", "btn secundario pequeno", "Exportar a tabela (CSV)");
  b.onclick = async () => {
    const x = await chamar(b, "exportar_checkshot", id);
    if (x.ok) status(`Tabela tempo × profundidade (${x.niveis} níveis) em ${x.arquivo}.`, "ok");
  };
  c.appendChild(b);
  return c;
}


// ------------------------------------------------ geoquímica: isótopos do gás, geoquímica de rocha
function secaoGeoquimica(caixa, it) {
  const iso = it.isotopo_gas || [], roc = it.geoquimica_rocha || [];
  if (iso.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Intervalo (m)", "Amostra", "δ¹³C metano (‰)", "δ¹³C etano (‰)", "δ¹³C propano (‰)", "Leitura"],
      iso.map((x) => [intervaloM(x.prof_topo, x.prof_base), x.texto, numero(x.extra.C1, 2), numero(x.extra.C2, 2),
                      numero(x.extra.C3, 2), x.nome])));
    c.appendChild(el("p", "ajuda", "δ¹³C do metano mais pesado que −50 ‰: gás termogênico; mais leve que −60 ‰: biogênico " +
      "(Schoell, 1983; Whiticar, 1999). É indício da origem do gás, não prova."));
    blocoDp(caixa, "Geoquímica — isótopos de carbono do gás", iso.length, true, c);
  }
  if (roc.length) {
    blocoDp(caixa, "Geoquímica de rocha", roc.length, roc.length <= 10, tabelaSimples(
      ["Prof. (m)", "COT (%)", "S1", "S2", "S3", "Tmax (°C)", "IH", "IO", "Ro (%)"],
      roc.map((x) => [intervaloM(x.prof_topo, x.prof_base), numero(x.valor, 2), numero(x.extra.s1, 2), numero(x.extra.s2, 2),
                      numero(x.extra.s3, 2), numero(x.extra.tmax, 0), numero(x.extra.ih, 0), numero(x.extra.io, 0),
                      numero(x.extra.ro, 2)])));
  }
}


// ------------------------------------------------ petrofísica básica de testemunho: plugs e gama (0.48)
function faixaTexto(valores, casas) {
  const v = valores.filter((x) => x != null);
  if (!v.length) return "—";
  return `${numero(Math.min(...v), casas)} a ${numero(Math.max(...v), casas)}`;
}

function secaoPetrofisica(caixa, it) {
  const plugs = it.plug_testemunho || [], gama = it.gama_testemunho || [];
  if (plugs.length) {
    const c = el("div");
    c.appendChild(tabelaSimples(["Prof. (m)", "Amostra", "Tipo", "Porosidade (%)", "Permeabilidade long. (mD)", "Densidade", "Pressão (psi)"],
      plugs.map((x) => [numero(x.prof_topo, 2), x.nome, x.texto, numero(x.valor, 1), numero(x.extra.permeabilidade, 2),
                        numero(x.extra.densidade, 2), numero(x.extra.pressao, 0)])));
    c.appendChild(el("p", "ajuda", `${plugs.length} plug(s): porosidade ${faixaTexto(plugs.map((x) => x.valor), 1)} %; ` +
      `permeabilidade ${faixaTexto(plugs.map((x) => x.extra.permeabilidade), 2)} mD. A planilha não diz a unidade da ` +
      "densidade (valores perto de 2,65 sugerem densidade de grãos em g/cm³, mas confira com a operadora). " +
      "É medida em plug de testemunho, não perfil: serve de referência para a porosidade do perfil, não a substitui."));
    blocoDp(caixa, "Petrofísica de testemunho — plugs", plugs.length, true, c);
  }
  if (gama.length) {
    const prof = gama.map((x) => x.prof_topo);
    const c = el("div");
    c.appendChild(el("p", "ajuda", `${gama.length} pontos de gama do testemunho, de ${numero(Math.min(...prof), 1)} a ` +
      `${numero(Math.max(...prof), 1)} m: ${faixaTexto(gama.map((x) => x.valor), 1)} API. Serve para casar a profundidade ` +
      "do testemunho com a do perfil de raios gama (a diferença é o deslocamento do testemunho)."));
    c.appendChild(tabelaSimples(["Testemunho", "Prof. (m)", "Gama (API)"],
      gama.map((x) => [x.nome, numero(x.prof_topo, 2), numero(x.valor, 1)])));
    blocoDp(caixa, "Gama do testemunho (COREGAMA)", gama.length, gama.length <= 10, c);
  }
}


// ------------------------------------------------ topos de várias fontes: comparar e escolher (0.45)
function secaoToposFicha(corpo, tp, id) {
  if (!tp || !(tp.unidades || []).length) return;
  const caixa = el("div", "tp-secao");
  caixa.id = "fi-topos";
  corpo.appendChild(caixa);
  desenharToposFicha(caixa, tp, id);
}

function desenharToposFicha(caixa, tp, id) {
  limpar(caixa);
  const fontes = Object.keys(tp.fontes);
  const presentes = fontes.filter((f) => tp.unidades.some((u) => u.fontes[f]));
  caixa.appendChild(el("h3", "", "Topos de formação — compare as fontes e escolha"));
  caixa.appendChild(el("p", "ajuda", "O topo usado na seção estratigráfica e no bloco 3D. Sem escolha, vale a primeira " +
    `fonte da ordem do projeto: ${tp.precedencia.map((f) => tp.fontes[f]).join(" → ")} (mude em Dados › Dados consolidados).` +
    (tp.divergentes ? ` ${tp.divergentes} unidade(s) com fontes que diferem mais de ${numero(tp.tolerancia_m, 0)} m.` : "")));
  const t = el("table", "tabela tp-tabela");
  const cab = el("tr");
  for (const h of ["Unidade", ...presentes.map((f) => tp.fontes[f]), "Diferença (m)", "Usar"]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const u of tp.unidades) {
    const tr = el("tr");
    tr.appendChild(el("td", "", u.nome));
    for (const f of presentes) {
      const c = u.fontes[f];
      const td = el("td", c && u.usada === f ? "tp-usada" : "", c ? numero(c.topo, 1) : "—");
      if (c) td.title = [c.nome, c.detalhe, c.ref && c.ref.split("/").pop()].filter(Boolean).join(" · ");
      tr.appendChild(td);
    }
    tr.appendChild(el("td", u.diferenca_m > tp.tolerancia_m ? "tp-diverge" : "", u.diferenca_m ? numero(u.diferenca_m, 1) : "—"));
    const sel = el("select", "tp-escolha");
    sel.dataset.chave = u.chave;
    const padrao = u.escolha ? "padrão do projeto" : `padrão (${u.usada ? tp.fontes[u.usada] : "—"})`;
    sel.appendChild(new Option(padrao, "padrao"));
    for (const f of fontes) if (u.fontes[f]) sel.appendChild(new Option(tp.fontes[f], f));
    sel.appendChild(new Option("não usar", "nenhuma"));
    sel.value = u.escolha || "padrao";
    sel.onchange = async () => {
      const r = await chamar(sel, "topos_escolher", id, u.chave, sel.value);
      if (!r.ok) return;
      status(`Topo de ${u.nome}: ${sel.value === "padrao" ? "padrão do projeto" : sel.value === "nenhuma" ? "não usado" : tp.fontes[sel.value]}.`, "ok");
      desenharToposFicha(caixa, r, id);
    };
    const td = el("td");
    td.appendChild(sel);
    tr.appendChild(td);
    t.appendChild(tr);
  }
  caixa.appendChild(t);
  caixa.appendChild(el("p", "ajuda", "Em negrito, o topo usado. Passe o mouse num valor para ver de qual documento veio."));
}
