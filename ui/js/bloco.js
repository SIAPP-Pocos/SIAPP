// SIAPP — aba Bloco 3D: escolha dos poços, montagem (motor/bloco.py) e controles.
// O desenho 3D é do js/bloco3d.js (three.js), que se registra em window.BlocoVisor.
"use strict";

// opacidade guardada por modo: o bloco fechado fica opaco de saída (translúcido, as camadas se embaralham)
const bl = { pocos: [], ultimo: null, modelo: null, isolado: false, modo: "superficies",
             opacidade: { superficies: 0.85, fechado: 1 } };

async function carregarBloco() {
  if (!projetoAberto) return;
  const r = await chamar(null, "bloco_opcoes");
  if (r.ok) {
    const dl = limpar($("bl-lista-pocos"));
    for (const p of r.pocos) {
      const o = document.createElement("option");
      o.value = p.id;
      o.label = [p.campo, `${p.n_unidades} unidade(s)`].filter(Boolean).join(" · ");
      dl.appendChild(o);
    }
    const sc = $("bl-campo"), atualC = sc.value;
    limpar(sc);
    for (const c of r.campos) {
      const o = document.createElement("option");
      o.value = c.campo;
      o.textContent = `${c.campo} (${c.pocos} poço${c.pocos > 1 ? "s" : ""})`;
      sc.appendChild(o);
    }
    if (atualC) sc.value = atualC;
    // bacias: caixas de marcação (uma ou mais); mantém o que já estava marcado
    const caixaB = $("bl-bacias"), marcadas = new Set(bacias_marcadas_bloco());
    limpar(caixaB);
    for (const b of r.bacias) {
      const rot = el("label", "opcao");
      const cx = el("input");
      cx.type = "checkbox";
      cx.value = b;
      cx.checked = marcadas.has(b);
      rot.append(cx, el("span", "", ` ${b} (${numero((r.bacias_pocos || {})[b] || 0, 0)} poços)`));
      caixaB.appendChild(rot);
    }
    if (r.interpolacao) prepararInterpolacao(r.interpolacao);
    pedirGuia();
    $("bl-disponiveis").textContent = r.total
      ? `${numero(r.total, 0)} poço(s) com topos de formação no AGP e coordenadas no cadastro.`
      : "Nenhum poço com topos ainda: leia os AGPs no Levantamento do acervo (Acervo).";
  }
  desenharListaBloco();
  carregarHistoricoBloco();
}

// as bacias marcadas na lista (0.56: pode ser mais de uma)
function bacias_marcadas_bloco() {
  const caixa = $("bl-bacias");
  return caixa ? [...caixa.querySelectorAll("input:checked")].map((c) => c.value) : [];
}

function trocarModoBloco() {
  const m = $("bl-modo").value;
  $("bl-campo-box").hidden = m !== "campo";
  $("bl-raio-box").hidden = m !== "raio";
  $("bl-bacia-box").hidden = m !== "todos";
  $("bl-montar-campo").hidden = m !== "campo";
}

// um campo, um clique: escolher o campo já traz os poços; "Montar este campo" traz e monta
function campoEscolhidoBloco() {
  if ($("bl-modo").value !== "campo" || !$("bl-campo").value) return;
  if ($("pr-campo") && (!$("pr-campo").value || $("pr-campo").dataset.doBloco === "1")) {
    $("pr-campo").value = $("bl-campo").value;
    $("pr-campo").dataset.doBloco = "1";
    if (typeof mostrarResumoProducao === "function") mostrarResumoProducao();
  }
  return selecionarPocosBloco();
}

async function montarCampoBloco() {
  if ($("bl-modo").value !== "campo") { $("bl-modo").value = "campo"; trocarModoBloco(); }
  if (!$("bl-campo").value) { status("Escolha o campo.", "erro"); return; }
  if ($("bl-escala").value !== "reservatorio") { $("bl-escala").value = "reservatorio"; aplicarEscala("reservatorio"); }
  await selecionarPocosBloco();
  if (!$("bl-titulo").value.trim()) $("bl-titulo").value = `Campo de ${nomeCampo($("bl-campo").value)}`;
  await montarBloco();
}

// GUAMARÉ → Guamaré; CANTO DO AMARO → Canto do Amaro
function nomeCampo(c) {
  return (c || "").toLowerCase().replace(/(^|\s)(\p{L})/gu, (m, a, b) => a + b.toUpperCase())
    .replace(/ (Do|Da|De|Dos|Das|E) /g, (m) => m.toLowerCase());
}

async function selecionarPocosBloco() {
  const modo = $("bl-modo").value;
  if (modo === "secao") {
    bl.pocos = (sec.pocos || []).slice();
    bl.isolado = false;
    desenharListaBloco();
    pedirGuia();
    status(bl.pocos.length ? `${bl.pocos.length} poço(s) da aba Seção.` : "A lista da aba Seção está vazia.",
           bl.pocos.length ? "ok" : "erro");
    return;
  }
  const bacias = bacias_marcadas_bloco();
  if (modo === "todos" && !bacias.length) { status("Marque ao menos uma bacia.", "erro"); return; }
  const r = await chamar($("bl-selecionar"), "bloco_selecionar", modo, $("bl-campo").value, $("bl-centro").value.trim(),
                         $("bl-raio").value.replace(",", "."), "", bacias);
  if (!r.ok) return;
  bl.pocos = r.pocos;
  bl.isolado = r.isolado;
  pedirGuia();
  // campo isolado: margem 0 (a margem infla a área de um campo delimitado)
  if (r.isolado) $("bl-margem").value = "0";
  desenharListaBloco();
  status(`${r.pocos.length} poço(s) com topos de formação.`, r.pocos.length >= 3 ? "ok" : "erro");
}

function adicionarPocoBloco(id) {
  id = (id || "").trim().toUpperCase();
  if (!id) return;
  if (bl.pocos.includes(id)) { status(`${id} já está no bloco.`); return; }
  bl.pocos.push(id);
  desenharListaBloco();
  pedirGuia();
}

function desenharListaBloco() {
  $("bl-n").textContent = bl.pocos.length;
  const p = limpar($("bl-lista"));
  const mostrar = bl.pocos.slice(0, 60);
  p.textContent = mostrar.join(", ") + (bl.pocos.length > 60 ? ` … e mais ${bl.pocos.length - 60}` : "");
}

function opcoesBloco() {
  return { nivel: $("bl-nivel").value, margem: $("bl-margem").value, dist_max: $("bl-distmax").value,
           celulas: $("bl-celulas").value, titulo: $("bl-titulo").value, base: $("bl-base").value,
           escala: $("bl-escala").value, interpolacao: lerInterpolacao(), ambiente: $("bl-ambiente").value,
           zonas: typeof lerZonasBloco === "function" ? lerZonasBloco() : undefined };
}

// ---------------------------------------------------------------- interpolação e escala
// Os textos (métodos, parâmetros, escalas) vêm do motor (motor/interpolacao.py), pela ponte.
const CAMPOS_INTERP = ["estrutura", "espessura", "propriedades"];
const PARAMS_INTERP = ["potencia", "vizinhos", "modelo", "alcance_km", "azimute", "razao", "grau", "funcao", "raio_km"];
const blI = { info: null, aplicado: false, campoAjuda: "estrutura" };

function prepararInterpolacao(info) {
  blI.info = info;
  for (const campo of CAMPOS_INTERP) {
    const sel = $(`bl-m-${campo}`), atual = sel.value;
    limpar(sel);
    for (const m of info.metodos) {
      const o = document.createElement("option");
      o.value = m.id; o.textContent = m.nome;
      sel.appendChild(o);
    }
    sel.value = atual || "linear";
  }
  for (const lab of document.querySelectorAll("#bl-interp [data-param]")) {
    lab.title = info.parametros[lab.dataset.param] || "";
  }
  $("bl-empilhamento").title = info.parametros.empilhamento || "";
  const sa = $("bl-ambiente"), atualA = sa.value || lerAmbienteSalvo();
  limpar(sa);
  for (const a of info.ambientes || []) sa.appendChild(new Option(a.nome, a.id));
  sa.value = (info.ambientes || []).some((a) => a.id === atualA) ? atualA : "nao_sei";
  $("bl-suavidade").title = info.parametros.suavidade || "";
  if (!blI.aplicado) {                    // a escala só preenche o formulário uma vez (depois, é do usuário)
    blI.aplicado = true;
    aplicarEscala($("bl-escala").value);
  }
  atualizarInterpolacao();
}

