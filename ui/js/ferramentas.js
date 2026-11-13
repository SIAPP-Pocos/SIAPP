// SIAPP — esquemas de ferramentas na ficha do poço: o que é cada arquivo de perfil.
// A leitura (nome do arquivo + texto/OCR do PDF) é do motor (motor/ferramentas.py).
"use strict";

const NOMES_FAMILIA_FERR = {
  gr: "raios gama", gr_espectral: "GR espectral", neutron: "nêutron", densidade: "densidade",
  micro: "microrresistividade", inducao: "indução", laterolog: "laterolog", sonico: "sônico",
  imagem: "imagem", mergulho: "mergulho", rmn: "RMN", testador: "testador", amostrador: "amostrador lateral",
  cimentacao: "cimentação", ccl: "CCL", inclinometria: "inclinometria", caliper: "cáliper",
  espectroscopia: "espectroscopia", lwd: "LWD", sismica: "sísmica de poço",
};

function seloCorrida(info) {
  if (!info || !info.rotulo) return null;
  const s = el("span", "selo corrida t-" + (info.tipo || "nd"), info.rotulo);
  const partes = [`Pelo ${info.fonte}`];
  if (info.esquemas && info.esquemas.length) partes.push("esquema: " + info.esquemas.join(", "));
  if (info.ferramentas && info.ferramentas.length) partes.push("ferramentas: " + info.ferramentas.join(" "));
  s.title = partes.join("\n");
  return s;
}

function secaoEsquemasFicha(corpo, esq, poco) {
  if (!esq || !esq.esquemas || !esq.esquemas.length) return;
  const lidos = esq.esquemas.filter((e) => e.lido).length;
  corpo.appendChild(el("h3", "", `Esquemas de ferramentas (${esq.esquemas.length})`));
  const caixa = el("div", "esq-ficha");
  for (const e of esq.esquemas) caixa.appendChild(cartaoEsquema(e));
  corpo.appendChild(caixa);
  const falta = esq.esquemas.length - lidos;
  const linha = el("div", "linha");
  if (falta) {
    const b = el("button", "btn-abrir", !lidos ? "Ler os esquemas (OCR)"
      : falta === 1 ? "Ler o esquema que falta" : `Ler os ${falta} esquemas que faltam`);
    b.type = "button";
    b.title = "Baixa os PDFs (~200 KB cada) e reconhece as ferramentas; ~2 s por esquema";
    b.onclick = () => lerEsquemasPoco(b, poco);
    linha.appendChild(b);
  }
  corpo.appendChild(linha);
  corpo.appendChild(el("p", "ajuda", lidos
    ? "Ferramentas reconhecidas por OCR e conferidas com o dicionário do SIAPP — confira no PDF antes de citar."
    : "Tipo de corrida pelo nome do arquivo. Leia os esquemas para ver as ferramentas."));
}

function cartaoEsquema(e) {
  const d = e.dados || {};
  const c = el("div", "esq-cartao");
  const topo = el("div", "esq-topo");
  const nome = el("span", "esq-nome", e.nome);
  nome.title = e.caminho;
  topo.append(el("span", "selo corrida t-" + (e.tipo || "nd"), e.rotulo || "tipo não identificado"), nome);
  c.appendChild(topo);
  const info = [];
  if (d.fabricante) info.push(d.fabricante);
  if (d.carimbo && d.carimbo.data) info.push(d.carimbo.data);
  if (d.diametro_max_pol) info.push(`Ø máx. ${numero(d.diametro_max_pol, 2)}"`);
  if (d.comprimento_m) info.push(`${numero(d.comprimento_m, 2)} m`);
  if (d.metodo) info.push(d.metodo === "embutido" ? "texto do PDF" : "OCR");
  if (info.length) c.appendChild(el("div", "ajuda", info.join(" · ")));
  if (d.carimbo && d.carimbo.confere === false) {
    c.appendChild(el("div", "agp-aviso", `O carimbo diz ${d.carimbo.poco}: confira se o esquema é deste poço.`));
  }
  const ferr = (d.ferramentas || []).filter((f) => !f.apoio);
  if (ferr.length) {
    const chips = el("div", "esq-chips");
    for (const f of ferr) {
      const ch = el("span", "chip", f.codigo);
      ch.title = `${f.nome}${f.fabricante ? " · " + f.fabricante : ""}\nlido como: ${f.lido}` +
        (f.familias.length ? "\nmede: " + f.familias.map((x) => NOMES_FAMILIA_FERR[x] || x).join(", ") : "");
      chips.appendChild(ch);
    }
    c.appendChild(chips);
  }
  if ((d.familias || []).length) {
    c.appendChild(el("div", "ajuda", "Mede: " + d.familias.map((x) => NOMES_FAMILIA_FERR[x] || x).join(", ")));
  }
  if (e.erro) c.appendChild(el("div", "agp-aviso", e.erro));
  else if (d.aviso) c.appendChild(el("div", "ajuda", d.aviso));
  if (e.perfis.length) {
    c.appendChild(el("div", "esq-perfis", "Perfis desta corrida: " + e.perfis.join(", ")));
  }
  if (e.arquivo_local) {
    const b = el("button", "btn-abrir", "Abrir o PDF");
    b.type = "button";
    b.onclick = () => chamar(b, "abrir_esquema", e.arquivo_local);
    c.appendChild(b);
  }
  return c;
}

async function lerEsquemasPoco(botao, poco) {
  status(`Lendo os esquemas de ferramentas de ${poco}…`, "trab");
  const r = await chamar(botao, "ler_esquemas_poco", poco);
  if (!r.ok) return;
  if (!r.lidos) status("Os esquemas deste poço já foram lidos.", "ok");
  else status(`${r.lidos} esquema(s) lido(s)` + (r.ocr ? "." : " — sem o modelo de OCR (sem internet?): só os PDFs com texto foram lidos."),
              "ok");
  if (fichaAberta === poco || fichaAberta === r.poco) abrirFicha(fichaAberta);
}

const NOMES_TIPO_CORRIDA = {
  testador: "Teste de formação a cabo", rmn: "Ressonância magnética", imagem: "Perfil de imagem",
  mergulho: "Perfil de mergulho", amostrador: "Amostragem lateral", cimentacao: "Perfil de cimentação",
  lwd: "Perfilagem durante a perfuração", convencional: "Perfilagem convencional",
  resistividade: "Perfil de resistividade", sonico: "Perfil sônico", correlacao: "Correlação (GR/CCL)",
  sismica: "Sísmica de poço (checkshot, VSP)",
};
