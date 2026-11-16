// SIAPP — Acervo › Buscar por tipo: em quais poços há cada tipo de dado, pelo levantamento do acervo.
// Nada é baixado para procurar; baixar é uma ação à parte, só dos poços que você marcar.

const tdado = { tipos: [], marcados: new Set(), resultado: null, escolhidos: new Set(), restrito: null };
const LIMITE_MAPA = 300;
const AVISO_DOWNLOAD_BYTES = 2 * 1024 ** 3;

// Restrição da busca: um campo digitado, ou poços vindos da Seção ou do Mapa.
function restricaoTipos() {
  const campo = $("tp-campo").value.trim();
  if (campo) return { campo };
  if (tdado.restrito) return { pocos: tdado.restrito.pocos };
  return null;
}

function desenharRestricaoTipos() {
  const box = limpar($("tp-restricao"));
  if (!tdado.restrito) return;
  const c = el("span", "chip-dic");
  const x = el("button", "x", "×");
  x.type = "button";
  x.title = "Tirar a restrição";
  x.onclick = () => { tdado.restrito = null; carregarTipos(); };
  c.append(el("span", "", `Só ${tdado.restrito.rotulo}`), x);
  box.appendChild(c);
}

// Chamado pela Seção e pelo Mapa: abre Acervo › Buscar por tipo já restrito a esses poços.
function procurarDadosDosPocos(ids, rotulo) {
  const lista = [...new Set((ids || []).map((x) => String(x).trim()).filter(Boolean))];
  if (!lista.length) { status("Não há poços para procurar: adicione poços primeiro.", "erro"); return; }
  tdado.restrito = { pocos: lista, rotulo };
  $("tp-campo").value = "";
  tdado.resultado = null;
  limpar($("tp-resultado"));
  irPara("tipos", "carregarTipos");
}

async function carregarTipos() {
  if (!api || !$("tp-tipos")) return;
  const bacia = $("tp-bacia").value || "";
  const r = await chamar(null, "tipos_de_dado", bacia, restricaoTipos());
  if (!r.ok) return;
  tdado.tipos = r.tipos;
  preencherCamposTipos(r.campos || []);
  desenharRestricaoTipos();
  preencherBaciasTipos(r.bacias || [], bacia);
  desenharTipos(r);
}

function preencherCamposTipos(campos) {
  const dl = $("tp-campos");
  if (dl.options.length === campos.length) return;
  limpar(dl);
  for (const c of campos) dl.appendChild(new Option(`${c.n} poço(s)`, c.campo));
}

function preencherBaciasTipos(bacias, atual) {
  const sel = $("tp-bacia");
  if (sel.options.length === bacias.length + 1) return;      // já preenchida
  limpar(sel);
  sel.appendChild(new Option("Todas as bacias levantadas", ""));
  for (const b of bacias) sel.appendChild(new Option(b, b));
  sel.value = atual || "";
}

function desenharTipos(r) {
  const box = limpar($("tp-tipos"));
  if (!r.pocos_levantados) {
    box.appendChild(el("p", "ajuda", "Ainda não há levantamento do acervo neste projeto. Faça um em Acervo › Levantamento do " +
      "acervo (a listagem não baixa os arquivos) e volte aqui."));
    return;
  }
  const intro = el("p", "ajuda", `${numero(r.pocos_levantados, 0)} poço(s) levantado(s). Marque o que procura:`);
  if (r.criterio) intro.title = "Como conta: " + r.criterio;
  box.appendChild(intro);
  if (r.criterio) box.appendChild(el("p", "ajuda criterio", "Como conta: " + r.criterio));
  // 0.59: "tudo de um campo" = todos os tipos + "pelo menos um" + o campo acima
  const atalhos = el("div", "linha");
  const bTudo = el("button", "btn secundario pequeno", "Todos os tipos");
  bTudo.id = "tp-todos-tipos";
  bTudo.type = "button";
  bTudo.title = "Marca todos os tipos e procura poços com pelo menos um deles (com o campo acima: tudo do campo)";
  bTudo.onclick = () => {
    for (const t of r.tipos) if (t.n_pocos) tdado.escolhidos.add(t.chave);
    $("tp-modo").value = "algum";
    desenharTipos(r);
  };
  const bNada = el("button", "btn secundario pequeno", "Nenhum");
  bNada.type = "button";
  bNada.onclick = () => { tdado.escolhidos.clear(); desenharTipos(r); };
  atalhos.append(bTudo, bNada);
  box.appendChild(atalhos);
  const lista = el("div", "tp-lista");
  for (const t of r.tipos) {
    const rot = el("label", "opcao tp-tipo" + (t.n_pocos ? "" : " tp-vazio"));
    const cx = el("input");
    cx.type = "checkbox";
    cx.disabled = !t.n_pocos;
    cx.checked = tdado.escolhidos.has(t.chave);
    cx.onchange = () => { cx.checked ? tdado.escolhidos.add(t.chave) : tdado.escolhidos.delete(t.chave); };
    const txt = el("span");
    txt.append(el("strong", "", t.rotulo), el("span", "tp-n", ` — ${numero(t.n_pocos, 0)} poço(s), ${numero(t.n_arquivos, 0)} arquivo(s), ${tamanho(t.bytes)}`));
    txt.append(el("br"), el("span", "ajuda", `${t.descricao} SIAPP: ${t.le_com}.`));
    rot.append(cx, txt);
    lista.appendChild(rot);
  }
  box.appendChild(lista);
}