function aplicarEscala(id) {
  const e = blI.info && blI.info.escalas[id];
  $("bl-escala-ajuda").textContent = e ? e.resumo
    : "Cada opção à sua escolha. A escala só preenche o formulário: tudo continua editável.";
  if (!e) return;
  if ($("bl-modo").value !== "secao") { $("bl-modo").value = e.selecao; trocarModoBloco(); }
  $("bl-margem").value = String(e.margem_km ?? 0).replace(".", ",");
  $("bl-celulas").value = e.celulas;
  $("bl-distmax").value = e.dist_max_km ? String(e.dist_max_km).replace(".", ",") : "";
  aplicarInterpolacao(e.interpolacao, true);
}

const metodoDe = (v) => (typeof v === "string" ? v : (v && v.metodo) || "linear");
const decimal = (v) => (v == null ? "" : String(v).replace(".", ","));

// cfg: {estrutura, espessura, propriedades, empilhamento} (texto ou {metodo, parâmetros}); campos ausentes ficam
function aplicarInterpolacao(cfg, padraoNoResto = false) {
  if (!cfg) return;
  for (const campo of CAMPOS_INTERP) if (cfg[campo]) $(`bl-m-${campo}`).value = metodoDe(cfg[campo]);
  if (cfg.empilhamento) $("bl-empilhamento").value = cfg.empilhamento;
  const base = (blI.info && blI.info.padrao) || {};
  const est = typeof cfg.estrutura === "object" && cfg.estrutura ? cfg.estrutura : {};
  const p = padraoNoResto ? { ...base, ...est } : est;
  if ("suavidade" in p || padraoNoResto) {
    const auto = p.suavidade == null;
    $("bl-suavidade-auto").checked = auto;
    if (!auto) $("bl-suavidade").value = p.suavidade;
  }
  for (const k of PARAMS_INTERP) {
    if (!(k in p)) continue;
    const campo = $(`bl-p-${k}`);
    campo.value = campo.tagName === "SELECT" ? String(p[k] ?? "") : decimal(p[k]);
  }
  atualizarInterpolacao();
}

function lerInterpolacao() {
  const cfg = { empilhamento: $("bl-empilhamento").value, parametros: {} };
  for (const campo of CAMPOS_INTERP) cfg[campo] = { metodo: $(`bl-m-${campo}`).value };
  cfg.parametros.suavidade = $("bl-suavidade-auto").checked ? null : Number($("bl-suavidade").value);
  for (const k of PARAMS_INTERP) {
    const v = $(`bl-p-${k}`).value.trim();
    if (v !== "") cfg.parametros[k] = v.replace(",", ".");
  }
  return cfg;
}

// mostra só os parâmetros dos métodos escolhidos e explica o método do campo em foco
function atualizarInterpolacao() {
  const usados = new Set(CAMPOS_INTERP.map((c) => $(`bl-m-${c}`).value));
  const tem = (...ms) => ms.some((m) => usados.has(m));
  const vis = { potencia: tem("idw"), vizinhos: tem("idw"), modelo: tem("krigagem", "tendencia"),
                alcance_km: tem("krigagem", "tendencia"), azimute: tem("krigagem", "tendencia"),
                razao: tem("krigagem", "tendencia"), grau: tem("tendencia"), funcao: tem("rbf"), raio_km: tem("rbf") };
  for (const lab of document.querySelectorAll("#bl-interp [data-param]")) lab.hidden = !vis[lab.dataset.param];
  const liso = tem("spline", "rbf", "krigagem", "tendencia");
  $("bl-suavidade-auto").disabled = !liso;
  $("bl-suavidade").disabled = !liso || $("bl-suavidade-auto").checked;
  $("bl-suavidade-v").textContent = !liso ? "—" : $("bl-suavidade-auto").checked ? "auto"
    : numero(Number($("bl-suavidade").value), 2);
  const p = $("bl-metodo-ajuda");
  limpar(p);
  const info = blI.info && blI.info.metodos.find((m) => m.id === $(`bl-m-${blI.campoAjuda}`).value);
  if (info) {
    const rot = { estrutura: "Topos", espessura: "Espessuras", propriedades: "Propriedades" }[blI.campoAjuda];
    p.append(el("strong", "", `${rot} — ${info.nome}. `), document.createTextNode(info.resumo + " "),
             el("em", "", `Bom para: ${info.quando}.`));
  }
}

function interpolacaoMudou() {
  $("bl-escala").value = "";                // mexeu à mão: personalizada
  $("bl-escala-ajuda").textContent = "Cada opção à sua escolha. A escala só preenche o formulário: tudo continua editável.";
  atualizarInterpolacao();
}

// ---------------------------------------------------------------- qual método usar (guia)
// Ambiente do reservatório + os dados + a comparação dos métodos (se já feita): motor/guia_interpolacao.py
const NOTA_GUIA = { indicado: "indicado", possivel: "possível", evitar: "evitar" };
const FONTE_GUIA = { ambiente: "ambiente", dados: "dados", comparacao: "seus poços", geral: "geral" };
let guiaAtual = null, guiaPedido = 0, guiaTimer = null;

function lerAmbienteSalvo() {
  return (prefs && prefs.bloco && prefs.bloco.ambiente) || "";
}

function pedirGuia() {
  clearTimeout(guiaTimer);
  guiaTimer = setTimeout(atualizarGuia, 150);
}

async function atualizarGuia() {
  if (!projetoAberto || !$("bl-ambiente").options.length) return;
  const meu = ++guiaPedido;
  const montado = bl.ultimo && bl.modelo && (bl.modelo.parametros || {}).pocos &&
    bl.modelo.parametros.pocos.length === bl.pocos.length && bl.modelo.parametros.pocos.every((p) => bl.pocos.includes(p));
  const r = await chamar(null, "bloco_guia", $("bl-ambiente").value, montado ? [] : bl.pocos, montado ? bl.ultimo : "");
  if (meu !== guiaPedido || !r.ok) return;
  guiaAtual = r;
  desenharGuia(r);
}

function desenharGuia(r) {
  $("bl-ambiente-resumo").textContent = r.ambiente.resumo || "";
  const ol = limpar($("bl-guia-lista"));
  for (const m of r.metodos) {
    const li = el("li", "nota-" + m.nota);
    const cab = el("div", "g-cab");
    cab.append(el("span", "g-selo " + m.nota, NOTA_GUIA[m.nota]), el("strong", "", m.nome));
    li.appendChild(cab);
    const ul = el("ul", "g-motivos");
    for (const mo of m.motivos) {
      const it = el("li", mo.sinal > 0 ? "mais" : mo.sinal < 0 ? "menos" : "");
      it.append(el("span", "g-fonte", FONTE_GUIA[mo.fonte] || mo.fonte), document.createTextNode(mo.texto));
      ul.appendChild(it);
    }
    li.appendChild(ul);
    if (m.nota === "evitar") li.classList.add("recolhido");
    cab.onclick = () => li.classList.toggle("recolhido");
    ol.appendChild(li);
  }
  $("bl-guia-nota").textContent = r.ambiente.nota || "";
  $("bl-guia-nota").hidden = !r.ambiente.nota;
  const d = r.dados || {};
  const partes = [];
  if (d.n) partes.push(`${d.n} poço(s)`);
  if (d.espacamento_km != null) partes.push(`espaçamento típico ${numero(d.espacamento_km, 1)} km`);
  partes.push(r.com_comparacao ? "com a comparação dos métodos" : "sem comparação ainda (monte e use Comparar métodos)");
  $("bl-guia-fontes").textContent = "Pesa: " + partes.join(" · ") + ".";
  const ind = r.indicado;
  const curto = { linear: "linear", idw: "IDW", spline: "spline", rbf: "RBF", krigagem: "krigagem",
                  tendencia: "tendência + krigagem" };
  $("bl-guia-usar").textContent = `Usar o indicado: ${curto[ind.metodo] || ind.metodo}`;
}

function usarIndicado() {
  if (!guiaAtual) return;
  const ind = guiaAtual.indicado;
  const est = { metodo: ind.metodo, ...(ind.parametros || {}) };
  // tendência só nos topos: a espessura vai por krigagem (como na comparação dos métodos)
  const esp = ind.metodo === "tendencia" ? { metodo: "krigagem" } : { metodo: ind.metodo };
  const empilhamento = ["spline", "rbf", "krigagem", "tendencia"].includes(ind.metodo) ? "topos" : $("bl-empilhamento").value;
  aplicarInterpolacao({ estrutura: est, espessura: esp, empilhamento });
  for (const [k, v] of Object.entries(ind.parametros || {})) {
    const c = $(`bl-p-${k}`);
    if (c) c.value = c.tagName === "SELECT" ? String(v) : decimal(v);
  }
  blI.campoAjuda = "estrutura";
  interpolacaoMudou();
  status(`Métodos preenchidos com ${ind.nome}. Monte o bloco para ver.`, "ok");
}

