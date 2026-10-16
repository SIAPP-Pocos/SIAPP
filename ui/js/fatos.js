// SIAPP — dados transcritos ("fatos"): cada valor com a fonte (documento, página, caixa).
"use strict";

const TIPOS_FATO = {
  topo_formacao: "Topo de formação",
  intervalo_alvo: "Intervalo-alvo",
  profundidade_final: "Profundidade final",
  revestimento: "Revestimento (sapata)",
  teste_formacao: "Teste de formação",
  canhoneio: "Canhoneio",
  mesa_rotativa: "Elevação da mesa rotativa",
  contato_fluido: "Contato de fluido",
  observacao: "Observação",
};

const ORIGEM_FATO = { local: "seu", pacote: "pacote", base: "comunidade" };

function profFato(f) {
  const t = f.prof_topo, b = f.prof_base;
  if (t === null && b === null) return "";
  if (t !== null && b !== null && b !== t) return `${numero(t, 2)}–${numero(b, 2)} m`;
  return `${numero(t !== null ? t : b, 2)} m`;
}

// Tabela de fatos; `aoRemover(f)` opcional mostra um × nos fatos locais.
function tabelaFatos(fatos, aoRemover) {
  const t = el("table", "tabela fatos");
  const cab = el("tr");
  for (const h of ["Tipo", "Nome / valor", "Profundidade", "Fonte", ""]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const f of fatos) {
    const tr = el("tr");
    const valor = [f.nome, f.valor && `${f.valor}${f.unidade ? " " + f.unidade : ""}`].filter(Boolean).join(" · ");
    const fonte = f.pagina ? `pág. ${f.pagina}` : (f.fonte_rel || f.fonte_caminho ? "documento" : "—");
    const tdFonte = el("td", "", fonte);
    tdFonte.title = [f.fonte_rel || f.fonte_caminho, f.autor && `por ${f.autor}`, ORIGEM_FATO[f.origem]].filter(Boolean).join("\n");
    const tdAcao = el("td");
    if (aoRemover && f.origem === "local") {
      const x = el("button", "x", "×");
      x.title = "Apagar este dado";
      x.onclick = () => aoRemover(f);
      tdAcao.appendChild(x);
    } else if (f.origem !== "local") {
      tdAcao.appendChild(el("span", "selo", ORIGEM_FATO[f.origem]));
    }
    tr.append(el("td", "", TIPOS_FATO[f.tipo] || f.tipo), el("td", "", valor || f.observacao || "—"),
              el("td", "mono", profFato(f)), tdFonte, tdAcao);
    t.appendChild(tr);
  }
  return t;
}

// ======================================================= transcrição assistida
// Na página de um documento: desenhar uma caixa na imagem, conferir a sugestão do
// OCR e salvar o dado com a fonte (documento, página, caixa).
const RE_NOME_POCO = /^\d{1,2}-?[A-Z]{1,7}-?\d{1,5}[A-Z]{0,3}-?[A-Z]{2,3}$/i;
const tr = { rel: null, pagina: null, palavras: [], caixa: null, fatos: [], arraste: null };

function iniciarTranscricao(r) {
  const outroDoc = tr.rel !== r.rel;
  Object.assign(tr, { rel: r.rel, pagina: r.pagina, palavras: r.palavras || [], fatos: r.fatos || [] });
  if (outroDoc || !$("tr-poco").value) $("tr-poco").value = r.poco_id || r.poco || "";
  limparCaixa();
  desenharFatosPagina();
}

function desenharFatosPagina() {
  $("tr-n").textContent = tr.fatos.length;
  const lista = limpar($("tr-lista"));
  if (tr.fatos.length) {
    lista.appendChild(tabelaFatos(tr.fatos, async (f) => {
      const r = await chamar(null, "remover_fato", f.id);
      if (r.ok) { tr.fatos = tr.fatos.filter((x) => x.id !== f.id); desenharFatosPagina(); }
    }));
  }
  const caixas = limpar($("pg-caixas"));
  for (const f of tr.fatos) {
    if (!f.caixa) continue;
    const d = el("div", "pg-caixa salva" + (f.caixa[0] > 0.55 ? " direita" : ""));
    posicionar(d, f.caixa);
    d.appendChild(el("span", "", [TIPOS_FATO[f.tipo], f.nome, profFato(f)].filter(Boolean).join(" · ")));
    caixas.appendChild(d);
  }
  if (tr.caixa) caixas.appendChild(caixaAtual());
}

function posicionar(div, [x0, y0, x1, y1]) {
  div.style.left = 100 * x0 + "%";
  div.style.top = 100 * y0 + "%";
  div.style.width = 100 * (x1 - x0) + "%";
  div.style.height = 100 * (y1 - y0) + "%";
}

function caixaAtual() {
  const d = el("div", "pg-caixa nova");
  d.id = "tr-caixa";
  posicionar(d, tr.caixa);
  return d;
}

