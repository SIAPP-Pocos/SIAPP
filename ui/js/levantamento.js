// SIAPP — levantamento do acervo (aba Mapa): o que cada poço tem no portal,
// pelo conteúdo dos arquivos. O trabalho roda no motor, em segundo plano.
"use strict";

const CORES_ACERVO = { digital: "#2f7d4f", imagem: "#d08a1e", sem_perfil: "#a3342b", pendente: "#8e7cc3" };
const NOMES_SITUACAO = { digital: "perfil digital", imagem: "só imagem", sem_perfil: "sem perfil",
                         pendente: "falta conferir" };
const NOMES_FORMATO = { dlis: "DLIS", lis: "LIS", las: "LAS", tiff: "imagem TIFF", pdf: "PDF",
                        png: "imagem PNG", jpg: "imagem JPEG" };
let lvAtivo = false;

function preencherBaciasLevantamento(bacias) {
  const sel = $("lv-bacia");
  if (sel.options.length) return;
  for (const b of bacias) sel.appendChild(new Option(b, b));
  sel.value = baciaConectada || baciaAnterior || "Potiguar";
}

async function carregarLevantamento() {
  if (!projetoAberto || !$("lv-bacia").value) return;
  const r = await chamar(null, "levantamento_resumo", $("lv-bacia").value);
  if (!r.ok) return;
  lvAtivo = r.ativo;
  mostrarAtivo(r.ativo);
  desenharResumoLevantamento(r.resumo);
}

function mostrarAtivo(ativo) {
  $("lv-iniciar").hidden = ativo;
  $("lv-cancelar").hidden = !ativo;
  $("lv-progresso").hidden = !ativo;
}

function reiniciarCategorias() {
  const caixa = limpar($("lv-cats"));
  const b = el("button", "btn secundario pequeno", "Escolher categorias…");
  b.id = "lv-carregar";
  b.onclick = carregarCategoriasLevantamento;
  caixa.append(b, el("span", "ajuda", "sem escolher, levanta a bacia inteira"));
}

async function carregarCategoriasLevantamento() {
  const bacia = $("lv-bacia").value;
  const r = await chamar($("lv-carregar"), "levantamento_categorias", bacia);
  if (!r.ok) return;
  const caixa = limpar($("lv-cats"));
  for (const c of r.categorias) {
    const l = el("label", "opcao");
    const cb = el("input");
    cb.type = "checkbox";
    cb.value = c;
    cb.className = "lv-cat";
    l.append(cb, document.createTextNode(c.replace("Categoria-", "Cat. ")));
    caixa.appendChild(l);
  }
  caixa.appendChild(el("span", "ajuda", "nenhuma marcada = todas"));
}

async function iniciarLevantamento() {
  const bacia = $("lv-bacia").value;
  const cats = [...document.querySelectorAll(".lv-cat:checked")].map((c) => c.value);
  const r = await chamar($("lv-iniciar"), "levantar_acervo", bacia, cats,
                         $("lv-curvas").checked, $("lv-todos").checked, $("lv-agp").checked);
  if (!r.ok) return;
  lvAtivo = true;
  mostrarAtivo(true);
  $("lv-texto").textContent = `Começando o levantamento de ${bacia}…`;
  $("lv-barra").style.width = "0%";
  status(`Levantamento de ${bacia} em andamento. Pode usar o resto do SIAPP enquanto isso.`, "trab");
}

function pct(n, total) { return total ? `${numero((100 * n) / total, 0)}%` : "—"; }

