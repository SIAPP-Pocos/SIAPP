// SIAPP — aba Seção: poços lado a lado, correlacionados pelos topos do AGP.
// O desenho (SVG) vem pronto do motor (motor/secao.py), o mesmo que é exportado.
"use strict";

const sec = { pocos: [], disponiveis: new Map(), ultima: null, unidades: [] };

async function carregarSecao() {
  if (!projetoAberto) return;
  const r = await chamar(null, "secao_pocos");
  if (r.ok) {
    sec.disponiveis = new Map(r.pocos.map((p) => [p.id, p]));
    const dl = limpar($("sec-lista-pocos"));
    for (const p of r.pocos) {
      const o = document.createElement("option");
      o.value = p.id;
      o.label = [p.campo, `${p.n_unidades} unidade(s)`].filter(Boolean).join(" · ");
      dl.appendChild(o);
    }
    $("sec-disponiveis").textContent = r.total
      ? `${numero(r.total, 0)} poço(s) com topos de formação no AGP e coordenadas no cadastro.`
      : "Nenhum poço com topos ainda: leia os AGPs no Levantamento do acervo (Acervo).";
  }
  desenharListaSecao();
  carregarHistoricoSecao();
}

function adicionarPocoSecao(id) {
  id = (id || "").trim().toUpperCase();
  if (!id) return;
  if (sec.pocos.includes(id)) { status(`${id} já está na seção.`); return; }
  if (sec.pocos.length >= 20) { status("No máximo 20 poços por seção.", "erro"); return; }
  sec.pocos.push(id);
  desenharListaSecao();
  status(`${id} na seção (${sec.pocos.length} poço(s)).`);
}

function desenharListaSecao() {
  const ol = limpar($("sec-lista"));
  $("sec-n").textContent = sec.pocos.length;
  sec.pocos.forEach((id, i) => {
    const li = el("li");
    const info = sec.disponiveis.get(id);
    const nome = el("span", "sec-nome", id);
    if (info) {
      nome.title = `${info.campo || "sem campo"} · ${info.n_unidades} unidade(s): ${info.siglas || ""}`;
    } else {
      nome.classList.add("sem-topos");
      nome.title = "Sem topos litoestratigráficos no AGP lido";
    }
    const acoes = el("span", "sec-acoes");
    for (const [rot, dica, fn] of [["↑", "Subir", () => moverPocoSecao(i, -1)], ["↓", "Descer", () => moverPocoSecao(i, 1)],
                                   ["×", "Tirar da seção", () => { sec.pocos.splice(i, 1); desenharListaSecao(); }]]) {
      const b = el("button", "sec-mini", rot);
      b.type = "button";
      b.title = dica;
      b.onclick = fn;
      acoes.appendChild(b);
    }
    li.append(nome, acoes);
    ol.appendChild(li);
  });
  if (!$("sec-datum-box").hidden) carregarDatumSecao();
}

function moverPocoSecao(i, d) {
  const j = i + d;
  if (j < 0 || j >= sec.pocos.length) return;
  [sec.pocos[i], sec.pocos[j]] = [sec.pocos[j], sec.pocos[i]];
  desenharListaSecao();
}

async function carregarDatumSecao() {
  const sel = $("sec-datum");
  const atual = sel.value;
  limpar(sel);
  if (sec.pocos.length < 2) return;
  const r = await chamar(null, "secao_unidades", sec.pocos);
  if (!r.ok) return;
  for (const u of r.unidades) {
    const o = document.createElement("option");
    o.value = u.chave;
    o.textContent = `${u.nome} (${u.pocos} de ${sec.pocos.length} poços)`;
    sel.appendChild(o);
  }
  if ([...sel.options].some((o) => o.value === atual)) sel.value = atual;
}