function nomeMetodo(id) {
  const m = blI.info && blI.info.metodos.find((x) => x.id === id);
  return m ? m.nome.replace(/ \(.*\)$/, "").toLowerCase() : id;
}

function textoMetodos(p) {
  const c = p && p.interpolacao;
  if (!c) return "linear";
  const e = metodoDe(c.estrutura), s = metodoDe(c.espessura);
  return e === s ? nomeMetodo(e) : `topos por ${nomeMetodo(e)}, espessuras por ${nomeMetodo(s)}`;
}

async function montarBloco() {
  if (bl.pocos.length < 3) { status("Escolha ao menos três poços.", "erro"); return; }
  status("Montando o bloco…", "trab");
  const r = await chamar($("bl-montar"), "bloco_montar", bl.pocos, opcoesBloco());
  if (!r.ok) return;
  mostrarBloco(r);
  status(`Bloco com ${r.modelo.pocos.length} poço(s), contorno de ${numero(r.modelo.area_km2, 1)} km² — ` +
         `registrado em execucoes/${r.id}.json`, "ok");
  carregarHistoricoBloco();
}

function mostrarBloco(r) {
  bl.ultimo = r.id;
  bl.modelo = r.modelo;
  bl.autor = r.autor || "";
  $("bl-vazio").hidden = true;
  $("bl-painel").hidden = false;
  $("bl-exportado").textContent = "";
  const m = r.modelo;
  limpar($("bl-unidades"));          // bloco novo: todas as unidades ligadas
  resumoBloco(m);
  desenharUnidadesBloco(m);
  const temSolido = !!(m.solido && m.solido.ok);
  const ul = limpar($("bl-avisos"));
  for (const a of m.avisos || []) ul.appendChild(el("li", "", a));
  for (const a of (m.solido && m.solido.avisos) || []) ul.appendChild(el("li", "", `Bloco fechado: ${a}`));
  const bf = document.querySelector("[data-modo3d='fechado']");
  bf.disabled = !temSolido;
  bf.title = temSolido ? "O volume inteiro, do terreno à base, fatiado nas unidades"
    : "Sem bloco fechado para estes poços (veja os avisos).";
  if (!temSolido) bl.modo = "superficies";
  $("bl-corte").checked = false;
  $("bl-afastar").value = "0";
  $("bl-parede").checked = false;
  // validação (guardada no registro) e prognóstico
  bl.prog = null;
  $("bl-prog").hidden = true;
  ligarEscolha(false);
  for (const id of ["bl-prog-clique", "bl-prog-ir", "bl-prog-latlon"]) {
    if ($(id).dataset.titulo == null) $(id).dataset.titulo = $(id).title;
    $(id).disabled = !temSolido;
    $(id).title = temSolido ? $(id).dataset.titulo : "O prognóstico usa o bloco fechado, que este bloco não tem.";
  }
  mostrarValidacao(m.validacao || null);
  mostrarComparacao(m.comparacao || null);
  pedirGuia();
  prepararSaidas(temSolido);
  // exagero inicial: o relevo das superfícies ocupa ~1/4 da largura do bloco
  const g = m.grade, lado = Math.max(g.nx, g.ny) * g.passo;
  // pela faixa das superfícies (não pelo fundo dos poços, que pode ir muito abaixo)
  const comZ = m.superficies.filter((s) => s.z);
  const zmax = comZ.length ? Math.max(...comZ.map((s) => s.cota_max)) : m.cota_max;
  const zmin = comZ.length ? Math.min(...comZ.map((s) => s.cota_min)) : m.cota_min;
  const faixa = Math.max(50, zmax - zmin) / 1000;
  const ex = Math.min(60, Math.max(1, Math.round((lado * 0.25) / faixa)));
  // muitos poços: nomes desligados de saída (viram um borrão); o mouse mostra o nome
  $("bl-nomes").checked = m.pocos.length <= 40;
  $("bl-exagero").value = ex;
  $("bl-exagero-v").textContent = `${ex}×`;
  if (!window.BlocoVisor) {
    $("bl-visor").textContent = "O visor 3D não carregou (o computador precisa de WebGL).";
    return;
  }
  preencherDrapeBloco(m);
  // trilha padrão: pay se algum poço foi avaliado; senão, indícios do AGP se houver
  const temPay = m.pocos.some((p) => (p.classes || []).length);
  const temInd = m.pocos.some((p) => (p.indicios || []).length);
  // a escolha do usuário fica de um bloco para o outro (se o bloco novo tiver esse dado)
  const tem = { avaliacao: temPay, indicios: temInd, nenhuma: true };
  $("bl-trilha").value = bl.trilhaEscolhida && tem[bl.trilhaEscolhida] ? bl.trilhaEscolhida
    : temPay ? "avaliacao" : temInd ? "indicios" : "nenhuma";
  window.BlocoVisor.mostrar($("bl-visor"), m, { exagero: ex, opacidade: Number($("bl-opacidade").value),
                                               nomes: $("bl-nomes").checked, caixa: $("bl-caixa").checked,
                                               trilha: $("bl-trilha").value, drape: drapeEscolhido(),
                                               modo: bl.modo, corte: opcoesCorte(), aparencia: aparenciaAtual() });
  desenharCoresTrilha();
  window.BlocoVisor.validacao(m.validacao || null);
  trocarModo3d(bl.modo);
}

// ------------------------------------------------ aparência dos poços (vale na hora; guardada nas preferências)
// bl.aparencia: a última escolhida nesta janela (a resposta de uma gravação antiga não a desfaz)
function aparenciaAtual() {
  const salva = bl.aparencia || (prefs && prefs.bloco && prefs.bloco.aparencia) || {};
  return JSON.parse(JSON.stringify(salva));
}

function preencherAparencia() {
  const a = aparenciaAtual(), m = a.marcador || {}, t = a.trilha || {};
  $("bl-ap-forma").value = m.forma || "esfera";
  $("bl-ap-cor").value = m.cor || "#1c2227";
  $("bl-ap-tamanho").value = m.tamanho || 1;
  $("bl-ap-linha").value = (a.linha && a.linha.cor) || "#3a4148";
  $("bl-ap-espessura").value = t.espessura || 1;
  $("bl-ap-topos").checked = a.topos !== false;
  $("bl-ap-legenda").checked = a.legenda !== false;
  $("bl-ap-porcima").value = a.por_cima || "fechado";
}

function lerAparencia() {
  const atual = aparenciaAtual();
  const cores = { ...((atual.trilha || {}).cores || {}) };
  for (const inp of document.querySelectorAll("#bl-ap-cores input[type=color]")) cores[inp.dataset.chave] = inp.value;
  return { marcador: { forma: $("bl-ap-forma").value, cor: $("bl-ap-cor").value, tamanho: Number($("bl-ap-tamanho").value) },
           linha: { cor: $("bl-ap-linha").value },
           trilha: { espessura: Number($("bl-ap-espessura").value), cores },
           topos: $("bl-ap-topos").checked, legenda: $("bl-ap-legenda").checked, por_cima: $("bl-ap-porcima").value };
}

let _guardarAparencia = null;
function aparenciaMudou() {
  const ap = lerAparencia();
  bl.aparencia = ap;
  if (window.BlocoVisor) window.BlocoVisor.aparencia(ap);
  clearTimeout(_guardarAparencia);
  _guardarAparencia = setTimeout(() => guardarPreferencias({ bloco: { aparencia: ap } }), 400);
}

// uma cor para cada classe da trilha que aparece no bloco (pay, reservatório sem pay, indício de óleo…)
function desenharCoresTrilha() {
  const box = limpar($("bl-ap-cores"));
  const itens = window.BlocoVisor && window.BlocoVisor.itensTrilha ? window.BlocoVisor.itensTrilha() : [];
  for (const [cor, nome, chave] of itens) {
    const lab = el("label");
    const inp = document.createElement("input");
    inp.type = "color";
    inp.value = cor;
    inp.dataset.chave = chave;
    inp.oninput = aparenciaMudou;
    lab.append(inp, document.createTextNode(nome));
    box.appendChild(lab);
  }
}