function desenharResumoLevantamento(r) {
  const box = limpar($("lv-resumo"));
  $("lv-acoes").hidden = !r || !r.pocos;
  if (!r || !r.pocos) {
    box.appendChild(el("p", "ajuda", "Ainda não levantada neste projeto."));
    return;
  }
  const total = r.pocos;
  box.appendChild(el("p", "", `${numero(total, 0)} pasta(s) de poço em ${r.bacia} · ` +
    `${numero(r.arquivos_conferidos, 0)} de ${numero(r.arquivos_candidatos, 0)} arquivo(s) de perfil conferidos pelo conteúdo`));
  const barra = el("div", "barra-sit");
  for (const [s, n] of Object.entries(r.situacoes)) {
    if (!n) continue;
    const i = el("i");
    i.style.width = (100 * n) / total + "%";
    i.style.background = CORES_ACERVO[s];
    i.title = `${NOMES_SITUACAO[s]}: ${n}`;
    barra.appendChild(i);
  }
  box.appendChild(barra);
  const t = el("table");
  for (const [s, n] of Object.entries(r.situacoes)) {
    const tr = el("tr");
    const th = el("th");
    const b = el("i", "bola");
    b.style.background = CORES_ACERVO[s];
    th.append(b, document.createTextNode(" " + NOMES_SITUACAO[s]));
    tr.append(th, el("td", "n", numero(n, 0)), el("td", "n", pct(n, total)));
    t.appendChild(tr);
  }
  box.appendChild(t);
  if (Object.keys(r.extensao_enganosa || {}).length) {
    box.appendChild(el("h3", "", "O nome engana"));
    const tt = el("table");
    for (const [k, n] of Object.entries(r.extensao_enganosa)) {
      const tr = el("tr");
      tr.append(el("th", "", k), el("td", "n", numero(n, 0)));
      tt.appendChild(tr);
    }
    box.appendChild(tt);
  }
  if (r.pocos_com_curvas) {
    box.appendChild(el("h3", "", `Curvas (${numero(r.pocos_com_curvas, 0)} poço(s) com lista)`));
    const tf = el("table");
    for (const [f, n] of Object.entries(r.familias)) {
      const tr = el("tr");
      tr.append(el("th", "", f), el("td", "n", numero(n, 0)), el("td", "n", pct(n, r.pocos_com_curvas)));
      tf.appendChild(tr);
    }
    box.appendChild(tf);
  }
  const cats = Object.entries(r.por_categoria || {});
  if (cats.length > 1) {
    box.appendChild(el("h3", "", "Por categoria (digital / só imagem / sem perfil / falta)"));
    const tc = el("table");
    for (const [c, v] of cats) {
      const tr = el("tr");
      tr.append(el("th", "", c), el("td", "n", `${v.digital} / ${v.imagem} / ${v.sem_perfil} / ${v.pendente}`));
      tc.appendChild(tr);
    }
    box.appendChild(tc);
  }
  if (r.agp_disponiveis) {
    box.appendChild(el("h3", "", "AGP (topos de formação)"));
    const ta = el("table");
    for (const [rot, n] of [["AGPs no portal", r.agp_disponiveis], ["lidos", r.agp_lidos],
                            ["com topos de formação", r.agp_com_topos], ["de outro poço (pasta trocada)", r.agp_de_outro_poco]]) {
      const tr = el("tr");
      tr.append(el("th", "", rot), el("td", "n", numero(n, 0)));
      ta.appendChild(tr);
    }
    box.appendChild(ta);
  }
  if (r.atualizado_em) box.appendChild(el("p", "ajuda", `Atualizado em ${dataCurta(r.atualizado_em)}.`));
}

async function exportarLevantamento() {
  const r = await chamar($("lv-exportar"), "exportar_levantamento", $("lv-bacia").value);
  if (r.ok) status(`Exportado: ${r.arquivos.join(" e ")}`, "ok");
}

// Chamado pelo motor a cada passo do levantamento.
window.eventoLevantamento = function (ev) {
  if (ev.tipo === "etapa") {
    $("lv-texto").textContent = ev.texto;
  } else if (ev.tipo === "listagem" || ev.tipo === "arquivo" || ev.tipo === "agp") {
    const fase = { listagem: "1/3 · ", arquivo: "2/3 · ", agp: "3/3 · " }[ev.tipo];
    $("lv-texto").textContent = `${fase}${ev.texto} (${numero(ev.feito, 0)} de ${numero(ev.total, 0)})`;
    $("lv-texto").title = ev.texto;
    $("lv-barra").style.width = ev.total ? (100 * ev.feito / ev.total).toFixed(1) + "%" : "0%";
    if (ev.tipo === "listagem" && ev.feito === ev.total && !$("vista-mapa").hidden) consultarMapa();
  } else if (["fim", "cancelado", "erro"].includes(ev.tipo)) {
    lvAtivo = false;
    mostrarAtivo(false);
    if (ev.tipo === "fim") {
      status(`Levantamento concluído: ${numero(ev.pocos, 0)} poço(s), ${numero(ev.arquivos_lidos, 0)} arquivo(s) conferidos pelo conteúdo` +
             (ev.agps_lidos ? `, ${numero(ev.agps_lidos, 0)} AGP(s) lidos.` : "."), "ok");
    } else if (ev.tipo === "cancelado") {
      status("Levantamento cancelado. O que já foi lido fica salvo; levante de novo para continuar.", "ok");
    } else {
      status(`Levantamento interrompido: ${ev.erro}. O que já foi lido fica salvo.`, "erro");
    }
    carregarLevantamento();
    if (!$("vista-mapa").hidden) {
      $("f-cor").value = "acervo";
      trocarCorMapa();
    }
  }
};

