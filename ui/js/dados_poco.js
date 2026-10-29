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
  caixa.appendChild(el("h3", "", "Formulários da ANP — RFP, completação e perfuração"));
  const ul = el("ul", "dp-docs");
  const ordem = { rfp: 0, rfcp: 1, perfuracao: 2 };
  for (const d of [...docs].sort((a, b) => (ordem[a.documento] ?? 9) - (ordem[b.documento] ?? 9))) {
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
  const calha = it.calha || [];
  if (calha.length) {
    blocoDp(caixa, "Amostragem de calha", calha.length, false, tabelaSimples(["Intervalo (m)", "Padrão"],
      calha.map((x) => [intervaloM(x.prof_topo, x.prof_base), x.texto])));
  }
  for (const d of docs) {
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