function ligarAparencia() {
  preencherAparencia();
  for (const id of ["bl-ap-forma", "bl-ap-topos", "bl-ap-legenda", "bl-ap-porcima"]) ligar(id, "onchange", aparenciaMudou);
  for (const id of ["bl-ap-cor", "bl-ap-tamanho", "bl-ap-linha", "bl-ap-espessura"]) ligar(id, "oninput", aparenciaMudou);
  ligar("bl-ap-padrao", "onclick", () => {
    bl.aparencia = {};
    preencherAparencia();
    if (window.BlocoVisor) window.BlocoVisor.aparencia({});
    desenharCoresTrilha();
    clearTimeout(_guardarAparencia);
    guardarPreferencias({ bloco: { aparencia: {} } });
  });
}

// ------------------------------------------------ saídas: mapas, simulador, volumetria, 3D
function prepararSaidas(temSolido) {
  bl.saidasDe = null;
  bl.mapa2dDe = null;
  limpar($("bl-m2d-fig"));
  $("bl-m2d-info").textContent = "";
  if ($("bl-m2d").open) carregarMapa2d();
  for (const id of ["bl-ecl-box", "bl-vol-box", "bl-glb-box"]) {
    $(id).classList.toggle("desligado", !temSolido);
    for (const c of $(id).querySelectorAll("button, input")) c.disabled = !temSolido;
  }
  limpar($("bl-ecl-camadas"));
  limpar($("bl-vol-tabela"));
  $("bl-ecl-previa").textContent = temSolido ? "" : "Sem bloco fechado neste bloco (veja os avisos): só os mapas.";
  $("bl-vol-notas").textContent = "";
  if ($("bl-saidas").open) carregarSaidas();
}

async function carregarSaidas() {
  if (!bl.ultimo || bl.saidasDe === bl.ultimo || !(bl.modelo.solido && bl.modelo.solido.ok)) return;
  bl.saidasDe = bl.ultimo;
  await previaEcl(true);
  await calcularVolumetria();
}

function opcoesEcl(inicial) {
  const caixas = [...document.querySelectorAll("#bl-ecl-camadas input")];
  return { camadas: inicial || !caixas.length ? null : caixas.filter((c) => c.checked).map((c) => c.value),
           nz: $("bl-ecl-nz").value, dx: $("bl-ecl-dx").value, max_celulas: $("bl-ecl-max").value };
}

async function previaEcl(inicial = false) {
  const r = await chamar(null, "bloco_eclipse_previa", bl.ultimo, opcoesEcl(inicial));
  if (!r.ok) return;
  if (inicial || !$("bl-ecl-camadas").children.length) {
    const box = limpar($("bl-ecl-camadas"));
    for (const c of r.camadas) {
      const lab = el("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = c.chave;
      cb.checked = !!c.marcada;
      cb.onchange = () => previaEcl();
      lab.append(cb, document.createTextNode(c.nome));
      box.appendChild(lab);
    }
  }
  if (r.erro) { $("bl-ecl-previa").textContent = r.erro; return; }
  const nk = r.camadas.filter((c) => c.marcada).map((c) => `${c.nome} ${c.nk}`).join(", ");
  $("bl-ecl-previa").textContent = `Sairia: ${r.nx} × ${r.ny} × ${r.nz} = ${numero(r.celulas, 0)} células ` +
    `(teto ${numero(r.max_celulas, 0)}), células de ${numero(r.dx, 0)} m, EPSG:${r.epsg}. Camadas por formação: ${nk}.`;
}

async function exportarEcl() {
  status("Gerando o deck do simulador…", "trab");
  const r = await chamar($("bl-ecl"), "bloco_exportar_eclipse", bl.ultimo, opcoesEcl(false));
  if (!r.ok) return;
  $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.pasta}/${r.deck}`;
  $("bl-ecl-previa").textContent = `${r.deck}: ${r.nx} × ${r.ny} × ${r.nz} = ${numero(r.celulas, 0)} células ` +
    `(${numero(r.ativas, 0)} ativas), células de ${numero(r.dx, 0)} m, ${r.pocos} poço(s). ` + r.notas.join("; ") +
    ". Permeabilidade, PVT, curvas relativas e contatos: provisórios (veja o LEIA-ME).";
  status(`Deck exportado: ${r.pasta}/${r.deck}`, "ok");
}

// ------------------------------------------------ mapa 2D com curvas de nível (0.56)
async function carregarMapa2d() {
  if (!bl.ultimo || bl.mapa2dDe === bl.ultimo) return;
  const r = await chamar(null, "bloco_mapa2d_lista", bl.ultimo);
  if (!r.ok) return;
  bl.mapa2dDe = bl.ultimo;
  const sm = limpar($("bl-m2d-mapa"));
  for (const m of r.mapas) {
    const o = document.createElement("option");
    o.value = m.nome;
    o.textContent = m.titulo;
    sm.appendChild(o);
  }
  const sp = limpar($("bl-m2d-paleta"));
  for (const p of r.paletas) {
    const o = document.createElement("option");
    o.value = p.chave;
    o.textContent = p.nome;
    sp.appendChild(o);
  }
  // o primeiro topo (ou o terreno, se não houver) já aparece desenhado
  const primeiro = r.mapas.find((m) => m.nome.startsWith("topo_")) || r.mapas[0];
  if (primeiro) sm.value = primeiro.nome;
  desenharMapa2d();
}

function opcoesMapa2d() {
  return { intervalo: $("bl-m2d-int").value.replace(",", "."), rotulo_cada: $("bl-m2d-rot").value, paleta: $("bl-m2d-paleta").value,
           inverter: $("bl-m2d-inv").checked, profundidade: $("bl-m2d-prof").checked, desde_mesa: $("bl-m2d-mesa").checked, preencher: $("bl-m2d-preencher").checked,
           curvas: $("bl-m2d-curvas").checked, pocos: $("bl-m2d-pocos").checked, nomes_pocos: $("bl-m2d-nomes").checked,
           titulo: $("bl-m2d-titulo").value };
}

async function desenharMapa2d(formato) {
  const nome = $("bl-m2d-mapa").value;
  if (!bl.ultimo || !nome) return;
  const r = await chamar(formato ? $(`bl-m2d-${formato}`) : null, "bloco_mapa2d", bl.ultimo, nome, opcoesMapa2d(), formato || "");
  if (!r.ok) return;
  if (formato) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Mapa salvo: ${r.arquivo}`, "ok");
    return;
  }
  $("bl-m2d-fig").innerHTML = r.svg;
  $("bl-m2d-info").textContent = `${r.titulo}: de ${numero(r.min, 1)} a ${numero(r.max, 1)} m, ${r.n_curvas} curvas a cada ${numero(r.intervalo_m, 1)} m.`;
}

async function exportarMapas() {
  status("Gerando os mapas…", "trab");
  const r = await chamar($("bl-mapas"), "bloco_exportar_mapas", bl.ultimo, $("bl-mapas-passo").value);
  if (!r.ok) return;
  $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.pasta}/ (${r.mapas.length} mapas, ${r.nx} × ${r.ny} ` +
    `pixels de ${numero(r.passo_m, 0)} m, EPSG:${r.epsg})`;
  status(`Mapas exportados: ${r.pasta}`, "ok");
}

function informadosVol() {
  const inf = {};
  for (const i of document.querySelectorAll("#bl-vol-tabela input")) {
    if (!i.value.trim()) continue;
    (inf[i.dataset.chave] = inf[i.dataset.chave] || {})[i.dataset.par] = i.value.trim();
  }
  return inf;
}

const co2Vol = () => ({ eficiencia: $("bl-vol-e").value.trim(), densidade: $("bl-vol-rho").value.trim() });
const mi = (v, casas = 1) => (v == null ? "—" : numero(v / 1e6, casas));
const fr = (v) => (v == null ? "" : numero(v, 3));

async function calcularVolumetria() {
  const inf = informadosVol();
  const r = await chamar($("bl-vol-calc"), "bloco_volumetria", bl.ultimo, inf, co2Vol());
  if (!r.ok) return;
  mostrarVolumetria(r, inf);
}

function mostrarVolumetria(v, inf) {
  const t = limpar($("bl-vol-tabela"));
  const cab = document.createElement("thead");
  t.appendChild(cab);
  linhaTabela(cab, ["formação", "área (km²)", "esp. média (m)", "rocha (10⁶ m³)", "N/G", "φ", "Sw", "Bo",
                    "poroso (10⁶ m³)", "HC (10⁶ m³)", "óleo in place (10⁶ m³)", "CO₂ (Mt)"], true);
  const corpo = document.createElement("tbody");
  t.appendChild(corpo);
  const campo = (l, par, valor, fonte) => {
    const i = document.createElement("input");
    i.dataset.chave = l.chave;
    i.dataset.par = par;
    i.inputMode = "decimal";
    const dig = ((inf || {})[l.chave] || {})[par];
    i.value = dig || "";
    i.placeholder = fonte === "informado" || valor == null ? "" : fr(valor);
    i.title = fonte && fonte !== "informado" ? `da ${fonte}` : valor == null ? "sem avaliação: digite" : "";
    i.onkeydown = (ev) => { if (ev.key === "Enter") calcularVolumetria(); };
    return { nos: [i] };
  };
  for (const l of v.linhas) {
    linhaTabela(corpo, [chipUnidade(l.nome, l.cor), numero(l.area_km2, 1), l.espessura_media_m == null ? "—" : numero(l.espessura_media_m, 0),
                        mi(l.grv_m3, 0), campo(l, "ntg", l.ntg, l.fonte.ntg), campo(l, "phi", l.phi, l.fonte.phi),
                        campo(l, "sw", l.sw, l.fonte.sw), campo(l, "bo", l.bo, ""), mi(l.vp_m3), mi(l.hc_m3),
                        mi(l.voip_m3), l.co2_t == null ? "—" : numero(l.co2_t / 1e6, 2)]);
  }
  const pe = document.createElement("tfoot");
  t.appendChild(pe);
  const T = v.total;
  linhaTabela(pe, ["total", "", "", mi(T.grv_m3, 0), "", "", "", "", mi(T.vp_m3), mi(T.hc_m3), mi(T.voip_m3),
                   T.co2_t == null ? "—" : numero(T.co2_t / 1e6, 2)]);
  $("bl-vol-notas").textContent = "Placeholder cinza = média da avaliação de formação (passe o mouse para ver de quantos poços). " +
    v.notas.join(" ");
}

async function exportarVolumetria() {
  const r = await chamar($("bl-vol-csv"), "bloco_exportar_volumetria", bl.ultimo, informadosVol(), co2Vol());
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Volumetria exportada: ${r.arquivo}`, "ok");
  }
}