function limparCaixa() {
  tr.caixa = null;
  $("tr-caixa-info").textContent = "Sem caixa marcada.";
  const atual = $("tr-caixa");
  if (atual) atual.remove();
}

function pontoNormalizado(ev) {
  const r = $("pg-img").getBoundingClientRect();
  return [Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)),
          Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height))];
}

function sugerirDoOCR(caixa) {
  const [x0, y0, x1, y1] = caixa;
  const dentro = tr.palavras.filter(([a, b, c, d]) => {
    const cx = (a + c) / 2, cy = (b + d) / 2;
    return cx >= x0 && cx <= x1 && cy >= y0 && cy <= y1;
  }).sort((p, q) => (Math.abs(p[1] - q[1]) > 0.008 ? p[1] - q[1] : p[0] - q[0]));
  const texto = dentro.map((p) => p[4]).join(" ").trim();
  $("tr-caixa-info").textContent = texto ? `O OCR leu na caixa: “${texto}”` : "O OCR não leu nada na caixa.";
  if (!texto) return;
  // nome de poço (7-GMR-13-RN) não é profundidade; números com decimal ou 2+ dígitos primeiro
  const util = dentro.map((p) => p[4]).filter((w) => !RE_NOME_POCO.test(w)).join(" ");
  const todos = util.match(/\d+(?:[.,]\d+)?/g) || [];
  const numeros = [...todos.filter((n) => /[.,]|\d{2,}/.test(n)), ...todos.filter((n) => !/[.,]|\d{2,}/.test(n))];
  const letras = util.replace(/[\d.,:;/()-]+/g, " ").replace(/\s+/g, " ").trim();
  const sugerir = (id, valor) => {
    if (!valor || $(id).value) return;
    $(id).value = valor;
    $(id).classList.add("sugestao");
  };
  sugerir("tr-topo", numeros[0]);
  if (numeros.length > 1) sugerir("tr-base", numeros[1]);
  if (letras.length >= 3) sugerir("tr-nome", letras);
}

function ligarTranscricao() {
  const sel = $("tr-tipo");
  for (const [k, v] of Object.entries(TIPOS_FATO)) sel.appendChild(new Option(v, k));
  for (const inp of document.querySelectorAll("#tr-form input")) inp.addEventListener("input", () => inp.classList.remove("sugestao"));

  const quadro = $("pg-quadro");
  quadro.onmousedown = (ev) => {
    if (!$("tr-box").open || ev.button !== 0) return;
    ev.preventDefault();
    tr.arraste = pontoNormalizado(ev);
  };
  quadro.onmousemove = (ev) => {
    if (!tr.arraste) return;
    const [a, b] = tr.arraste, [c, d] = pontoNormalizado(ev);
    tr.caixa = [Math.min(a, c), Math.min(b, d), Math.max(a, c), Math.max(b, d)];
    const atual = $("tr-caixa");
    if (atual) posicionar(atual, tr.caixa); else $("pg-caixas").appendChild(caixaAtual());
  };
  const terminar = () => {
    if (!tr.arraste) return;
    tr.arraste = null;
    if (!tr.caixa || (tr.caixa[2] - tr.caixa[0]) * (tr.caixa[3] - tr.caixa[1]) < 0.00005) { limparCaixa(); return; }
    tr.caixa = tr.caixa.map((x) => Math.round(x * 10000) / 10000);
    sugerirDoOCR(tr.caixa);
  };
  quadro.onmouseup = terminar;
  quadro.onmouseleave = terminar;
  $("tr-box").addEventListener("toggle", () => quadro.classList.toggle("marcando", $("tr-box").open));

  $("tr-limpar").onclick = () => {
    for (const id of ["tr-nome", "tr-topo", "tr-base", "tr-valor", "tr-unidade", "tr-obs"]) {
      $(id).value = "";
      $(id).classList.remove("sugestao");
    }
    limparCaixa();
  };
  $("tr-form").onsubmit = async (ev) => {
    ev.preventDefault();
    if (!tr.rel) return;
    const num = (id) => $(id).value.trim().replace(/\.(?=\d{3}(\D|$))/g, "");
    const dados = { tipo: $("tr-tipo").value, poco: $("tr-poco").value, nome: $("tr-nome").value,
                    prof_topo: num("tr-topo"), prof_base: num("tr-base"), valor: $("tr-valor").value,
                    unidade: $("tr-unidade").value, observacao: $("tr-obs").value, caixa: tr.caixa };
    const r = await chamar(null, "salvar_fato_pagina", tr.rel, tr.pagina, dados);
    if (!r.ok) return;
    tr.fatos = r.fatos;
    $("tr-limpar").click();
    desenharFatosPagina();
    status(`${TIPOS_FATO[r.fato.tipo]} salvo no poço ${r.fato.poco_id} (pág. ${r.fato.pagina}).`, "ok");
  };
}
