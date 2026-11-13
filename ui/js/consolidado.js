// SIAPP — Acervo › Dados consolidados: cada tipo de dado, de onde vem, onde fica e onde é usado.

const ORIGEM_LEITOR = { cdpe: "Formulários CDPE da ANP", pressoes: "Pressões (teste a cabo, TFR)", pvt: "PVT",
  pag: "PAG", checkshot: "Sísmica de poço", geoquimica: "Geoquímica", petrofisica: "Petrofísica de testemunho" };

let coPocoPendente = null;      // aberto pela ficha: mostra o poço em vez do projeto

async function carregarConsolidado() {
  const box = $("co-resultado");
  if (!box || !api) return;
  if (coPocoPendente) {
    const id = coPocoPendente;
    coPocoPendente = null;
    $("co-poco").value = id;
    const r = await chamar(null, "consolidado_poco", id);
    if (r.ok) desenharConsolidadoPoco(r);
    return;
  }
  const r = await chamar(null, "consolidado_projeto");
  if (!r.ok) return;
  desenharConsolidadoProjeto(r);
}

function listaUsos(usos) {
  const ul = el("ul", "co-usos");
  for (const u of usos) ul.appendChild(el("li", "", u));
  return ul;
}

function desenharConsolidadoProjeto(r) {
  const box = limpar($("co-resultado"));
  box.appendChild(el("h3", "", "No projeto"));
  const t = el("table", "tabela co-tabela");
  const cab = el("tr");
  for (const h of ["Dado", "De onde vem (poços · registros)", "Onde fica no banco", "Onde é usado"]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const tm of r.temas) {
    const tr = el("tr");
    const fontes = el("td");
    const onde = el("td", "co-onde");
    for (const f of tm.fontes) {
      const d = el("div", f.pocos ? "co-fonte" : "co-fonte co-vazia", `${f.rotulo}: ${numero(f.pocos, 0)} · ${numero(f.registros, 0)}`);
      fontes.appendChild(d);
      onde.appendChild(el("div", "", f.onde));
    }
    const usos = el("td");
    usos.appendChild(listaUsos(tm.usos));
    tr.append(el("th", "", tm.nome), fontes, onde, usos);
    t.appendChild(tr);
  }
  box.appendChild(t);
  if ((r.leituras || []).length) {
    box.appendChild(el("h3", "", "Documentos lidos pelos leitores do bloco 9"));
    box.appendChild(tabelaSimples(["Leitor", "Documento", "Lidos", "Sem leitura", "De outro poço"],
      r.leituras.map((x) => [ORIGEM_LEITOR[x.leitor] || x.leitor, x.documento || "—", x.n, x.erros || 0, x.de_outro_poco || 0])));
  }
  box.appendChild(el("p", "ajuda", "Em cinza, fonte sem dado neste projeto. Os leitores rodam ao baixar o arquivo e ao abrir o projeto."));
  const prec = el("div", "co-precedencia");
  prec.id = "co-precedencia";
  box.appendChild(prec);
  desenharPrecedencia(prec);
}

// Ordem das fontes de topo: vale onde você não escolheu na ficha do poço (seção e bloco 3D). Desde a 0.63 ela muda em
// Configurações › Fontes e prioridade (junto com a das zonas); aqui fica o resumo.
async function desenharPrecedencia(caixa) {
  if (!fontesProjeto) await lerFontesProjeto();
  if (!fontesProjeto) return;
  limpar(caixa);
  caixa.appendChild(el("h3", "", "Topos: qual fonte vale quando você não escolhe"));
  const p = el("p", "", resumoFontes("topos") + " ");
  p.appendChild(botaoMudarFontes());
  caixa.append(p, el("p", "ajuda", fontesProjeto.topos.explicacao));
}

function desenharConsolidadoPoco(r) {
  const box = limpar($("co-resultado"));
  const h = el("h3", "", `Poço ${r.poco}`);
  const bf = el("button", "btn secundario pequeno", "Abrir a ficha");
  bf.onclick = () => { $("aba-mapa").click(); abrirFicha(r.poco); };
  h.appendChild(bf);
  box.appendChild(h);
  const com = r.temas.filter((tm) => tm.com_dado);
  if (!com.length) { box.appendChild(el("p", "ajuda", "Nenhum dado deste poço no projeto ainda.")); return; }
  for (const tm of r.temas) {
    const d = el("details", "co-tema");
    d.open = tm.com_dado > 0 && tm.chave !== "perfis";
    const n = tm.fontes.reduce((s, f) => s + f.n, 0);
    d.appendChild(el("summary", tm.com_dado ? "" : "co-vazia", `${tm.nome} — ${tm.com_dado} de ${tm.fontes.length} fonte(s)` + (n ? ` · ${n} registro(s)` : "")));
    const linhas = [];
    for (const f of tm.fontes) {
      if (!f.n) { linhas.push([f.rotulo, "—", "", "", "sem dado"]); continue; }
      for (const x of f.linhas) {
        const prof = x.topo == null && x.base == null ? "" : intervaloM(x.topo, x.base);
        linhas.push([f.rotulo, prof, x.nome, x.valor, x.detalhe]);
      }
    }
    d.appendChild(tabelaSimples(["Fonte", "Prof. (m)", "Nome", "Valor", "Detalhe"], linhas, "co-tabela-poco"));
    const onde = el("p", "ajuda", "Onde fica: " + tm.fontes.map((f) => `${f.rotulo} → ${f.onde}`).join(" · "));
    d.append(onde, listaUsos(tm.usos));
    box.appendChild(d);
  }
}

function ligarConsolidado() {
  ligar("co-ver", "onclick", async () => {
    const r = await chamar($("co-ver"), "consolidado_poco", $("co-poco").value);
    if (r.ok) desenharConsolidadoPoco(r);
  });
  ligar("co-poco", "onkeydown", (ev) => { if (ev.key === "Enter") $("co-ver").click(); });
  ligar("co-projeto", "onclick", carregarConsolidado);
}

// a partir da ficha do poço
function verConsolidadoDoPoco(id) {
  coPocoPendente = id;
  ui.subDados = "consolidado";
  $("aba-dados").click();                        // mostra o painel de ui.subDados e chama carregarConsolidado
}