async function exportarGlb() {
  const va = window.BlocoVisor ? window.BlocoVisor.vistaAtual() : {};
  status("Gerando o modelo 3D…", "trab");
  const r = await chamar($("bl-glb"), "bloco_exportar_glb", bl.ultimo,
                         { exagero: va.exagero, camadas: va.camadas && va.camadas.length ? va.camadas : null,
                           pocos: $("bl-glb-pocos").checked });
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo} (${numero(r.triangulos, 0)} triângulos, ` +
      `${numero(r.bytes / 1e6, 1)} MB)`;
    status(`Modelo 3D exportado: ${r.arquivo}`, "ok");
  }
}

// ------------------------------------------------ validação cruzada
async function validarBloco() {
  if (!bl.ultimo) return;
  status(`Validando: tirando cada um dos ${bl.modelo.pocos.length} poços e refazendo o bloco sem ele…`, "trab");
  const r = await chamar($("bl-validar"), "bloco_validar", bl.ultimo);
  if (!r.ok) return;
  bl.modelo.validacao = r.validacao;
  mostrarValidacao(r.validacao);
  if (window.BlocoVisor) window.BlocoVisor.validacao(r.validacao);
  if (bl.prog) preverBloco({ x: bl.prog.x, y: bl.prog.y });     // ganha a incerteza
  const g = r.validacao.global.fechado.n ? r.validacao.global.fechado : r.validacao.global.superficie;
  status(`Validação: ${r.validacao.n_comparacoes} topos de ${r.validacao.n_pocos} poços; metade com erro até ` +
         `${numero(g.mediana, 0)} m.`, "ok");
}

async function compararMetodos() {
  if (!bl.ultimo) return;
  status("Comparando os métodos: a validação cruzada com cada um (no bloco regional, alguns minutos)…", "trab");
  const r = await chamar($("bl-comparar"), "bloco_comparar", bl.ultimo);
  if (!r.ok) return;
  bl.modelo.comparacao = r.comparacao;
  mostrarComparacao(r.comparacao);
  pedirGuia();
  const c = r.comparacao, b = c.candidatos.find((x) => x.id === c.melhor);
  status(`Métodos comparados: o que menos errou foi ${b.nome} (metade dos erros até ` +
         `${numero(b.global[c.criterio].mediana, 0)} m).`, "ok");
}

function mostrarComparacao(c) {
  $("bl-cmp").hidden = !c;
  if (!c) return;
  const crit = c.criterio || "fechado", nomeCrit = crit === "fechado" ? "no bloco fechado" : "nas superfícies";
  const cand = c.candidatos, b = cand.find((x) => x.id === c.melhor);
  const atual = bl.modelo && bl.modelo.parametros && bl.modelo.parametros.interpolacao;
  const igual = (x) => atual && ["estrutura", "espessura"].every((k) => metodoDe(atual[k]) === metodoDe(x.interpolacao[k])) &&
    (atual.empilhamento || "espessuras") === x.interpolacao.empilhamento;
  let txt = `Com cada método, ${c.n_comparacoes} topos previstos sem o próprio poço. Errou menos ${nomeCrit}: ` +
            `${b.nome} — metade dos erros até ${numero(b.global[crit].mediana, 1)} m, 68% até ` +
            `${numero(b.global[crit].p68, 1)} m.`;
  if (crit === "fechado" && c.melhor_superficie && c.melhor_superficie !== c.melhor) {
    const s = cand.find((x) => x.id === c.melhor_superficie);
    txt += ` Só nas superfícies, o melhor foi ${s.nome} (${numero(s.global.superficie.mediana, 1)} m).`;
  }
  txt += igual(b) ? " É o que este bloco já usa." : "";
  $("bl-cmp-resumo").textContent = txt;
  $("bl-cmp-usar").disabled = !!igual(b);
  const t = limpar($("bl-cmp-tabela"));
  const cab = document.createElement("thead");
  t.appendChild(cab);
  // "Krigagem, topo a topo" → método em cima, empilhamento embaixo (a tabela cabe na largura)
  const cabMetodo = (x) => {
    const [m, ...resto] = x.nome.split(", ");
    return { nos: [document.createTextNode(m), el("small", "", resto.join(", "))], cls: x.id === c.melhor ? "melhor" : "" };
  };
  linhaTabela(cab, ["unidade", "n", ...cand.map(cabMetodo)], true);
  const corpo = document.createElement("tbody");
  t.appendChild(corpo);
  const celula = (g) => (g && g.mediana != null ? `${m1(g.mediana)} / ${m1(g.p68)}` : "—");
  const melhorDe = (f) => {
    let id = null, v = Infinity;
    for (const x of cand) { const g = f(x); if (g && g.mediana != null && g.mediana < v) { v = g.mediana; id = x.id; } }
    return id;
  };
  const linha = (rotulo, n, f) => {
    const m = melhorDe(f);
    linhaTabela(corpo, [rotulo, n, ...cand.map((x) => ({ nos: [document.createTextNode(celula(f(x)))],
                                                          cls: x.id === m ? "melhor" : "" }))]);
  };
  linha({ nos: [el("strong", "", `todas (${nomeCrit.replace("no ", "").replace("nas ", "")})`)] },
        String(b.global[crit].n || ""), (x) => x.global[crit]);
  if (crit === "fechado") linha("todas (superfícies)", String(b.global.superficie.n || ""), (x) => x.global.superficie);
  for (const [k, u] of Object.entries(cand[0].unidades)) {
    if (!u.n) continue;
    linha(chipUnidade(u.nome, u.cor), String(u.n), (x) => x.unidades[k][crit]);
  }
}

function usarMelhorMetodo() {
  const c = bl.modelo && bl.modelo.comparacao;
  if (!c) return;
  const b = c.candidatos.find((x) => x.id === c.melhor);
  // as propriedades ficam como estão (a comparação é dos topos)
  aplicarInterpolacao({ estrutura: b.interpolacao.estrutura, espessura: b.interpolacao.espessura,
                        empilhamento: b.interpolacao.empilhamento });
  $("bl-escala").value = "";
  montarBloco();
}

async function exportarComparacao(botao) {
  if (!bl.ultimo) return;
  const r = await chamar(botao, "bloco_exportar_comparacao", bl.ultimo, botao.dataset.comparacao);
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Comparação exportada: ${r.arquivo}`, "ok");
  }
}

function linhaTabela(tabela, textos, cabecalho = false) {
  const tr = document.createElement("tr");
  for (const t of textos) {
    const c = document.createElement(cabecalho ? "th" : "td");
    if (t && typeof t === "object") { c.append(...t.nos); if (t.cls) c.className = t.cls; if (t.span) c.colSpan = t.span; }
    else c.textContent = t ?? "—";
    tr.appendChild(c);
  }
  tabela.appendChild(tr);
  return tr;
}

