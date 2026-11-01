// SIAPP — Bloco 3D › Zonas produtoras (net pay): topo e base de cada reservatório, poço a poço, no lugar dos topos de formação.
// Aqui se escolhem as fontes dos intervalos, se confere o que o SIAPP achou (com o aviso de OCR), se move, ignora ou corrige cada
// intervalo, se escolhe qual reservatório mostrar e se compara com a tabela feita à mão.

const bz = { fontes: [], ativas: null, ajustes: {}, nomes: {}, previa: null, tabela: null, info: null };
const FONTES_ZONA = [
  ["tabela", "Tabela sua (CSV ou Excel importado)"],
  ["marcado", "Intervalos que você marcou (intervalo-alvo)"],
  ["canhoneado", "Canhoneados (RFCP)"],
  ["teste", "Testes de formação (RFP, TFR)"],
  ["analise_perfil", "Análise de perfis do operador (RFP)"],
  ["fluido", "Análise de fluido (amostra do PVT)"],
  ["agp_zonas", "Zonas-reservatório do AGP"],
];

function iniciarZonas() {
  if (!$("bl-zonas")) return;
  bz.fontes = FONTES_ZONA.map(([id, rotulo]) => ({ id, rotulo, marcada: id !== "tabela" }));
  desenharFontesZona();
  $("bl-nivel").addEventListener("change", aoMudarNivelZonas);
  $("bz-previa").onclick = previaZonas;
  $("bz-importar").onclick = importarTabelaZonas;
  $("bz-apagar-tabela").onclick = apagarTabelaZonas;
  for (const id of ["bz-regra", "bz-tol", "bz-coord"]) $(id).onchange = () => { if (bz.previa) previaZonas(); };
  aoMudarNivelZonas();
}

function aoMudarNivelZonas() {
  const ativo = $("bl-nivel").value === "zonas";
  $("bl-zonas").hidden = !ativo;
  if (ativo) carregarTabelaZonas();
}

function desenharFontesZona() {
  const caixa = limpar($("bz-fontes"));
  bz.fontes.forEach((f, i) => {
    const linha = el("div", "bz-fonte");
    const cx = el("input");
    cx.type = "checkbox";
    cx.checked = f.marcada;
    cx.disabled = f.id === "tabela" && !bz.tabela;
    cx.onchange = () => { f.marcada = cx.checked; if (bz.previa) previaZonas(); };
    const subir = el("button", "btn secundario pequeno", "↑");
    subir.title = "Dar mais prioridade";
    subir.disabled = i === 0;
    subir.onclick = () => { [bz.fontes[i - 1], bz.fontes[i]] = [bz.fontes[i], bz.fontes[i - 1]]; desenharFontesZona(); if (bz.previa) previaZonas(); };
    const rot = el("label", "opcao");
    rot.append(cx, el("span", "", ` ${i + 1}. ${f.rotulo}`));
    linha.append(rot, subir);
    caixa.appendChild(linha);
  });
}

// O que a ponte precisa para montar (e para a prévia).
function lerZonasBloco() {
  if ($("bl-nivel").value !== "zonas") return undefined;
  return {
    fontes: bz.fontes.filter((f) => f.marcada).map((f) => f.id), regra: $("bz-regra").value, tolerancia_m: $("bz-tol").value,
    ativas: bz.ativas ? [...bz.ativas] : null, ajustes: bz.ajustes, nomes: bz.nomes,
    usar_coordenadas_da_tabela: $("bz-coord").checked,
  };
}

// ------------------------------------------------------------------------------------------------------ tabela do usuário
async function carregarTabelaZonas() {
  const r = await chamar(null, "bloco_zonas_tabela");
  if (r.ok) mostrarTabelaZonas(r.tabela);
}

function mostrarTabelaZonas(t) {
  bz.tabela = t;
  const info = $("bz-tabela-info");
  $("bz-apagar-tabela").hidden = !t;
  $("bz-coord").disabled = !(t && t.com_coordenadas);
  if (!t) {
    info.textContent = "Nenhuma tabela sua importada. O arquivo precisa ter, no cabeçalho, as colunas de poço, topo e base (e, se tiver, reservatório, lat/lon ou X/Y em UTM).";
    for (const f of bz.fontes) if (f.id === "tabela") f.marcada = false;
  } else {
    info.textContent = `${t.origem}: ${t.n_linhas} linha(s), ${t.n_pocos} poço(s); profundidade em ${t.ref === "cota" ? "cota" : "profundidade medida"}; ` +
      `${t.com_coordenadas ? "com coordenadas" : "sem coordenadas"}. ` + (t.avisos || []).join(" ");
    for (const f of bz.fontes) if (f.id === "tabela") f.marcada = true;
  }
  desenharFontesZona();
}

