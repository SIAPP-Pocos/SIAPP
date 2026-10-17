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
  trocarModo3d(bl.modo);
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
  for (const b of document.querySelectorAll("[data-vista3d]")) {
    b.onclick = () => window.BlocoVisor && window.BlocoVisor.vista(b.dataset.vista3d);
  }
  trocarModoBloco();
}