// ------------------------------------------------ ficha do poço: o que há no portal
function secaoAcervoFicha(corpo, acervo) {
  if (!acervo || !acervo.length) return;
  corpo.appendChild(el("h3", "", `No acervo do REATE (${acervo.length} arquivo(s) de perfil)`));
  const ul = el("ul", "dic-lista acervo-lista");
  for (const a of acervo) {
    const li = el("li");
    const fmt = a.formato || "";
    const conferido = a.verificado === "conteudo";
    const tipoFmt = ["dlis", "lis", "las"].includes(fmt) ? "perfil" : ["tiff", "pdf", "png", "jpg"].includes(fmt) ? "documento" : "outro";
    const selo = el("span", "fmt " + tipoFmt, (NOMES_FORMATO[fmt] || (fmt || "?")) + (a.envelope === "tif" ? " em fita" : ""));
    selo.title = conferido ? "Conferido pelo conteúdo do arquivo" : "Pela extensão (não conferido)";
    if (!conferido) selo.textContent += " ?";
    const nome = el("span", "", `${a.pasta ? a.pasta + "/" : ""}${a.nome} · ${tamanho(a.tamanho)}`);
    nome.title = a.caminho;
    li.append(selo, nome);
    const lista = a.curvas ? JSON.parse(a.curvas) : [];
    if (lista.length) {
      const c = el("span", "ajuda", `${lista.length} curva(s)${a.curvas_completas ? "" : "+"}`);
      c.title = lista.join(" ") + (a.curvas_completas ? "" : "\n(lista do começo do arquivo; pode haver mais)");
      li.appendChild(c);
    }
    if (a.erro) li.appendChild(el("span", "ajuda", a.erro));
    ul.appendChild(li);
  }
  corpo.appendChild(ul);
}

// ------------------------------------------------ ficha do poço: AGP da ANP
const NIVEL_AGP = { F: "Formação", M: "Membro", G: "Grupo", S: "Supergrupo", C: "Camadas" };
const TIP_AGP = { L: "litoestratigráfica", C: "cronoestratigráfica", M: "marco", D: "discordância", O: "ostracodes",
                  Q: "sequência estratigráfica" };