async function importarTabelaZonas() {
  const r = await chamar($("bz-importar"), "bloco_zonas_importar_tabela", $("bz-ref").value, $("bz-utm").value.trim(), true);
  if (!r.ok || r.cancelado) return;
  mostrarTabelaZonas(r.tabela);
  status(`Tabela ${r.tabela.origem} importada (${r.tabela.n_linhas} linhas).`, "ok");
  if (bz.previa) previaZonas();
}

async function apagarTabelaZonas() {
  const r = await chamar($("bz-apagar-tabela"), "bloco_zonas_apagar_tabela");
  if (!r.ok) return;
  $("bz-coord").checked = false;
  mostrarTabelaZonas(null);
  if (bz.previa) previaZonas();
}

// ------------------------------------------------------------------------------------------------------ prévia dos reservatórios
async function previaZonas() {
  if (!bl.pocos.length) { status("Escolha os poços do bloco primeiro (passo 1 e 2).", "erro"); return; }
  const r = await chamar($("bz-previa"), "bloco_zonas_previa", bl.pocos, { zonas: lerZonasBloco() });
  if (!r.ok) return;
  bz.previa = r;
  if (bz.ativas === null) bz.ativas = new Set(r.zonas.map((z) => z.chave));
  for (const z of r.zonas) if (bz.nomes[z.chave] == null) bz.nomes[z.chave] = z.nome;
  desenharPreviaZonas();
}

const ROTULO_LEITURA = { digital: "texto digital", ocr: "OCR: conferir", "": "—" };

function desenharPreviaZonas() {
  const r = bz.previa;
  const caixa = limpar($("bz-resultado"));
  // resumo e aviso de OCR: números lidos por reconhecimento de imagem precisam de conferência
  const usados = r.candidatos.filter((c) => c.usado);
  const ocr = usados.filter((c) => c.leitura === "ocr").length;
  caixa.appendChild(el("p", "ajuda", `${r.candidatos.length} intervalo(s) candidato(s) em ${new Set(r.candidatos.map((c) => c.poco)).size} poço(s); ` +
    `${usados.length} usado(s) nos reservatórios. ` + (usados.length ? `${ocr} de ${usados.length} vêm de página lida por OCR` +
    (ocr ? ": **confira cada número na imagem do documento** (o OCR erra profundidades)." : ".") : "")));
  for (const a of r.avisos || []) caixa.appendChild(el("p", "aviso", a));

  caixa.appendChild(el("h3", "", "Reservatórios"));
  const t = el("table", "tabela");
  const cab = el("tr");
  for (const h of ["Mostrar", "Nome", "Poços", "Cota média (m)", "Espessura média (m)"]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const z of r.zonas) {
    const tr = el("tr");
    const cx = el("input");
    cx.type = "checkbox";
    cx.checked = bz.ativas.has(z.chave);
    cx.onchange = () => { cx.checked ? bz.ativas.add(z.chave) : bz.ativas.delete(z.chave); };
    const nome = el("input");
    nome.type = "text";
    nome.value = bz.nomes[z.chave] || z.nome;
    nome.onchange = () => { bz.nomes[z.chave] = nome.value.trim() || z.nome; };
    const td0 = el("td"), td1 = el("td");
    td0.appendChild(cx);
    td1.appendChild(nome);
    tr.append(td0, td1, el("td", "n", String(z.n_pocos)), el("td", "n", z.cota_media == null ? "—" : numero(z.cota_media, 1)),
              el("td", "n", z.espessura_media == null ? "—" : numero(z.espessura_media, 1)));
    t.appendChild(tr);
  }
  caixa.appendChild(t);
  caixa.appendChild(el("p", "ajuda", "Marque só um reservatório para montar o bloco só com ele (por exemplo, o raso, que tem mais poços). " +
    "O agrupamento é pela profundidade: se um mesmo reservatório ficou dividido (falha), aumente a tolerância ou mova os intervalos."));

  caixa.appendChild(el("h3", "", "Intervalos poço a poço"));
  caixa.appendChild(tabelaCandidatosZona(r));
  if (r.comparacao) caixa.appendChild(tabelaComparacaoZona(r.comparacao));
}

