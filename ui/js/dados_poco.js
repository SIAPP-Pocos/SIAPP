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
  caixa.appendChild(el("h3", "", "Formulários da ANP e testes de formação"));
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
  if (topos.length) {
    const semNome = topos.every((x) => !x.nome);
    const c = el("div");
    c.appendChild(tabelaSimples(["Unidade", "Prevista (m)", "Constatada (m)", "Cota (m)", "Diferença (m)"],
      topos.map((x) => [x.nome || `topo ${x.extra.ordem}`, numero(x.extra.prev_medida, 1), numero(x.prof_topo, 1),
                        numero(x.cota, 1),
                        x.extra.prev_medida != null ? (x.prof_topo - x.extra.prev_medida >= 0 ? "+" : "") +
                          numero(x.prof_topo - x.extra.prev_medida, 1) : ""])));
    if (semNome) c.appendChild(el("p", "ajuda", "Este formulário não traz o nome das unidades, só as profundidades; " +
      "compare com os topos do AGP ou de um documento do poço."));
    blocoDp(caixa, "Topos estratigráficos", topos.length, true, c);
  }

  const pr = dp.pressoes || {};
  if ((pr.pontos || []).length) blocoDp(caixa, "Pressões × profundidade", pr.pontos.length, true, secaoPressoes(pr));
  for (const t of pr.tfr || []) blocoDp(caixa, `Teste de formação ${t.nome || ""} — relatório`, null, true, secaoTfr(t, pr.series || []));

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
