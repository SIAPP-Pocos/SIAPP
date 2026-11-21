// SIAPP — aba Comunidade, em três partes:
//   Contribuir   autoria, exportar/importar pacotes e base comunitária;
//   Painel       quanto do acervo está preenchido, quem contribuiu e onde ajudar (0.35);
//   Biblioteca   interpretações de perfil compartilhadas: ver, comparar e refazer (0.35).
"use strict";

const ORIGENS_COM = { local: "sua", pacote: "pacote", base: "base", "não compartilhada": "não compartilhada" };

function descreverItens(it) {
  const p = [];
  if (it.correcoes) p.push(`${it.correcoes} correção(ões)`);
  if (it.palavras) p.push(`${it.palavras} palavra(s)`);
  if (it.manter_original) p.push(`${it.manter_original} “OCR estava certo”`);
  if (it.fatos) p.push(`${it.fatos} dado(s) transcrito(s)`);
  if (it.apelidos) p.push(`${it.apelidos} nome(s) de poço`);
  if (it.interpretacoes) p.push(`${it.interpretacoes} interpretação(ões) de perfil`);
  return p.join(" · ") || "nada";
}

// A aba abre na parte escolhida (ui.subCom, lembrada nas preferências).
async function carregarComunidade() {
  if (!projetoAberto) {
    $("com-local").textContent = "Abra o projeto primeiro (Início).";
    $("pn-sub").textContent = "Abra o projeto primeiro (Início).";
    $("bib-resumo").textContent = "Abra o projeto primeiro (Início).";
    return;
  }
  if (ui.subCom === "painel") return carregarPainelCom();
  if (ui.subCom === "biblioteca") return carregarBiblioteca();
  return carregarContribuir();
}

async function carregarContribuir() {
  const r = await chamar(null, "comunidade");
  if (!r.ok) return;
  const a = r.autor || {};
  $("autor-nome").value = a.nome || "";
  $("autor-inst").value = a.instituicao || "";
  $("autor-orcid").value = a.orcid || "";
  const l = r.local;
  $("com-local").textContent =
    `Neste computador: ${l.correcoes} correção(ões), ${l.palavras} palavra(s), ` +
    `${l.manter_original} “OCR estava certo”, ${l.fatos} dado(s) transcrito(s), ` +
    `${l.interpretacoes} interpretação(ões) de perfil. ` +
    (r.ultima_exportacao ? `Última exportação: ${dataCurta(r.ultima_exportacao)}.` : "Nada exportado ainda.");
  $("com-base").textContent = r.base
    ? `Base ${r.base.resumo.versao} aplicada em ${dataCurta(r.base.aplicado_em)}: ` +
      `${r.base.resumo.contribuicoes} contribuição(ões), ${r.base.resumo.vocabulario} item(ns) de vocabulário, ` +
      `${r.base.resumo.fatos} dado(s).`
    : "Nenhuma base aplicada ainda.";
  desenharPacotes(r.importados);
}

function desenharPacotes(lista) {
  const ul = limpar($("lista-pacotes"));
  if (!lista.length) { ul.appendChild(el("li", "vazio-lista", "Nenhum.")); return; }
  for (const p of lista) {
    const li = el("li");
    const info = el("div");
    info.append(el("strong", "", p.autor || "sem autor"),
                el("span", "ajuda", ` · ${dataCurta(p.criado_em)} · ${descreverItens(p.resumo)}`));
    const b = el("button", "btn secundario pequeno", "Desfazer");
    b.title = "Remove tudo o que este pacote trouxe";
    b.onclick = async () => {
      const r = await chamar(b, "desfazer_pacote", p.id);
      if (r.ok) { status(`Pacote de ${p.autor} desfeito. ${r.paginas_atualizadas} página(s) atualizadas.`, "ok"); carregarContribuir(); }
    };
    li.append(info, b);
    ul.appendChild(li);
  }
}

async function salvarAutor(ev) {
  ev.preventDefault();
  const r = await chamar($("btn-autor"), "definir_autor", $("autor-nome").value,
                         $("autor-inst").value, $("autor-orcid").value);
  if (r.ok) status(`Autoria salva: ${r.autor.nome}.`, "ok");
}

async function exportarPacote() {
  const r = await chamar($("btn-exportar"), "exportar_contribuicao", $("com-novos").checked);
  if (!r.ok) return;
  $("com-exportado").textContent = `Pacote gravado em ${r.arquivo} (${descreverItens(r.itens)}).`;
  status("Contribuição exportada. Envie o arquivo ao repositório Comunidade.", "ok");
  carregarContribuir();
}