async function buscarCorredorSecao() {
  const a = $("sec-a").value.trim(), b = $("sec-b").value.trim();
  if (!a || !b) { status("Escolha os poços das duas pontas.", "erro"); return; }
  const r = await chamar($("sec-corredor"), "secao_corredor", a, b, $("sec-largura").value.replace(",", "."));
  if (!r.ok) return;
  sec.pocos = r.pocos.map((p) => p.id);
  $("sec-ordem").value = "linha";
  desenharListaSecao();
  $("sec-corredor-res").textContent =
    `${r.encontrados} poço(s) a até ${$("sec-largura").value} km da linha de ${numero(r.comprimento_km, 1)} km` +
    (r.encontrados > r.pocos.length ? `; ${r.pocos.length} escolhidos, espaçados por igual.` : ".");
}

// Da linha desenhada no mapa: os poços já vêm na ordem ao longo da linha.
async function receberPocosSecao(ids, comprimento) {
  if (!Array.isArray(ids) || ids.length < 2) return;
  if (!sec.disponiveis.size) await carregarSecao();
  sec.pocos = ids.slice(0, 20);
  $("sec-ordem").value = "lista";
  desenharListaSecao();
  $("sec-corredor-res").textContent = `${sec.pocos.length} poço(s) da linha desenhada no mapa` +
    (comprimento ? ` (${numero(comprimento, 1)} km), na ordem ao longo dela.` : ".");
  await montarSecao();
}

function opcoesSecao() {
  return {
    estilo: $("sec-estilo").value,
    ordem: $("sec-ordem").value, nivel: $("sec-nivel").value, eixo: $("sec-eixo").value,
    datum: $("sec-eixo").value === "nivelado" ? $("sec-datum").value : "",
    espacamento: $("sec-espacamento").value, gr: $("sec-gr").checked, litologia: $("sec-litologia").checked,
    y_topo: $("sec-ytopo").value, y_base: $("sec-ybase").value, limiar: $("sec-limiar").value,
    titulo: $("sec-titulo").value,
  };
}

async function montarSecao() {
  if (sec.pocos.length < 2) { status("Escolha ao menos dois poços.", "erro"); return; }
  status("Montando a seção…");
  const r = await chamar($("sec-montar"), "secao_montar", sec.pocos, opcoesSecao());
  if (!r.ok) return;
  mostrarSecao(r);
  status(`Seção com ${r.pocos.length} poço(s), ${numero(r.comprimento_km, 1)} km — registrada em execucoes/${r.id}.json`);
  carregarHistoricoSecao();
}

function mostrarSecao(r) {
  sec.ultima = r.id;
  $("sec-vazio").hidden = true;
  $("sec-painel").hidden = false;
  $("sec-exportado").textContent = "";
  // o SVG é gerado pelo próprio SIAPP (motor/secao.py), com todo texto escapado
  $("sec-figura").innerHTML = r.svg;
  // seção larga (muitos poços): tamanho real com rolagem, senão o texto fica ilegível
  const svg = $("sec-figura").querySelector("svg");
  const larga = svg && Number(svg.getAttribute("width")) > $("sec-figura").clientWidth * 1.35;
  $("sec-figura").classList.toggle("ajustada", !larga);
  const ul = limpar($("sec-avisos"));
  for (const a of r.avisos || []) ul.appendChild(el("li", "", a));
  desenharTabelaSecao(r.pocos && r.pocos.length && typeof r.pocos[0] === "object" ? r.pocos : null);
}