function chipUnidade(nome, cor) {
  const i = el("i", "bl-cor");
  i.style.background = cor;
  return { nos: [i, document.createTextNode(" " + nome)] };
}

const m1 = (v) => (v == null ? "—" : numero(v, 1));

function mostrarValidacao(val) {
  $("bl-val").hidden = !val;
  if (!val) return;
  const f = val.global.fechado, s = val.global.superficie;
  const piores = val.linhas.filter((l) => l.erro_fechado != null)
    .sort((a, b) => Math.abs(b.erro_fechado) - Math.abs(a.erro_fechado)).slice(0, 5)
    .map((l) => `${l.poco} (${l.unidade}, ${numero(l.erro_fechado, 0)} m)`);
  let txt = `Tirando um poço de cada vez, ${val.n_comparacoes} topos de ${val.n_pocos} poços foram previstos sem o próprio poço.`;
  if (f.n) txt += ` Bloco fechado: metade dos erros até ${numero(f.mediana, 0)} m, 68% até ${numero(f.p68, 0)} m` +
                  (f.n_extrapolado ? ` (${f.n_extrapolado} topos extrapolados, fora do contorno dos outros poços).` : ".");
  if (s.n) txt += ` Superfícies (só dentro do contorno, ${s.n} topos): ${numero(s.mediana, 0)} m e ${numero(s.p68, 0)} m.`;
  if (piores.length) txt += ` Maiores erros (confira o AGP desses poços; pode ser também uma mudança brusca real, como uma falha): ${piores.join("; ")}.`;
  $("bl-val-resumo").textContent = txt;
  const t = limpar($("bl-val-tabela"));
  const cab = document.createElement("thead");
  t.appendChild(cab);
  const g = linhaTabela(cab, ["", { nos: [document.createTextNode("bloco fechado (m)")], span: 6 },
                              { nos: [document.createTextNode("superfícies (m)")], span: 3 }, ""], true);
  g.className = "grupo";
  linhaTabela(cab, ["unidade", "n", "viés", "mediana", "68% ≤", "máx.", "poço do máx.", "n", "mediana", "68% ≤",
                    "espessura, erro médio"], true);
  const corpo = document.createElement("tbody");
  t.appendChild(corpo);
  for (const u of val.unidades) {
    const a = u.fechado, b = u.superficie;
    linhaTabela(corpo, [chipUnidade(u.nome, u.cor), String(u.n), a.n ? m1(a.vies) : "—", a.n ? m1(a.mediana) : "—",
                        a.n ? m1(a.p68) : "—", a.n ? numero(a.max, 0) : "—", { nos: [document.createTextNode(a.max_poco || "")], cls: "texto" },
                        String(b.n || 0), b.n ? m1(b.mediana) : "—", b.n ? m1(b.p68) : "—",
                        u.espessura.n ? m1(u.espessura.ema) : "—"]);
  }
  const fx = limpar($("bl-val-faixas"));
  const cab2 = document.createElement("thead");
  fx.appendChild(cab2);
  linhaTabela(cab2, ["distância ao poço mais próximo", "topos", "68% ≤ (fechado)", "68% ≤ (superfícies)"], true);
  const corpo2 = document.createElement("tbody");
  fx.appendChild(corpo2);
  for (const q of val.faixas) {
    if (!q.n) continue;
    const rot = q.ate == null ? `mais de ${numero(q.de, 0)} km` : `${numero(q.de, 0)} a ${numero(q.ate, 0)} km`;
    linhaTabela(corpo2, [rot, String(q.n), m1(q.p68_fechado), q.n_superficie ? m1(q.p68_superficie) : "—"]);
  }
  const ul = limpar($("bl-val-avisos"));
  for (const a of val.avisos || []) ul.appendChild(el("li", "", a));
}

async function exportarValidacao(botao) {
  if (!bl.ultimo) return;
  const r = await chamar(botao, "bloco_exportar_validacao", bl.ultimo, botao.dataset.validacao);
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Validação exportada: ${r.arquivo}`, "ok");
  }
}

// ------------------------------------------------ prognóstico num ponto
function ligarEscolha(sim) {
  const b = $("bl-prog-clique");
  b.setAttribute("aria-pressed", String(sim));
  if (!window.BlocoVisor) return;
  window.BlocoVisor.escolherPonto(sim ? (pt) => { ligarEscolha(false); preverBloco(pt); } : null);
}

async function preverBloco(ponto) {
  if (!bl.ultimo) return;
  const r = await chamar($("bl-prog-ir"), "bloco_prognostico", bl.ultimo, ponto);
  if (!r.ok) return;
  bl.prog = r;
  mostrarPrognostico(r);
  if (window.BlocoVisor) window.BlocoVisor.pino(r);
}

function mostrarPrognostico(p) {
  $("bl-prog").hidden = false;
  $("bl-prog-titulo").textContent = `Prognóstico em ${numero(p.lat, 5)}°, ${numero(p.lon, 5)}° · terreno ${numero(p.terreno, 0)} m`;
  const t = limpar($("bl-prog-tabela"));
  const cab = document.createElement("thead");
  t.appendChild(cab);
  linhaTabela(cab, ["camada", "topo (cota, m)", "prof. abaixo do terreno (m)", "± (m)", "espessura (m)",
                    "base (cota, m)", "", "poço mais próximo com a unidade a"], true);
  const corpo = document.createElement("tbody");
  t.appendChild(corpo);
  for (const c of p.camadas) {
    const tr = linhaTabela(corpo, [chipUnidade(c.nome, c.cor), numero(c.topo, 0), numero(c.prof_topo, 0),
                                   c.presente && c.incerteza_m != null ? numero(c.incerteza_m, 0) : "—",
                                   c.presente ? numero(c.espessura, 0) : "ausente", numero(c.base, 0),
                                   { nos: [document.createTextNode(c.presente ? (c.interpolado ? "interpolado" : "extrapolado") : "")], cls: "texto" },
                                   c.dist_km != null ? `${numero(c.dist_km, 1)} km` : "—"]);
    if (!c.presente) tr.className = "ausente";
  }
  const notas = [`Poços mais próximos: ${p.proximos.map((q) => `${q.poco} (${numero(q.dist_km, 1)} km)`).join(", ")}.`,
                 "Profundidade a partir do terreno (a mesa rotativa fica alguns metros acima).",
                 "± = erro que 68% das previsões da validação cruzada não passaram, para a unidade e a distância.",
                 ...p.avisos];
  $("bl-prog-notas").textContent = notas.join(" ");
}

async function exportarPrognostico() {
  if (!bl.ultimo || !bl.prog) return;
  const r = await chamar($("bl-prog-csv"), "bloco_exportar_prognostico", bl.ultimo, { x: bl.prog.x, y: bl.prog.y });
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Prognóstico exportado: ${r.arquivo}`, "ok");
  }
}

function opcoesCorte() {
  for (const id of ["bl-corte-quad", "bl-corte-x", "bl-corte-y"]) $(id).disabled = !$("bl-corte").checked;
  return { ativo: $("bl-corte").checked, quadrante: $("bl-corte-quad").value,
           fx: Number($("bl-corte-x").value), fy: Number($("bl-corte-y").value) };
}

// Superfícies ⇄ bloco fechado: os dois vêm da mesma montagem
function trocarModo3d(modo) {
  const m = bl.modelo;
  if (modo === "fechado" && !(m && m.solido && m.solido.ok)) modo = "superficies";
  if (modo !== bl.modo) {
    bl.opacidade[bl.modo] = Number($("bl-opacidade").value);
    $("bl-opacidade").value = String(bl.opacidade[modo]);
  }
  bl.modo = modo;
  for (const b of document.querySelectorAll("[data-modo3d]")) {
    const sim = b.dataset.modo3d === modo;
    b.classList.toggle("ativo", sim);
    b.setAttribute("aria-pressed", String(sim));
  }
  const fechado = modo === "fechado";
  $("bl-fechado-ctl").hidden = !fechado;
  // a propriedade no topo é do modo superfícies
  for (const id of ["bl-drape-unidade", "bl-drape-prop"]) $(id).closest("label").hidden = fechado;
  if (fechado && $("bl-drape-unidade").value) {
    $("bl-drape-unidade").value = "";
    if (window.BlocoVisor) window.BlocoVisor.drape(null);
  }
  if (!m) return;
  if (window.BlocoVisor) {
    window.BlocoVisor.opacidade(Number($("bl-opacidade").value));
    window.BlocoVisor.modo(modo);
  }
  resumoBloco(m);
  desenharUnidadesBloco(m);
}