async function procurarPorTipo() {
  if (!tdado.escolhidos.size) { status("Marque pelo menos um tipo de dado.", "erro"); return; }
  const r = await chamar($("tp-procurar"), "buscar_por_tipo", [...tdado.escolhidos], $("tp-bacia").value, $("tp-modo").value, restricaoTipos());
  if (!r.ok) return;
  tdado.resultado = r;
  tdado.marcados = new Set();                                    // nada vem marcado
  desenharResultadoTipos();
}

function resumoMarcados() {
  const r = tdado.resultado;
  const pocos = r.pocos.filter((p) => tdado.marcados.has(chavePoco(p)));
  const arqs = pocos.reduce((s, p) => s + p.arquivos.length, 0);
  const bytes = pocos.reduce((s, p) => s + p.arquivos.reduce((x, a) => x + (a.tamanho || 0), 0), 0);
  return { pocos, arqs, bytes };
}

const chavePoco = (p) => `${p.bacia}|${p.poco}`;

function desenharResultadoTipos() {
  const r = tdado.resultado;
  const box = limpar($("tp-resultado"));
  const nomes = r.tipos.map((t) => r.rotulos[t]).join(r.modo === "todos" ? " + " : " ou ");
  box.appendChild(el("h3", "", `${numero(r.n_pocos, 0)} poço(s) com ${nomes}`));
  if (!r.n_pocos) {
    box.appendChild(el("p", "ajuda", "Nenhum poço levantado tem essa combinação. Tente “pelo menos um dos tipos” ou outra bacia."));
    return;
  }
  box.appendChild(el("p", "ajuda", `${numero(r.n_arquivos, 0)} arquivo(s) desses tipos, ${tamanho(r.bytes)} no total. ` +
    "Nada vem marcado: marque os poços de que precisa."));
  const acoes = el("div", "linha");
  const bTodos = el("button", "btn secundario pequeno", "Marcar todos");
  const bNenhum = el("button", "btn secundario pequeno", "Desmarcar todos");
  const bMapa = el("button", "btn secundario pequeno", "Ver os marcados no mapa");
  const bCsv = el("button", "btn secundario pequeno", "Exportar a busca (CSV)");
  const bBaixar = el("button", "btn pequeno", "Baixar os arquivos dos marcados");
  const marc = el("span", "ajuda");
  acoes.append(bTodos, bNenhum, bMapa, bCsv, bBaixar, marc);
  box.appendChild(acoes);
  const area = el("div", "tp-confirmar");
  box.appendChild(area);

  const t = el("table", "tabela");
  const cab = el("tr");
  const todos = el("input");
  todos.type = "checkbox";
  todos.title = "Marcar ou desmarcar todos";
  const th0 = el("th");
  th0.appendChild(todos);
  cab.appendChild(th0);
  for (const h of ["Poço", "Bacia", "Categoria", ...r.tipos.map((x) => r.rotulos[x]), ""]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  const caixas = [];
  for (const p of r.pocos) {
    const tr = el("tr");
    const cx = el("input");
    cx.type = "checkbox";
    cx.onchange = () => { cx.checked ? tdado.marcados.add(chavePoco(p)) : tdado.marcados.delete(chavePoco(p)); atualizarMarcados(); };
    caixas.push([cx, p]);
    const td0 = el("td");
    td0.appendChild(cx);
    const tdf = el("td");
    const bf = el("button", "btn secundario pequeno", "Ficha");
    bf.onclick = () => { $("aba-mapa").click(); abrirFicha(p.poco_id); };
    tdf.appendChild(bf);
    tr.append(td0, el("td", "mono", p.poco), el("td", "", p.bacia), el("td", "", p.categoria || "—"),
              ...r.tipos.map((x) => {
                const d = p.tipos[x];
                return el("td", "", d ? `${d.n_arquivos} arq · ${tamanho(d.bytes)}` : "—");
              }), tdf);
    t.appendChild(tr);
  }
  box.appendChild(t);

  function atualizarMarcados() {
    const m = resumoMarcados();
    marc.textContent = m.pocos.length ? `${m.pocos.length} marcado(s): ${m.arqs} arquivo(s), ${tamanho(m.bytes)}` : "nenhum marcado";
    todos.checked = m.pocos.length === r.pocos.length;
    limpar(area);
  }
  function marcarTodos(v) {
    tdado.marcados = new Set(v ? r.pocos.map(chavePoco) : []);
    for (const [cx, p] of caixas) cx.checked = tdado.marcados.has(chavePoco(p));
    atualizarMarcados();
  }
  todos.onchange = () => marcarTodos(todos.checked);
  bTodos.onclick = () => marcarTodos(true);
  bNenhum.onclick = () => marcarTodos(false);
  bMapa.onclick = () => verNoMapa(resumoMarcados().pocos);
  bCsv.onclick = async () => {
    const x = await chamar(bCsv, "exportar_busca_por_tipo", r.tipos, r.bacia, r.modo, restricaoTipos());
    if (x.ok) status(`Busca gravada em ${x.arquivo} (${x.n_pocos} poços, ${x.n_arquivos} arquivos).`, "ok");
  };
  bBaixar.onclick = () => pedirDownloadTipos(area, resumoMarcados());
  atualizarMarcados();
}

async function verNoMapa(pocos) {
  if (!pocos.length) { status("Marque os poços que quer ver no mapa.", "erro"); return; }
  if (pocos.length > LIMITE_MAPA) {
    status(`São ${pocos.length} poços marcados; o mapa destaca até ${LIMITE_MAPA} de uma vez. Marque menos.`, "erro");
    return;
  }
  $("aba-mapa").click();
  const cor = ($("dq-cor") && $("dq-cor").value) || "#e0218a";
  await destacarPocos(pocos.map((p) => p.poco_id), cor);
}

function pedirDownloadTipos(area, m) {
  limpar(area);
  if (!m.pocos.length) { status("Marque os poços cujos arquivos quer baixar.", "erro"); return; }
  area.appendChild(el("p", m.bytes > AVISO_DOWNLOAD_BYTES ? "erro" : "ajuda",
    `Baixar ${m.arqs} arquivo(s) de ${m.pocos.length} poço(s), ${tamanho(m.bytes)}, só das pastas dos tipos procurados` +
    (m.bytes > AVISO_DOWNLOAD_BYTES ? " — é bastante dado; confira antes." : ".") +
    " Eles caem na fila de downloads e ficam na pasta bruto do projeto, como sempre."));
  const ok = el("button", "btn", "Confirmar e baixar");
  const nao = el("button", "btn secundario", "Cancelar");
  nao.onclick = () => limpar(area);
  ok.onclick = async () => {
    ok.disabled = true;
    await baixarTipos(m.pocos);
    limpar(area);
  };
  const linha = el("div", "linha");
  linha.append(ok, nao);
  area.appendChild(linha);
}

async function baixarTipos(pocos) {
  const porBacia = new Map();
  for (const p of pocos) porBacia.set(p.bacia, [...(porBacia.get(p.bacia) || []), p]);
  let n = 0;
  for (const [bacia, lista] of porBacia) {
    status(`Conectando à bacia ${bacia}…`);
    const c = await chamar(null, "conectar", bacia);
    if (!c.ok) return;
    for (const p of lista) {
      const arquivos = p.arquivos.map((a) => ({ caminho: a.caminho, nome: a.nome, tamanho: a.tamanho, pasta_relativa: a.pasta_relativa }));
      const r = await chamar(null, "baixar", p.poco, arquivos, bacia);
      if (!r.ok) return;
      n += arquivos.length;
    }
  }
  status(`${n} arquivo(s) de ${pocos.length} poço(s) na fila de downloads (Acervo › Catálogo do REATE mostra o andamento).`, "ok");
}

function iniciarTipos() {
  if (!$("tp-procurar")) return;
  $("tp-procurar").onclick = procurarPorTipo;
  $("tp-bacia").onchange = carregarTipos;
  $("tp-campo").onchange = () => { if ($("tp-campo").value.trim()) tdado.restrito = null; carregarTipos(); };
}
iniciarTipos();