function desenharTabelaSecao(pocos) {
  const t = limpar($("sec-tabela"));
  if (!pocos) { t.appendChild(el("caption", "ajuda", "Abra o CSV para ver os topos desta seção.")); return; }
  const cab = el("tr");
  for (const h of ["Poço", "Distância (km)", "Unidade", "Topo (m)", "Base (m)", "Cota do topo (m)", "Espessura (m)", "Fonte"]) {
    cab.appendChild(el("th", "", h));
  }
  t.appendChild(cab);
  for (const p of pocos) {
    p.unidades.forEach((u, k) => {
      const tr = el("tr");
      tr.append(el("td", "", k ? "" : p.id), el("td", "", k ? "" : numero(p.x_km, 2)), el("td", "", u.nome),
                el("td", "", numero(u.topo, 1)),
                el("td", "", numero(u.base, 1) + (u.base_atingida ? "" : " (não atingida)")),
                el("td", "", numero(u.cota_topo, 1)),
                el("td", "", u.base == null ? "—" : numero(u.base - u.topo, 1)),
                el("td", "", [u.fonte, u.data !== "01/01/1900" ? u.data : "", u.qualidade].filter(Boolean).join(" · ")));
      t.appendChild(tr);
    });
  }
  const cap = el("caption", "nota-agp-cap");
  const nota = el("details", "nota-agp");
  nota.append(el("summary", "", "O que são \"fonte\" e \"qualidade\" (ex.: \"AGP antigo\", \"questionável\")?"),
              notaFonteAgp(el("div", "nota-agp-texto")));
  cap.appendChild(nota);
  t.appendChild(cap);
}

async function carregarHistoricoSecao() {
  const r = await chamar(null, "secao_execucoes");
  if (!r.ok) return;
  const ul = limpar($("sec-historico"));
  if (!r.execucoes.length) { ul.appendChild(el("li", "ajuda", "Nenhuma ainda.")); return; }
  for (const h of r.execucoes) {
    const li = el("li");
    const b = el("button", "link", `${(h.criado_em || "").slice(0, 16).replace("T", " ")} · ${h.pocos.length} poços`);
    b.type = "button";
    b.title = h.pocos.join(", ");
    b.onclick = () => abrirSecaoAnterior(h.id);
    li.appendChild(b);
    ul.appendChild(li);
  }
}

async function abrirSecaoAnterior(ident) {
  const r = await chamar(null, "secao_abrir", ident);
  if (!r.ok) return;
  sec.pocos = r.pocos.slice();
  const p = r.parametros || {};
  for (const [id, k] of [["sec-estilo", "estilo"], ["sec-ordem", "ordem"], ["sec-nivel", "nivel"], ["sec-eixo", "eixo"],
                         ["sec-espacamento", "espacamento"]]) {
    if (p[k]) $(id).value = p[k];
  }
  $("sec-datum-box").hidden = $("sec-eixo").value !== "nivelado";
  desenharListaSecao();
  mostrarSecao({ ...r, pocos: null });
  status(`Seção ${ident} reaberta (sem recalcular).`);
}

async function exportarSecao(botao) {
  if (!sec.ultima) return;
  const r = await chamar(botao, "secao_exportar", sec.ultima, botao.dataset.formato);
  if (r.ok) {
    $("sec-exportado").textContent = `Salvo na pasta do projeto: ${r.arquivo}`;
    status(`Seção exportada: ${r.arquivo}`);
  }
}

function ligarSecao() {
  ligar("sec-form-poco", "onsubmit", (ev) => {
    ev.preventDefault();
    adicionarPocoSecao($("sec-poco").value);
    $("sec-poco").value = "";
  });
  ligar("sec-limpar", "onclick", () => { sec.pocos = []; desenharListaSecao(); });
  ligar("sec-dados", "onclick", () => procurarDadosDosPocos(sec.pocos, `os ${sec.pocos.length} poço(s) da seção`));
  ligar("sec-corredor", "onclick", buscarCorredorSecao);
  ligar("sec-no-mapa", "onclick", () => irPara("mapa", "iniciarLinhaMapa"));
  ligar("sec-montar", "onclick", montarSecao);
  ligar("sec-eixo", "onchange", () => {
    $("sec-datum-box").hidden = $("sec-eixo").value !== "nivelado";
    if (!$("sec-datum-box").hidden) carregarDatumSecao();
  });
  ligar("sec-ajustar", "onclick", () => $("sec-figura").classList.add("ajustada"));
  ligar("sec-real", "onclick", () => $("sec-figura").classList.remove("ajustada"));
  ligar("sec-pasta", "onclick", () => chamar(null, "abrir_pasta_secoes"));
  for (const b of document.querySelectorAll("#sec-painel [data-formato]")) b.onclick = () => exportarSecao(b);
}