function resumoBloco(m) {
  const s = m.solido;
  if (bl.modo === "fechado" && s && s.ok) {
    $("bl-resumo").textContent = `Bloco fechado: ${m.pocos.length} poço(s) · ${numero(s.area_km2, 1)} km²` +
      (m.margem_km ? ` (contorno + margem de ${numero(m.margem_km, 1)} km)` : " (contorno dos poços)") +
      ` · ${s.camadas.length} camada(s) · do terreno (até ${numero(s.cota_topo_max, 0)} m) à base plana em ` +
      `${numero(s.base, 0)} m · ` + (s.empilhamento === "topos" ? "topo a topo"
        : `empilhadas por espessura a partir do topo de ${(m.legenda.find((u) => u.chave === s.referencia) || {}).nome || s.referencia}`) +
      ` · ${textoMetodos(m.parametros)} · mais claro = extrapolado`;
    return;
  }
  const sups = m.superficies.filter((x) => x.z);
  $("bl-resumo").textContent = `${m.pocos.length} poço(s) · contorno dos poços ${numero(m.area_km2, 1)} km²` +
    (m.margem_km ? ` (+ margem de ${numero(m.margem_km, 1)} km)` : "") +
    ` · ${sups.length} superfície(s) interpolada(s) por ${nomeMetodo(metodoDe((m.parametros.interpolacao || {}).estrutura))}` +
    ` · grade de ${numero(m.grade.passo * 1000, 0)} m`;
}

function paredeBloco() {
  if (!window.BlocoVisor) return;
  if (!$("bl-parede").checked) { window.BlocoVisor.parede(null); return; }
  const n = window.BlocoVisor.parede(sec.pocos || []);
  if (n < 2) {
    $("bl-parede").checked = false;
    status((sec.pocos || []).length
      ? "Menos de dois poços da aba Seção estão neste bloco." : "A lista da aba Seção está vazia.", "erro");
  } else {
    status(`Seção A–A′ por ${n} poço(s) da aba Seção, prolongada até a borda do bloco.`, "ok");
  }
}

function preencherDrapeBloco(m) {
  const su = limpar($("bl-drape-unidade"));
  const o0 = document.createElement("option");
  o0.value = ""; o0.textContent = "— (cor da unidade)";
  su.appendChild(o0);
  const props = m.propriedades || {};
  for (const u of m.legenda) {
    if (!props[u.chave]) continue;
    const o = document.createElement("option");
    o.value = u.chave;
    const nAv = props[u.chave].pocos.length;
    o.textContent = nAv ? `${u.nome} (${nAv} poço(s) avaliado(s))` : `${u.nome} (incerteza da krigagem)`;
    su.appendChild(o);
  }
  su.disabled = su.options.length === 1;
  su.title = su.disabled ? "Nenhuma unidade com avaliação de formação nos poços deste bloco (aba Perfis)." : "";
  propsDrapeBloco();
}

// só as propriedades que a unidade escolhida tem (φ, N/G… da avaliação; σ da krigagem)
function propsDrapeBloco() {
  const m = bl.modelo;
  if (!m) return;
  const sp = $("bl-drape-prop"), atual = sp.value;
  limpar(sp);
  const info = (m.propriedades || {})[$("bl-drape-unidade").value];
  for (const [k, nome] of Object.entries(m.nomes_propriedades || {})) {
    if (info && !(info.faixas || {})[k]) continue;
    const o = document.createElement("option");
    o.value = k; o.textContent = nome;
    sp.appendChild(o);
  }
  if ([...sp.options].some((o) => o.value === atual)) sp.value = atual;
  sp.disabled = $("bl-drape-unidade").disabled;
}

function drapeEscolhido() {
  return $("bl-drape-unidade").value ? { chave: $("bl-drape-unidade").value, prop: $("bl-drape-prop").value } : null;
}

function desenharUnidadesBloco(m) {
  const box = limpar($("bl-unidades"));
  const desligadas = new Set([...document.querySelectorAll("#bl-unidades input:not(:checked)")].map((c) => c.dataset.chave));
  if (bl.modo === "fechado" && m.solido && m.solido.ok) {
    for (const c of m.solido.camadas) {
      const lab = el("label", "bl-unidade");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = !desligadas.has(c.chave);
      cb.dataset.chave = c.chave;
      cb.onchange = () => window.BlocoVisor && window.BlocoVisor.unidade(c.chave, cb.checked);
      const cor = el("i", "bl-cor");
      cor.style.background = c.cor;
      const extra = c.fracao_extrapolada > 0.005 ? ` · ${numero(c.fracao_extrapolada * 100, 0)}% extrapolada` : "";
      const info = el("small", "", `${numero(c.area_km2, 1)} km² · espessura máx. ${numero(c.espessura_max_m, 0)} m · ` +
        `${numero(c.volume_km3, c.volume_km3 < 1 ? 3 : 1)} km³` + (c.chave.startsWith("_") ? "" : ` · ${c.n_espessuras} poço(s)`) + extra);
      lab.append(cb, cor, el("span", "", c.nome), info);
      box.appendChild(lab);
    }
    return;
  }
  for (const u of m.legenda) {
    const s = m.superficies.find((x) => x.chave === u.chave);
    const lab = el("label", "bl-unidade");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !desligadas.has(u.chave);
    cb.dataset.chave = u.chave;
    cb.onchange = () => window.BlocoVisor && window.BlocoVisor.unidade(u.chave, cb.checked);
    const cor = el("i", "bl-cor");
    cor.style.background = u.cor;
    const txt = el("span", "", u.nome);
    const info = el("small", "", s && s.z
      ? `${u.n_pocos} poços · ${numero(s.area_km2, 1)} km² · cota ${numero(s.cota_max, 0)} a ${numero(s.cota_min, 0)} m`
      : `${u.n_pocos} poço(s) · só nos poços`);
    lab.append(cb, cor, txt, info);
    box.appendChild(lab);
  }
}

async function carregarHistoricoBloco() {
  const r = await chamar(null, "bloco_execucoes");
  if (!r.ok) return;
  const ul = limpar($("bl-historico"));
  if (!r.execucoes.length) { ul.appendChild(el("li", "ajuda", "Nenhum ainda.")); return; }
  for (const h of r.execucoes) {
    const li = el("li");
    const b = el("button", "link", `${(h.criado_em || "").slice(0, 16).replace("T", " ")} · ${h.n_pocos} poços · ` +
                                   `${numero(h.area_km2, 0)} km²`);
    b.type = "button";
    b.title = (h.parametros.pocos || []).join(", ");
    b.onclick = () => abrirBlocoAnterior(h.id);
    li.appendChild(b);
    ul.appendChild(li);
  }
}

async function abrirBlocoAnterior(ident) {
  const r = await chamar(null, "bloco_abrir", ident);
  if (!r.ok) return;
  const p = r.modelo.parametros || {};
  bl.pocos = (p.pocos || []).slice();
  if (p.nivel) $("bl-nivel").value = p.nivel;
  $("bl-margem").value = String(p.margem_km ?? 0).replace(".", ",");
  $("bl-distmax").value = p.dist_max_km ? String(p.dist_max_km).replace(".", ",") : "";
  if (p.celulas) $("bl-celulas").value = p.celulas;
  $("bl-base").value = p.base_cota != null ? String(p.base_cota).replace(".", ",") : "";
  // blocos de antes da 0.23: linear, por espessuras
  aplicarInterpolacao(p.interpolacao || { estrutura: "linear", espessura: "linear", propriedades: "linear",
                                          empilhamento: "espessuras" }, true);
  $("bl-escala").value = p.escala || "";
  if (r.modelo.ambiente && [...$("bl-ambiente").options].some((o) => o.value === r.modelo.ambiente)) {
    $("bl-ambiente").value = r.modelo.ambiente;
  }
  $("bl-escala-ajuda").textContent = (blI.info && blI.info.escalas[p.escala] || {}).resumo ||
    "Cada opção à sua escolha. A escala só preenche o formulário: tudo continua editável.";
  desenharListaBloco();
  mostrarBloco(r);
  status(`Bloco ${ident} reaberto (sem recalcular).`, "ok");
}

async function exportarPngBloco() {
  if (!bl.ultimo || !window.BlocoVisor) return;
  status("Gerando a imagem…", "trab");
  const url = window.BlocoVisor.imagem({ titulo: bl.modelo.titulo || "", autor: bl.autor, versao: $("versao").textContent });
  const r = await chamar($("bl-png"), "bloco_salvar_png", bl.ultimo, url);
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Bloco exportado: ${r.arquivo}`, "ok");
  }
}

async function exportarFiguraBloco(botao) {
  if (!bl.ultimo || !window.BlocoVisor) return;
  const r = await chamar(botao, "bloco_figura", bl.ultimo, { ...window.BlocoVisor.vistaAtual(),
                                                              titulo: bl.modelo.titulo || "" }, botao.dataset.figura);
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivo}`;
    status(`Figura do bloco: ${r.arquivo}`, "ok");
  }
}