function secaoAgpFicha(corpo, agps) {
  if (!agps || !agps.length) return;
  const g = agps[0];
  corpo.appendChild(el("h3", "", "AGP — dados gerais do poço (ANP)"));
  if (g.confere === 0) {
    corpo.appendChild(el("p", "agp-aviso", `Este AGP (${g.cabecalho.poco_agp}) estava na pasta de ${g.poco_pasta} no portal.`));
  }
  const c = g.cabecalho || {};
  const t = el("table", "tabela ficha");
  linhaFicha(t, "Classificação", [c.classificacao, c.reclassificacao].filter(Boolean).join(" · "));
  linhaFicha(t, "Prof. final (sondador)", c.prof_final != null ? `${numero(c.prof_final, 1)} m` : "");
  linhaFicha(t, "Formação na prof. final", c.formacao_pf);
  linhaFicha(t, "Mesa rotativa", c.mesa_rotativa != null ? `${numero(c.mesa_rotativa, 1)} m` : "");
  linhaFicha(t, "Datum", c.datum);
  linhaFicha(t, "Cota altimétrica", c.bap != null ? `${numero(c.bap, 1)} m` : "");
  if (c.sigla_pais && c.sigla_pais_id !== c.poco_id) linhaFicha(t, "Nome antigo (Petrobras)", c.sigla_pais);
  corpo.appendChild(t);
  const us = (g.unidades || []).filter((u) => u.tip === "L");
  if (us.length) {
    const tu = el("table", "tabela agp-tabela");
    const cab = el("tr");
    for (const h of ["Unidade", "Topo (m)", "Base (m)", "Fonte"]) cab.appendChild(el("th", "", h));
    tu.appendChild(cab);
    for (const u of us) {
      const tr = el("tr");
      const nome = el("td", "", `${NIVEL_AGP[u.nivel] || ""} ${u.nome}`.trim());
      nome.title = `${u.sigla}${u.codigo ? ` · código ${u.codigo}` : ""} · ${u.tipo_desc || TIP_AGP[u.tip] || u.tip}` +
        (u.qualidade ? ` · qualidade: ${u.qualidade}` : "") + (u.metodo_desc ? ` · método: ${u.metodo_desc}` : "") +
        (u.desc_topo ? ` · topo: ${u.desc_topo}` : "");
      tr.append(nome, el("td", "", numero(u.topo, 1)), el("td", "", u.base == null ? "—" : numero(u.base, 1)),
                el("td", "", [u.fonte, u.data && u.data !== "01/01/1900" ? u.data : ""].filter(Boolean).join(" · ")));
      tu.appendChild(tr);
    }
    corpo.appendChild(tu);
  }
  const extras = [];
  if ((g.zonas || []).length) extras.push(`${g.zonas.length} zona(s)-reservatório`);
  if ((g.indicios || []).length) extras.push(`${g.indicios.length} indício(s) de hidrocarboneto`);
  if ((g.testes || []).length) extras.push(`${g.testes.length} teste(s) de formação`);
  if ((g.revestimentos || []).length) extras.push(`${g.revestimentos.length} revestimento(s)`);
  if ((g.litologia || []).length) extras.push(`litologia descrita em ${g.litologia.length} camada(s) (trilha na aba Perfis)`);
  for (const cr of g.corridas || []) {
    const partes = [];
    if (cr.rm != null) partes.push(`Rm ${numero(cr.rm, 3)}${cr.t_rm != null ? ` a ${numero(cr.t_rm, 1)} °F` : ""}`);
    if (cr.rmf != null) partes.push(`Rmf ${numero(cr.rmf, 3)}${cr.t_rmf != null ? ` a ${numero(cr.t_rmf, 1)} °F` : ""}`);
    if (cr.bht != null) partes.push(`BHT ${numero(cr.bht, 0)} °F`);
    if (partes.length) extras.push(`corrida ${cr.corrida}: ${partes.join(", ")}`);
  }
  if (extras.length) corpo.appendChild(el("p", "ajuda", extras.join(" · ")));
  for (const ts of (g.testes || []).slice(0, 5)) {
    const p = el("p", "ajuda", `Teste ${ts.numero} (${ts.data}) ${numero(ts.topo, 1)}–${numero(ts.base, 1)} m: ${ts.resultado || "—"}` +
      (ts.salinidade_ppm ? ` · salinidade ${numero(ts.salinidade_ppm, 0)} ppm` : ""));
    p.title = ts.observacoes || "";
    corpo.appendChild(p);
  }
  const ids = (g.unidades || []).some((u) => u.tip === "L") ? (c.poco_id || g.poco_pasta) : "";
  if (ids) {
    const bs = el("button", "btn-abrir", "Adicionar à seção");
    bs.type = "button";
    bs.title = "Põe o poço na lista da aba Seção (seção estratigráfica)";
    bs.onclick = () => adicionarPocoSecao(ids);
    corpo.appendChild(bs);
  }
  if (g.arquivo_local) {
    const b = el("button", "btn-abrir", "Abrir o AGP");
    b.type = "button";
    b.title = "Abrir o texto completo no programa do computador";
    b.onclick = () => chamar(b, "abrir_agp", g.arquivo_local);
    corpo.appendChild(b);
  }
}

function ligarLevantamento() {
  ligar("lv-carregar", "onclick", carregarCategoriasLevantamento);
  ligar("lv-iniciar", "onclick", iniciarLevantamento);
  ligar("lv-cancelar", "onclick", async () => {
    await chamar($("lv-cancelar"), "cancelar_levantamento");
    $("lv-texto").textContent = "Cancelando… termina o arquivo atual.";
  });
  ligar("lv-exportar", "onclick", exportarLevantamento);
  ligar("lv-pasta", "onclick", () => chamar($("lv-pasta"), "abrir_pasta_levantamento"));
  $("lv-bacia").onchange = () => { reiniciarCategorias(); carregarLevantamento(); };
}
