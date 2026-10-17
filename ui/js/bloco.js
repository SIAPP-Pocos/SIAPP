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
    const sb = $("bl-bacia"), atualB = sb.value;
    limpar(sb);
    for (const b of r.bacias) {
      const o = document.createElement("option");
      o.value = o.textContent = b;
      sb.appendChild(o);
    }
    if (atualB) sb.value = atualB;
    $("bl-disponiveis").textContent = r.total
      ? `${numero(r.total, 0)} poço(s) com topos de formação no AGP e coordenadas no cadastro.`
      : "Nenhum poço com topos ainda: leia os AGPs no Levantamento do acervo (aba Mapa).";
  }
  desenharListaBloco();
  carregarHistoricoBloco();
}

function trocarModoBloco() {
  const m = $("bl-modo").value;
  $("bl-campo-box").hidden = m !== "campo";
  $("bl-raio-box").hidden = m !== "raio";
  $("bl-bacia-box").hidden = m !== "todos";
}

async function selecionarPocosBloco() {
  const modo = $("bl-modo").value;
  if (modo === "secao") {
    bl.pocos = (sec.pocos || []).slice();
    bl.isolado = false;
    desenharListaBloco();
    status(bl.pocos.length ? `${bl.pocos.length} poço(s) da aba Seção.` : "A lista da aba Seção está vazia.",
           bl.pocos.length ? "ok" : "erro");
    return;
  }
  const r = await chamar($("bl-selecionar"), "bloco_selecionar", modo, $("bl-campo").value, $("bl-centro").value.trim(),
                         $("bl-raio").value.replace(",", "."), $("bl-bacia").value);
  if (!r.ok) return;
  bl.pocos = r.pocos;
  bl.isolado = r.isolado;
  // campo isolado: margem 0 (a margem infla a área de um campo delimitado)
  if (r.isolado) $("bl-margem").value = "0";
  desenharListaBloco();
  status(`${r.pocos.length} poço(s) com topos no AGP.`, r.pocos.length >= 3 ? "ok" : "erro");
}

function adicionarPocoBloco(id) {
  id = (id || "").trim().toUpperCase();
  if (!id) return;
  if (bl.pocos.includes(id)) { status(`${id} já está no bloco.`); return; }
  bl.pocos.push(id);
  desenharListaBloco();
}

function desenharListaBloco() {
  $("bl-n").textContent = bl.pocos.length;
  const p = limpar($("bl-lista"));
  const mostrar = bl.pocos.slice(0, 60);
  p.textContent = mostrar.join(", ") + (bl.pocos.length > 60 ? ` … e mais ${bl.pocos.length - 60}` : "");
}

function opcoesBloco() {
  return { nivel: $("bl-nivel").value, margem: $("bl-margem").value, dist_max: $("bl-distmax").value,
           celulas: $("bl-celulas").value, titulo: $("bl-titulo").value, base: $("bl-base").value };
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
  $("bl-trilha").value = temPay ? "avaliacao" : temInd ? "indicios" : "nenhuma";
  window.BlocoVisor.mostrar($("bl-visor"), m, { exagero: ex, opacidade: Number($("bl-opacidade").value),
                                               nomes: $("bl-nomes").checked, caixa: $("bl-caixa").checked,
                                               trilha: $("bl-trilha").value, drape: drapeEscolhido(),
                                               modo: bl.modo, corte: opcoesCorte() });
  window.BlocoVisor.validacao(m.validacao || null);
  trocarModo3d(bl.modo);
}

// ------------------------------------------------ saídas: mapas, simulador, volumetria, 3D
function prepararSaidas(temSolido) {
  bl.saidasDe = null;
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
      `${numero(s.base, 0)} m · empilhadas por espessura a partir do topo de ` +
      `${(m.legenda.find((u) => u.chave === s.referencia) || {}).nome || s.referencia} · mais claro = extrapolado`;
    return;
  }
  const sups = m.superficies.filter((x) => x.z);
  $("bl-resumo").textContent = `${m.pocos.length} poço(s) · contorno dos poços ${numero(m.area_km2, 1)} km²` +
    (m.margem_km ? ` (+ margem de ${numero(m.margem_km, 1)} km)` : "") +
    ` · ${sups.length} superfície(s) interpolada(s) · grade de ${numero(m.grade.passo * 1000, 0)} m`;
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
    o.textContent = `${u.nome} (${props[u.chave].pocos.length} poço(s) avaliado(s))`;
    su.appendChild(o);
  }
  su.disabled = su.options.length === 1;
  su.title = su.disabled ? "Nenhuma unidade com avaliação de formação nos poços deste bloco (aba Perfis)." : "";
  const sp = limpar($("bl-drape-prop"));
  for (const [k, nome] of Object.entries(m.nomes_propriedades || {})) {
    const o = document.createElement("option");
    o.value = k; o.textContent = nome;
    sp.appendChild(o);
  }
  sp.disabled = su.disabled;
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
  ligar("bl-modo", "onchange", trocarModoBloco);
  ligar("bl-selecionar", "onclick", selecionarPocosBloco);
  ligar("bl-limpar", "onclick", () => { bl.pocos = []; desenharListaBloco(); });
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
  ligar("bl-trilha", "onchange", () => window.BlocoVisor && window.BlocoVisor.trilha($("bl-trilha").value));
  const drape = () => {
    const d = drapeEscolhido();
    if (window.BlocoVisor) window.BlocoVisor.drape(d && d.chave, d && d.prop);
  };
  ligar("bl-drape-unidade", "onchange", drape);
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
  ligar("bl-saidas", "ontoggle", () => { if ($("bl-saidas").open) carregarSaidas(); });
  ligar("bl-mapas", "onclick", exportarMapas);
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