async function exportarCsvBloco() {
  if (!bl.ultimo) return;
  const r = await chamar($("bl-csv"), "bloco_exportar_csv", bl.ultimo);
  if (r.ok) {
    $("bl-exportado").textContent = `Salvo em ambiente_teste/${r.arquivos.join(" e ")}`;
    status(`Bloco exportado: ${r.arquivos.join(" e ")}`, "ok");
  }
}

async function lerDirecionaisBloco() {
  if (!bl.pocos.length) { status("Escolha os poços primeiro.", "erro"); return; }
  status("Lendo os dados direcionais…", "trab");
  const r = await chamar($("bl-direcionais"), "bloco_ler_direcionais", bl.pocos);
  if (r.ok) status(`${r.lidos} arquivo(s) de dados direcionais lido(s); ${r.com_trajetoria} poço(s) com trajetória. ` +
                   "Monte o bloco de novo para usar.", "ok");
}

function ligarBloco() {
  ligar("bl-direcionais", "onclick", lerDirecionaisBloco);
  ligar("bl-modo", "onchange", () => { trocarModoBloco(); campoEscolhidoBloco(); });
  ligar("bl-campo", "onchange", campoEscolhidoBloco);
  ligar("bl-montar-campo", "onclick", montarCampoBloco);
  ligar("bl-selecionar", "onclick", selecionarPocosBloco);
  ligar("bl-limpar", "onclick", () => { bl.pocos = []; desenharListaBloco(); pedirGuia(); });
  ligar("bl-ambiente", "onchange", () => {
    guardarPreferencias({ bloco: { ambiente: $("bl-ambiente").value } });
    atualizarGuia();
  });
  ligarAparencia();
  ligar("bl-guia-usar", "onclick", usarIndicado);
  ligar("bl-form-poco", "onsubmit", (ev) => {
    ev.preventDefault();
    adicionarPocoBloco($("bl-poco").value);
    $("bl-poco").value = "";
  });
  ligar("bl-montar", "onclick", montarBloco);
  ligar("bl-png", "onclick", exportarPngBloco);
  ligar("bl-csv", "onclick", exportarCsvBloco);
  for (const b of document.querySelectorAll("[data-figura]")) b.onclick = () => exportarFiguraBloco(b);
  ligar("bl-pasta", "onclick", () => chamar(null, "abrir_pasta_blocos"));
  ligar("bl-exagero", "oninput", () => {
    $("bl-exagero-v").textContent = `${$("bl-exagero").value}×`;
    if (window.BlocoVisor) window.BlocoVisor.exagero(Number($("bl-exagero").value));
  });
  ligar("bl-opacidade", "oninput", () => window.BlocoVisor && window.BlocoVisor.opacidade(Number($("bl-opacidade").value)));
  ligar("bl-trilha", "onchange", () => {
    bl.trilhaEscolhida = $("bl-trilha").value;
    if (window.BlocoVisor) window.BlocoVisor.trilha($("bl-trilha").value);
    desenharCoresTrilha();
  });
  const drape = () => {
    const d = drapeEscolhido();
    if (window.BlocoVisor) window.BlocoVisor.drape(d && d.chave, d && d.prop);
  };
  ligar("bl-drape-unidade", "onchange", () => { propsDrapeBloco(); drape(); });
  ligar("bl-drape-prop", "onchange", drape);
  ligar("bl-nomes", "onchange", () => window.BlocoVisor && window.BlocoVisor.nomes($("bl-nomes").checked));
  ligar("bl-caixa", "onchange", () => window.BlocoVisor && window.BlocoVisor.caixa($("bl-caixa").checked));
  for (const b of document.querySelectorAll("[data-modo3d]")) b.onclick = () => trocarModo3d(b.dataset.modo3d);
  const corte = () => window.BlocoVisor && window.BlocoVisor.corte(opcoesCorte());
  for (const id of ["bl-corte", "bl-corte-quad"]) ligar(id, "onchange", corte);
  for (const id of ["bl-corte-x", "bl-corte-y"]) ligar(id, "oninput", corte);
  ligar("bl-afastar", "oninput", () => window.BlocoVisor && window.BlocoVisor.afastar(Number($("bl-afastar").value)));
  ligar("bl-parede", "onchange", paredeBloco);
  ligar("bl-validar", "onclick", validarBloco);
  ligar("bl-comparar", "onclick", compararMetodos);
  ligar("bl-cmp-usar", "onclick", usarMelhorMetodo);
  for (const b of document.querySelectorAll("[data-comparacao]")) b.onclick = () => exportarComparacao(b);
  ligar("bl-escala", "onchange", () => aplicarEscala($("bl-escala").value));
  for (const campo of CAMPOS_INTERP) {
    const sel = $(`bl-m-${campo}`);
    sel.addEventListener("change", () => { blI.campoAjuda = campo; interpolacaoMudou(); });
    sel.addEventListener("focus", () => { blI.campoAjuda = campo; atualizarInterpolacao(); });
  }
  ligar("bl-empilhamento", "onchange", interpolacaoMudou);
  ligar("bl-suavidade", "oninput", interpolacaoMudou);
  ligar("bl-suavidade-auto", "onchange", interpolacaoMudou);
  for (const k of PARAMS_INTERP) ligar(`bl-p-${k}`, "onchange", interpolacaoMudou);
  for (const lab of document.querySelectorAll("#bl-interp [data-param]")) {
    lab.addEventListener("mouseenter", () => { $("bl-param-ajuda").textContent = lab.title; });
  }
  for (const id of ["bl-margem", "bl-celulas", "bl-distmax"]) ligar(id, "onchange", interpolacaoMudou);
  ligar("bl-saidas", "ontoggle", () => { if ($("bl-saidas").open) carregarSaidas(); });
  ligar("bl-mapas", "onclick", exportarMapas);
  ligar("bl-m2d", "ontoggle", () => { if ($("bl-m2d").open) carregarMapa2d(); });
  ligar("bl-m2d-mapa", "onchange", () => desenharMapa2d());
  for (const id of ["bl-m2d-int", "bl-m2d-rot", "bl-m2d-paleta", "bl-m2d-prof", "bl-m2d-mesa", "bl-m2d-inv", "bl-m2d-preencher",
                    "bl-m2d-curvas", "bl-m2d-pocos", "bl-m2d-nomes", "bl-m2d-titulo"]) ligar(id, "onchange", () => desenharMapa2d());
  for (const f of ["svg", "png", "pdf"]) ligar(`bl-m2d-${f}`, "onclick", () => desenharMapa2d(f));
  ligar("bl-ecl", "onclick", exportarEcl);
  for (const id of ["bl-ecl-nz", "bl-ecl-dx", "bl-ecl-max"]) ligar(id, "onchange", () => previaEcl());
  ligar("bl-vol-calc", "onclick", calcularVolumetria);
  ligar("bl-vol-csv", "onclick", exportarVolumetria);
  ligar("bl-glb", "onclick", exportarGlb);
  for (const b of document.querySelectorAll("[data-validacao]")) b.onclick = () => exportarValidacao(b);
  ligar("bl-prog-clique", "onclick", () => {
    const sim = $("bl-prog-clique").getAttribute("aria-pressed") !== "true";
    ligarEscolha(sim);
    if (sim) status("Clique num ponto do bloco (sem arrastar).");
  });
  ligar("bl-prog-ir", "onclick", () => {
    if ($("bl-prog-latlon").value.trim()) preverBloco({ latlon: $("bl-prog-latlon").value });
    else status("Escreva lat, lon ou use \"Clicar no bloco\".", "erro");
  });
  ligar("bl-prog-csv", "onclick", exportarPrognostico);
  ligar("bl-prog-latlon", "onkeydown", (ev) => { if (ev.key === "Enter") $("bl-prog-ir").click(); });
  ligar("bl-prog-limpar", "onclick", () => {
    bl.prog = null;
    $("bl-prog").hidden = true;
    if (window.BlocoVisor) window.BlocoVisor.pino(null);
  });
  for (const b of document.querySelectorAll("[data-vista3d]")) {
    b.onclick = () => window.BlocoVisor && window.BlocoVisor.vista(b.dataset.vista3d);
  }
  trocarModoBloco();
}