async function escolherPacote() {
  const r = await chamar($("btn-importar"), "escolher_contribuicao");
  if (!r.ok || r.cancelado) return;
  const pv = r.previa;
  const box = limpar($("previa"));
  box.hidden = false;
  box.appendChild(el("p", "", ""));
  box.firstChild.append(el("strong", "", pv.autor.nome || "sem autor"),
    document.createTextNode(` · ${dataCurta(pv.criado_em)} · arquivo ${r.arquivo}`));
  box.appendChild(el("p", "ajuda", "Traz: " + descreverItens(pv.itens) +
    (pv.correcoes_repetidas ? ` · ${pv.correcoes_repetidas} correção(ões) que você já tem` : "") +
    (pv.fatos_repetidos ? ` · ${pv.fatos_repetidos} dado(s) que você já tem` : "") +
    (pv.interpretacoes_repetidas ? ` · ${pv.interpretacoes_repetidas} interpretação(ões) que você já tem` : "")));
  if (pv.ja_importado) box.appendChild(el("p", "aviso", "Este pacote já foi importado antes; importar de novo não duplica nada."));
  if (pv.conflitos.length) {
    box.appendChild(el("p", "aviso", `${pv.conflitos.length} correção(ões) discordam das que você já usa. A sua continua valendo; a do pacote fica guardada.`));
    const t = el("table", "tabela");
    const cab = el("tr");
    for (const h of ["O OCR leu", "Você usa", "O pacote propõe"]) cab.appendChild(el("th", "", h));
    t.appendChild(cab);
    for (const c of pv.conflitos.slice(0, 50)) {
      const tr = el("tr");
      tr.append(el("td", "mono", c.de), el("td", "mono", c.atual), el("td", "mono", c.proposta));
      t.appendChild(tr);
    }
    box.appendChild(t);
  }
  const linha = el("div", "linha");
  const ok = el("button", "btn", "Importar");
  ok.onclick = async () => {
    const r2 = await chamar(ok, "confirmar_importacao", pv.id);
    if (!r2.ok) return;
    box.hidden = true;
    status(`Pacote importado: ${descreverItens(r2.resumo)}. ${r2.paginas_atualizadas} página(s) atualizadas.`, "ok");
    carregarContribuir();
  };
  const nao = el("button", "btn secundario", "Cancelar");
  nao.onclick = () => { box.hidden = true; };
  linha.append(ok, nao);
  box.appendChild(linha);
}

async function atualizarBase(botao, funcao) {
  const r = await chamar(botao, funcao);
  if (!r.ok || r.cancelado) return;
  status(`Base ${r.resumo.versao} aplicada: ${r.resumo.contribuicoes} contribuição(ões), ` +
         `${r.resumo.fatos} dado(s)` + (r.resumo.interpretacoes ? `, ${r.resumo.interpretacoes} interpretação(ões)` : "") +
         `. ${r.paginas_atualizadas} página(s) atualizadas.`, "ok");
  carregarContribuir();
}

// ================================================================== painel
const pn = { dados: null };

async function carregarPainelCom() {
  const r = await chamar($("pn-atualizar"), "painel_comunidade", $("pn-bacia").value);
  if (!r.ok) return;
  pn.dados = r;
  const sel = $("pn-bacia"), atual = sel.value;
  limpar(sel).appendChild(new Option("Todas", ""));
  for (const b of r.bacias) sel.appendChild(new Option(b, b));
  sel.value = r.bacias.includes(atual) ? atual : "";
  $("pn-titulo").textContent = r.bacia ? `Preenchimento do acervo · ${r.bacia}` : "Preenchimento do acervo";
  $("pn-sub").textContent = r.total
    ? `${numero(r.total, 0)} poço(s) ` + (r.levantamento ? "com pasta no REATE" : "com algum dado no projeto (faça o levantamento do acervo para a base completa)") +
      ` · ${r.global.autores} contribuidor(es) · ${numero(r.global.correcoes, 0)} correção(ões) do OCR valendo em todos os documentos` +
      (r.avaliacoes_nao_compartilhadas ? ` · ${r.avaliacoes_nao_compartilhadas} avaliação(ões) sua(s) ainda não compartilhada(s)` : "")
    : "Nenhum poço ainda. Faça o levantamento do acervo (Dados) ou baixe arquivos do REATE.";
  desenharKpis(r);
  desenharPorBacia(r);
  desenharContribuidores(r);
  desenharAtividade(r);
  desenharAjudar(r);
}

function barraPct(pct) {
  const b = el("div", "pn-barra");
  const f = el("span");
  f.style.width = `${Math.max(0, Math.min(100, pct || 0))}%`;
  b.appendChild(f);
  return b;
}

function desenharKpis(r) {
  const box = limpar($("pn-kpis"));
  for (const i of r.indicadores) {
    const c = el("div", "pn-kpi");
    c.dataset.ind = i.chave;
    c.title = i.explicacao;
    const n = el("strong", "", numero(i.n, 0));
    const pct = el("span", "pn-pct", i.pct === null ? "" : `${numero(i.pct, 1)}%`);
    const topo = el("div", "pn-kpi-num");
    topo.append(n, pct);
    c.append(topo, barraPct(i.pct), el("span", "pn-kpi-nome", i.nome));
    box.appendChild(c);
  }
}