function aplicarAjuste(c, campos) {
  const aj = { ...(bz.ajustes[c.id] || {}), ...campos };
  if (aj.topo != null && Number(aj.topo) === c.topo_orig) delete aj.topo;
  if (aj.base != null && Number(aj.base) === c.base_orig) delete aj.base;
  if (aj.zona === "auto") delete aj.zona;
  if (Object.keys(aj).length) bz.ajustes[c.id] = aj; else delete bz.ajustes[c.id];
  previaZonas();
}

function tabelaCandidatosZona(r) {
  const t = el("table", "tabela bz-tabela");
  const cab = el("tr");
  for (const h of ["Poço", "Fonte", "Descrição", "Topo (m)", "Base (m)", "Leitura", "Reservatório", "Usado"]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  const chaves = r.zonas.map((z) => z.chave);
  const ordem = [...r.candidatos].sort((a, b) => a.poco.localeCompare(b.poco) || a.topo - b.topo);
  for (const c of ordem) {
    const tr = el("tr", c.usado ? "" : "bz-nao-usado");
    const topo = el("input"), base = el("input");
    for (const [inp, v, campo] of [[topo, c.topo, "topo"], [base, c.base, "base"]]) {
      inp.type = "text";
      inp.className = "curto";
      inp.value = String(v).replace(".", ",");
      inp.onchange = () => {
        const x = Number(inp.value.replace(/\./g, "").replace(",", "."));
        if (Number.isFinite(x)) aplicarAjuste(c, { [campo]: x });
      };
    }
    const sel = el("select");
    for (const [v, rot] of [["auto", "automático"], ...chaves.map((k) => [k, bz.nomes[k] || k]), ["ignorar", "ignorar"]]) sel.appendChild(new Option(rot, v));
    const aj = bz.ajustes[c.id] || {};
    sel.value = aj.zona === "ignorar" ? "ignorar" : aj.zona || "auto";
    sel.onchange = () => aplicarAjuste(c, { zona: sel.value });
    const t0 = el("td"), t1 = el("td"), t2 = el("td");
    t0.appendChild(topo); t1.appendChild(base); t2.appendChild(sel);
    const doc = c.rel ? `${c.documento || ""} ${c.rel.split("/").pop()}${c.pagina ? ", p. " + c.pagina : ""}` : "";
    const leitura = el("td", c.leitura === "ocr" ? "bz-ocr" : "", ROTULO_LEITURA[c.leitura || ""]);
    if (doc) leitura.title = doc;
    const status_ = c.aviso ? c.aviso : c.ignorado ? "ignorado" : c.usado ? "✓" : "";
    tr.append(el("td", "mono", c.poco), el("td", "", c.fonte_rotulo), el("td", "", c.nome || "—"), t0, t1, leitura, t2,
              el("td", "", status_ + (c.editado ? " (editado)" : "")));
    t.appendChild(tr);
  }
  return t;
}

function tabelaComparacaoZona(comp) {
  const box = el("div");
  box.appendChild(el("h3", "", "Sua tabela × o que o SIAPP escolheu"));
  box.appendChild(el("p", "ajuda", "Diferença = SIAPP − sua tabela, em metros (positiva: o SIAPP é mais fundo). O SIAPP aqui usa as outras fontes, sem a sua tabela."));
  const t = el("table", "tabela");
  const cab = el("tr");
  for (const h of ["Poço", "Sua tabela (topo–base)", "SIAPP (topo–base)", "Fonte do SIAPP", "Dif. topo", "Dif. base", "Situação"]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  const f = (v) => (v == null ? "—" : numero(v, 1));
  for (const x of comp) {
    const tr = el("tr");
    tr.append(el("td", "mono", x.poco), el("td", "", `${f(x.topo_tabela)}–${f(x.base_tabela)}${x.ref === "cota" ? " (cota)" : ""}`),
              el("td", "", x.topo_siapp == null ? "—" : `${f(x.topo_siapp)}–${f(x.base_siapp)}`), el("td", "", x.fonte_siapp || "—"),
              el("td", "n", f(x.dif_topo)), el("td", "n", f(x.dif_base)), el("td", "", x.situacao));
    t.appendChild(tr);
  }
  box.appendChild(t);
  return box;
}

iniciarZonas();