function celulaPct(n, total) {
  const td = el("td", "nr");
  td.textContent = numero(n, 0);
  if (total) {
    const p = el("small", "", ` ${numero(100 * n / total, 0)}%`);
    td.appendChild(p);
  }
  return td;
}

// Nomes curtos para o cabeçalho das tabelas (o nome inteiro vai no title).
const CURTOS_PN = { documentos: "Docs", perfil: "Perfil", topos: "Topos", topos_transcritos: "Topos transcr.",
  transcricoes: "Dados", revisadas: "Pág. revisadas", interpretacoes: "Interpret.", producao: "Produção" };

function desenharPorBacia(r) {
  const t = limpar($("pn-bacias"));
  const cab = el("tr");
  const colunas = r.indicadores.map((i) => i.chave);
  cab.append(el("th", "", "Bacia"), el("th", "nr", "Poços"));
  for (const i of r.indicadores) {
    const th = el("th", "nr", CURTOS_PN[i.chave] || i.nome);
    th.title = `${i.nome}: ${i.explicacao}`;
    cab.appendChild(th);
  }
  const thead = el("thead");
  thead.appendChild(cab);
  t.appendChild(thead);
  const tb = el("tbody");
  for (const b of r.por_bacia) {
    const tr = el("tr");
    const nome = el("td");
    const link = el("button", "link", b.bacia);
    link.title = "Mostrar só esta bacia";
    link.onclick = () => { $("pn-bacia").value = b.bacia === "sem bacia" ? "" : b.bacia; carregarPainelCom(); };
    nome.appendChild(link);
    const tot = el("td", "nr", numero(b.total, 0));
    if (b.cadastro) tot.title = `${numero(b.cadastro, 0)} poço(s) no cadastro da ANP nesta bacia`;
    tr.append(nome, tot, ...colunas.map((k) => celulaPct(b[k], b.total)));
    tb.appendChild(tr);
  }
  if (!r.por_bacia.length) {
    const tr = el("tr");
    const td = el("td", "vazio-lista", "Nada ainda.");
    td.colSpan = colunas.length + 2;
    tr.appendChild(td);
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}

function desenharContribuidores(r) {
  const t = limpar($("pn-contrib"));
  const tipos = Object.keys(r.tipos);
  $("pn-contrib-sub").textContent = r.contribuidores.length
    ? "Cada linha soma o que tem o nome da pessoa gravado. “sua” = feito neste computador; “pacote” e “base” = veio da comunidade."
    : "Ninguém ainda. Transcreva um dado, corrija o OCR ou compartilhe uma interpretação.";
  if (!r.contribuidores.length) return;
  const cab = el("tr");
  const CURTOS = { fatos: "Dados", topos: "Topos", correcoes: "Correções", palavras: "Palavras", paginas: "Páginas", interpretacoes: "Interpret." };
  cab.append(el("th", "", "Autor"), el("th", "nr", "Total"));
  for (const k of tipos) { const th = el("th", "nr", CURTOS[k] || r.tipos[k]); th.title = r.tipos[k]; cab.appendChild(th); }
  for (const h of ["Poços", "Origem", "Período"]) cab.appendChild(el("th", h === "Poços" ? "nr" : "", h));
  const thead = el("thead");
  thead.appendChild(cab);
  t.appendChild(thead);
  const tb = el("tbody");
  const maior = Math.max(...r.contribuidores.map((d) => d.total), 1);
  for (const d of r.contribuidores) {
    const tr = el("tr", d.voce ? "voce" : "");
    const nome = el("td");
    nome.append(el("span", "", d.autor));
    if (d.voce) nome.append(el("span", "selo o-local", "você"));
    const total = el("td", "nr pn-total");
    total.append(el("span", "", numero(d.total, 0)));
    const b = el("span", "pn-mini");
    b.style.width = `${Math.round(48 * d.total / maior)}px`;
    total.appendChild(b);
    const org = el("td");
    for (const o of d.origens) org.appendChild(el("span", `selo o-${o}`, ORIGENS_COM[o] || o));
    const per = d.primeira ? (d.primeira.slice(0, 7) === d.ultima.slice(0, 7) ? dataCurta(d.ultima.slice(0, 10))
      : `${dataCurta(d.primeira.slice(0, 10))} a ${dataCurta(d.ultima.slice(0, 10))}`) : "—";
    tr.append(nome, total, ...tipos.map((k) => el("td", "nr" + (d[k] ? "" : " zero"), d[k] ? numero(d[k], 0) : "·")),
              el("td", "nr", numero(d.pocos, 0)), org, el("td", "", per));
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}

// Barras empilhadas por tipo de contribuição, em SVG (cores do tema, nada de imagem).
function desenharAtividade(r) {
  const box = limpar($("pn-atividade"));
  const meses = r.atividade;
  if (!meses.length) { box.appendChild(el("p", "ajuda", "Sem contribuições com data ainda.")); return; }
  const tipos = Object.keys(r.tipos);
  const NS = "http://www.w3.org/2000/svg";
  const L = 420, A = 150, mE = 28, mB = 22, larg = Math.min((L - mE - 6) / meses.length, 48);
  const barra = Math.max(2, Math.min(larg * 0.7, 28));
  const max = Math.max(...meses.map((m) => m.total), 1);
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${L} ${A}`);
  svg.setAttribute("class", "pn-svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Contribuições por mês");
  const linha = (y, txt) => {
    const g = document.createElementNS(NS, "line");
    g.setAttribute("x1", mE); g.setAttribute("x2", L - 4); g.setAttribute("y1", y); g.setAttribute("y2", y);
    g.setAttribute("class", "pn-grade");
    svg.appendChild(g);
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", mE - 4); t.setAttribute("y", y + 3); t.setAttribute("text-anchor", "end");
    t.setAttribute("class", "pn-eixo");
    t.textContent = txt;
    svg.appendChild(t);
  };
  const yDe = (v) => A - mB - (A - mB - 8) * v / max;
  linha(yDe(0), "0");
  linha(yDe(max), numero(max, 0));
  meses.forEach((m, k) => {
    let base = 0;
    const x = mE + 6 + k * larg + (larg - barra) / 2;
    for (const [i, tp] of tipos.entries()) {
      if (!m[tp]) continue;
      const r1 = document.createElementNS(NS, "rect");
      r1.setAttribute("x", x.toFixed(1));
      r1.setAttribute("width", barra.toFixed(1));
      r1.setAttribute("y", yDe(base + m[tp]).toFixed(1));
      r1.setAttribute("height", Math.max(1, yDe(base) - yDe(base + m[tp])).toFixed(1));
      r1.setAttribute("class", `pn-t${i}`);
      const tt = document.createElementNS(NS, "title");
      tt.textContent = `${m.mes}: ${m[tp]} ${r.tipos[tp].toLowerCase()}`;
      r1.appendChild(tt);
      svg.appendChild(r1);
      base += m[tp];
    }
    if (meses.length <= 12 || k % Math.ceil(meses.length / 12) === 0) {
      const t = document.createElementNS(NS, "text");
      t.setAttribute("x", (x + barra / 2).toFixed(1));
      t.setAttribute("y", A - 6);
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("class", "pn-eixo");
      t.textContent = `${m.mes.slice(5)}/${m.mes.slice(2, 4)}`;
      svg.appendChild(t);
    }
  });
  box.appendChild(svg);
  const leg = el("div", "pn-legenda");
  tipos.forEach((tp, i) => {
    if (!meses.some((m) => m[tp])) return;
    const it = el("span");
    it.append(el("i", `pn-t${i}`), document.createTextNode(r.tipos[tp]));
    leg.appendChild(it);
  });
  box.appendChild(leg);
}

function desenharAjudar(r) {
  const box = limpar($("pn-ajudar"));
  for (const a of r.ajudar) {
    const sec = el("div", "pn-ajuda-item");
    sec.append(el("h3", "", `${a.titulo} (${numero(a.total, 0)})`), el("p", "ajuda", a.explicacao));
    if (!a.pocos.length) { sec.appendChild(el("p", "ajuda", "Nenhum.")); box.appendChild(sec); continue; }
    const ul = el("ul", "pn-pocos");
    for (const p of a.pocos) {
      const li = el("li");
      const b = el("button", "link", p.poco);
      b.title = "Abrir a ficha do poço no mapa";
      b.onclick = () => irPara("mapa", "abrirFicha", p.poco);
      li.append(b, el("span", "ajuda", ` ${p.bacia ? p.bacia + " · " : ""}${p.n} ${a.unidade}`));
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    if (a.total > a.pocos.length) sec.appendChild(el("p", "ajuda", `e mais ${numero(a.total - a.pocos.length, 0)}.`));
    box.appendChild(sec);
  }
}

// ============================================================== biblioteca
const bib = { lista: [], selecionadas: new Set(), detalhe: null, timer: null };

function filtrosBiblioteca() {
  return { texto: $("bib-texto").value, bacia: $("bib-bacia").value, origem: $("bib-origem").value,
           poco: bib.poco || "" };
}

async function carregarBiblioteca() {
  const r = await chamar(null, "biblioteca", filtrosBiblioteca());
  if (!r.ok) return;
  bib.lista = r.interpretacoes;
  const sel = $("bib-bacia"), atual = sel.value;
  limpar(sel).appendChild(new Option("Todas", ""));
  for (const b of r.bacias) sel.appendChild(new Option(b, b));
  sel.value = r.bacias.includes(atual) ? atual : "";
  const visiveis = new Set([...r.interpretacoes.map((i) => i.id), ...r.nao_compartilhadas.map((e) => "exec:" + e.id)]);
  for (const id of [...bib.selecionadas]) if (!visiveis.has(id)) bib.selecionadas.delete(id);
  $("bib-resumo").textContent = r.total
    ? `${r.interpretacoes.length} de ${r.total} interpretação(ões) na biblioteca` +
      (bib.poco ? ` · só o poço ${bib.poco}` : "") + (r.autores.length ? ` · ${r.autores.length} autor(es)` : "")
    : "A biblioteca está vazia. Compartilhe uma avaliação de formação (aba Perfis) ou atualize a base comunitária.";
  desenharBiblioteca(r);
  atualizarSelecaoBib();
  if (bib.detalhe && !r.interpretacoes.some((i) => i.id === bib.detalhe)) {
    bib.detalhe = null;
    limpar($("bib-detalhe")).appendChild(el("p", "ajuda", "Escolha uma interpretação para ver os parâmetros e os intervalos."));
  }
}

function caixaSelecao(id) {
  const cb = el("input");
  cb.type = "checkbox";
  cb.className = "bib-marca";
  cb.checked = bib.selecionadas.has(id);
  cb.title = "Marcar para comparar";
  cb.setAttribute("aria-label", "Marcar para comparar");
  cb.onclick = (e) => {
    e.stopPropagation();
    if (cb.checked) bib.selecionadas.add(id); else bib.selecionadas.delete(id);
    atualizarSelecaoBib();
  };
  return cb;
}

function textoIntervalos(ints) {
  return ints.map((i) => `${i.nome || "—"} ${numero(i.topo, 0)}–${numero(i.base, 0)} m`).join(" · ");
}

function desenharBiblioteca(r) {
  const box = limpar($("bib-lista"));
  const porPoco = new Map();
  for (const i of r.interpretacoes) {
    if (!porPoco.has(i.poco)) porPoco.set(i.poco, []);
    porPoco.get(i.poco).push(i);
  }
  if (bib.poco) {
    const f = el("div", "bib-filtro-poco");
    f.append(el("span", "", `Só o poço ${bib.poco}`));
    const x = el("button", "btn secundario pequeno", "Mostrar todos");
    x.onclick = () => { bib.poco = ""; carregarBiblioteca(); };
    f.appendChild(x);
    box.appendChild(f);
  }
  if (!r.interpretacoes.length) box.appendChild(el("p", "ajuda", r.total ? "Nada com esses filtros." : ""));
  for (const [poco, itens] of porPoco) {
    const g = el("section", "bib-poco");
    const cab = el("h3");
    const b = el("button", "link", poco);
    b.title = "Mostrar só este poço";
    b.onclick = () => mostrarBibliotecaDoPoco(poco);
    cab.appendChild(b);
    const info = [itens[0].campo, itens[0].bacia].filter(Boolean).join(" · ");
    if (info) cab.appendChild(el("span", "ajuda", " " + info));
    g.appendChild(cab);
    for (const i of itens) g.appendChild(cartaoInterpretacao(i));
    box.appendChild(g);
  }
  const nao = r.nao_compartilhadas;
  $("bib-nao").hidden = !nao.length || $("bib-origem").value === "pacote" || $("bib-origem").value === "base";
  const nl = limpar($("bib-nao-lista"));
  for (const e of nao) nl.appendChild(cartaoNaoCompartilhada(e));
}

function cartaoInterpretacao(i) {
  const c = el("article", "bib-item" + (bib.detalhe === i.id ? " ativo" : ""));
  c.dataset.id = i.id;
  c.tabIndex = 0;
  const topo = el("div", "bib-item-topo");
  topo.append(caixaSelecao(i.id), el("strong", "", i.titulo || "sem título"));
  topo.appendChild(el("span", `selo o-${i.origem}`, ORIGENS_COM[i.origem] || i.origem));
  if (!i.tem_arquivo) {
    const s = el("span", "selo falta", "sem o arquivo");
    s.title = `Você não tem ${i.arquivo_nome || "o arquivo"}: dá para ver e comparar, não para refazer.`;
    topo.appendChild(s);
  }
  const t = i.totais;
  c.append(topo,
    el("p", "bib-meta", `${i.autor || "sem autor"} · ${dataCurta(i.criado_em)} · ${i.metodos}`),
    el("p", "bib-ints", textoIntervalos(i.intervalos)),
    el("p", "bib-num", `net pay ${numero(t.net_pay_m, 1)} m · φ ${numero(t.phi_pay, 3)} · Sw ${numero(t.sw_pay, 2)} · HPV ${numero(t.hpv_m, 2)} m`));
  c.onclick = () => abrirInterpretacaoBib(i.id);
  c.onkeydown = (e) => { if (e.key === "Enter") abrirInterpretacaoBib(i.id); };
  return c;
}

function cartaoNaoCompartilhada(e) {
  const id = "exec:" + e.id;
  const c = el("article", "bib-item nao");
  const topo = el("div", "bib-item-topo");
  topo.append(caixaSelecao(id), el("strong", "", `${e.poco} · ${e.arquivo_nome}`));
  const t = e.totais;
  const acoes = el("div", "linha");
  const b = el("button", "btn secundario pequeno", "Compartilhar…");
  const form = el("div", "form-compartilhar");
  form.hidden = true;
  b.onclick = () => formCompartilhar(form, e.id, () => carregarBiblioteca());
  acoes.appendChild(b);
  c.append(topo, el("p", "bib-meta", `${dataCurta(e.criado_em)} · ${e.metodos}`),
           el("p", "bib-ints", textoIntervalos(e.intervalos)),
           el("p", "bib-num", `net pay ${numero(t.net_pay_m, 1)} m · φ ${numero(t.phi_pay, 3)} · Sw ${numero(t.sw_pay, 2)}`),
           acoes, form);
  return c;
}

// Formulário curto (título e comentário) para compartilhar uma avaliação; usado aqui e na aba Perfis.
function formCompartilhar(box, execucao, aoTerminar, titulo = "", comentario = "") {
  limpar(box);
  box.hidden = false;
  const lt = el("label", "", "Título ");
  const it = el("input");
  it.type = "text";
  it.maxLength = 120;
  it.placeholder = "ex.: Açu inferior, Archie com Rw da lama do AGP";
  it.value = titulo;
  lt.appendChild(it);
  const lc = el("label", "", "Comentário (opcional) ");
  const tc = el("textarea");
  tc.rows = 3;
  tc.maxLength = 2000;
  tc.placeholder = "De onde veio o Rw, por que esse corte, dúvidas…";
  tc.value = comentario;
  lc.appendChild(tc);
  const linha = el("div", "linha");
  const ok = el("button", "btn pequeno", "Compartilhar");
  const nao = el("button", "btn secundario pequeno", "Cancelar");
  nao.onclick = () => { box.hidden = true; };
  ok.onclick = async () => {
    const r = await chamar(ok, "publicar_interpretacao", execucao, it.value, tc.value);
    if (!r.ok) return;
    box.hidden = true;
    status(r.atualizada ? "Interpretação atualizada na biblioteca. Vai de novo no próximo pacote."
                        : "Interpretação na biblioteca. Ela vai no próximo pacote que você exportar (Comunidade › Contribuir).", "ok");
    if (aoTerminar) aoTerminar(r);
  };
  linha.append(ok, nao);
  box.append(lt, lc, el("p", "ajuda", "Vão o poço, o arquivo (pelo hash), as curvas, os métodos, os parâmetros e o resumo dos intervalos, com o seu nome (CC-BY 4.0). As curvas calculadas não vão."), linha);
  it.focus();
}

function atualizarSelecaoBib() {
  const n = bib.selecionadas.size;
  $("bib-comparar").disabled = n < 2 || n > 6;
  $("bib-limpar-sel").hidden = !n;
  $("bib-sel").textContent = n === 0 ? "Marque de 2 a 6 para comparar (de preferência do mesmo poço)."
    : n === 1 ? "1 marcada: marque mais uma." : n > 6 ? `${n} marcadas: no máximo 6.` : `${n} marcadas.`;
}

async function abrirInterpretacaoBib(id) {
  const r = await chamar(null, "interpretacao", id);
  if (!r.ok) return;
  bib.detalhe = id;
  document.querySelectorAll("#bib-lista .bib-item").forEach((c) => c.classList.toggle("ativo", c.dataset.id === id));
  const box = limpar($("bib-detalhe"));
  const h = el("h2", "", r.titulo || "sem título");
  box.appendChild(h);
  const meta = el("p", "bib-meta");
  meta.append(el("span", `selo o-${r.origem}`, ORIGENS_COM[r.origem] || r.origem),
              document.createTextNode(` ${r.autor || "sem autor"} · ${dataCurta(r.criado_em)} · poço ${r.poco}` +
                (r.siapp_versao ? ` · SIAPP ${r.siapp_versao}` : "")));
  box.appendChild(meta);
  if (r.comentario) box.appendChild(el("p", "bib-comentario", r.comentario));
  const arq = el("p", "ajuda");
  arq.textContent = `Arquivo: ${r.arquivo_nome || "—"}` + (r.arquivo_caminho ? ` (${r.arquivo_caminho})` : "") +
    (r.arquivo_local ? ` · você tem este arquivo` + (r.arquivo_conferido_por === "sha256" ? " (mesmo hash)" : r.arquivo_conferido_por === "nome" ? " (pelo nome; o conteúdo pode ser outro)" : "")
                     : " · você ainda não tem este arquivo");
  box.appendChild(arq);
  const acoes = el("div", "linha");
  const refazer = el("button", "btn pequeno", "Refazer nos Perfis");
  refazer.disabled = !r.arquivo_local;
  refazer.title = r.arquivo_local ? "Abre o arquivo na aba Perfis com os intervalos, curvas e parâmetros desta interpretação"
                                  : "Baixe o arquivo antes (Acervo › Catálogo do REATE)";
  refazer.onclick = () => irPara("perfis", "abrirInterpretacaoNosPerfis", id);
  const doPoco = el("button", "btn secundario pequeno", "Outras deste poço");
  doPoco.onclick = () => mostrarBibliotecaDoPoco(r.poco);
  const ficha = el("button", "btn secundario pequeno", "Ficha no mapa");
  ficha.onclick = () => irPara("mapa", "abrirFicha", r.poco);
  acoes.append(refazer, doPoco, ficha);
  if (!r.arquivo_local) {
    const cat = el("button", "btn secundario pequeno", "Achar no Catálogo");
    cat.onclick = () => irPara("catalogo", "mostrarPocoNoCatalogo", r.poco);
    acoes.appendChild(cat);
  }
  if (r.pode_remover) {
    const rm = el("button", "btn secundario pequeno perigo", "Tirar da biblioteca");
    rm.onclick = async () => {
      const x = await chamar(rm, "remover_interpretacao", id);
      if (!x.ok) return;
      status(x.ja_exportada ? "Tirada da sua biblioteca. Ela já foi num pacote exportado: peça a remoção no repositório Comunidade se precisar."
                            : "Tirada da biblioteca.", "ok");
      bib.selecionadas.delete(id);
      bib.detalhe = null;
      carregarBiblioteca();
    };
    acoes.appendChild(rm);
  }
  box.appendChild(acoes);

  box.appendChild(el("h3", "", "Intervalos"));
  const t = el("table", "tabela bib-tabela");
  const cab = el("tr");
  for (const x of ["Intervalo", "Bruto", "Reserv.", "Net pay", "N/G", "φ pay", "Sw pay", "Vsh", "HPV"]) cab.appendChild(el("th", "", x));
  const thead = el("thead");
  thead.appendChild(cab);
  t.appendChild(thead);
  const tb = el("tbody");
  for (const i of r.intervalos_completos) {
    const tr = el("tr");
    tr.append(el("td", "", `${i.nome || "—"} (${numero(i.topo, 1)}–${numero(i.base, 1)})`),
      el("td", "nr", numero(i.bruto_m, 1)), el("td", "nr", numero(i.reservatorio_m, 1)),
      el("td", "nr destaque", numero(i.net_pay_m, 1)), el("td", "nr", numero(i.ntg, 2)),
      el("td", "nr", numero(i.phi_media_pay, 3)), el("td", "nr", numero(i.sw_media_pay, 2)),
      el("td", "nr", numero(i.vsh_medio, 2)), el("td", "nr", numero(i.hpv_m, 2)));
    tb.appendChild(tr);
  }
  t.appendChild(tb);
  box.appendChild(el("div", "tabela-rolar")).appendChild(t);

  box.appendChild(el("h3", "", "Métodos, curvas e parâmetros"));
  box.appendChild(el("p", "", r.metodos));
  const curvas = Object.entries(r.curvas_usadas).map(([p, c]) => `${p}: ${c.mnemonico}${c.unidade ? " (" + c.unidade + ")" : ""}`);
  if (curvas.length) box.appendChild(el("p", "ajuda", "Curvas: " + curvas.join(" · ")));
  const tp = el("table", "tabela ficha");
  for (const p of r.parametros) {
    const tr = el("tr");
    const v = el("td", "", typeof p.valor === "number" ? numero(p.valor, 4) : String(p.valor));
    if (p.auto) { v.appendChild(el("span", "selo", "auto")); v.title = p.auto; }
    tr.append(el("th", "", p.nome), v);
    tp.appendChild(tr);
  }
  box.appendChild(tp);
}

async function compararInterpretacoes(ids) {
  if (ids && ids.length) { bib.selecionadas = new Set(ids); atualizarSelecaoBib(); }
  const lista = [...bib.selecionadas];
  const r = await chamar($("bib-comparar"), "comparar_interpretacoes", lista);
  if (!r.ok) return;
  const box = limpar($("bib-comparacao"));
  box.hidden = false;
  const cab = el("div", "bib-comp-cab");
  cab.append(el("h2", "", "Comparação"));
  const fechar = el("button", "btn secundario pequeno", "Fechar");
  fechar.onclick = () => { box.hidden = true; };
  cab.appendChild(fechar);
  box.appendChild(cab);
  for (const a of r.avisos) box.appendChild(el("p", "aviso", a));
  box.appendChild(el("p", "ajuda", r.diferencas.length
    ? `Diferem em: ${r.diferencas.join(", ")}.` : "Mesmos métodos e parâmetros: a diferença só pode vir dos intervalos ou das curvas."));
  const t = el("table", "tabela bib-comp");
  const thead = el("thead");
  const h = el("tr");
  h.appendChild(el("th", "", ""));
  for (const it of r.itens) {
    const th = el("th");
    th.append(el("span", "", it.rotulo), el("small", "", `${it.autor || "—"} · ${ORIGENS_COM[it.origem] || it.origem}`));
    h.appendChild(th);
  }
  thead.appendChild(h);
  t.appendChild(thead);
  const tb = el("tbody");
  const secao = (titulo) => {
    const tr = el("tr", "secao");
    const td = el("td", "", titulo);
    td.colSpan = r.itens.length + 1;
    tr.appendChild(td);
    tb.appendChild(tr);
  };
  const linha = (nome, valores, difere = false, fmt = (v) => v ?? "—") => {
    const tr = el("tr", difere ? "difere" : "");
    tr.appendChild(el("th", "", nome));
    for (const v of valores) {
      const td = el("td", "nr");
      if (v && typeof v === "object" && "valor" in v) {
        td.textContent = v.valor === null || v.valor === undefined ? "—" : (typeof v.valor === "number" ? numero(v.valor, 4) : v.valor);
        if (v.auto) td.appendChild(el("span", "selo", "auto"));
      } else td.textContent = fmt(v);
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  };
  secao("Intervalos (casados pela profundidade)");
  for (const L of r.intervalos) {
    const nome = `${L.nomes.join(" / ") || "—"} · ${numero(L.topo, 0)}–${numero(L.base, 0)} m`;
    const tr = el("tr", L.net_pay_amplitude_m ? "difere" : "");
    const th = el("th", "", nome);
    if (L.net_pay_amplitude_m !== null) th.appendChild(el("small", "", ` diferença no net pay: ${numero(L.net_pay_amplitude_m, 1)} m`));
    tr.appendChild(th);
    for (const i of L.por_item) {
      tr.appendChild(el("td", "nr", i ? `${numero(i.net_pay_m, 1)} m · φ ${numero(i.phi_media_pay, 3)} · Sw ${numero(i.sw_media_pay, 2)}`
                                        : "não avaliou"));
    }
    tb.appendChild(tr);
  }
  secao("Totais");
  const casas = { phi_pay: 3, sw_pay: 2, vsh: 2, hpv_m: 2 };
  for (const L of r.totais) linha(L.nome, L.valores, false, (v) => numero(v, casas[L.chave] || 1));
  secao("Métodos");
  for (const L of r.metodos) linha(L.nome, L.valores, L.difere);
  if (r.curvas.length) {
    secao("Curvas");
    for (const L of r.curvas) linha(L.papel, L.valores, L.difere);
  }
  secao("Parâmetros");
  for (const L of r.parametros) linha(L.nome, L.valores, L.difere);
  t.appendChild(tb);
  box.appendChild(el("div", "tabela-rolar")).appendChild(t);
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Chamado de outras abas (irPara): a biblioteca só com um poço.
function mostrarBibliotecaDoPoco(poco) {
  bib.poco = poco;
  $("bib-texto").value = "";
  mostrarSubCom("biblioteca");
}

function mostrarSubCom(qual) {
  ui.subCom = qual;
  aplicarLayout(new Set(["comunidade"]));
  guardarLayout();
}

function ligarComunidade() {
  for (const b of document.querySelectorAll(".sub-nav [data-com]")) b.onclick = () => mostrarSubCom(b.dataset.com);
  $("pn-bacia").onchange = carregarPainelCom;
  $("pn-atualizar").onclick = carregarPainelCom;
  $("bib-texto").oninput = () => { clearTimeout(bib.timer); bib.timer = setTimeout(carregarBiblioteca, 250); };
  $("bib-bacia").onchange = carregarBiblioteca;
  $("bib-origem").onchange = carregarBiblioteca;
  $("bib-comparar").onclick = () => compararInterpretacoes();
  $("bib-limpar-sel").onclick = () => {
    bib.selecionadas.clear();
    document.querySelectorAll(".bib-marca").forEach((c) => { c.checked = false; });
    atualizarSelecaoBib();
  };
  $("form-autor").onsubmit = salvarAutor;
  $("btn-exportar").onclick = exportarPacote;
  $("btn-pasta-contrib").onclick = () => chamar($("btn-pasta-contrib"), "abrir_pasta_contribuicoes");
  $("btn-importar").onclick = escolherPacote;
  $("btn-base").onclick = () => atualizarBase($("btn-base"), "atualizar_base");
  $("btn-base-arquivo").onclick = () => atualizarBase($("btn-base-arquivo"), "importar_base_arquivo");
}
