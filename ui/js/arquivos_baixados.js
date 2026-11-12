// SIAPP — Acervo › Meus arquivos: tudo o que está em bruto/, em árvore (bacia › poço › pasta) e lista,
// com o que o SIAPP fez com cada arquivo. Abrir, mostrar no Explorer, ver na ficha e mandar para a Lixeira.

const ab = { dados: null, no: null, abertos: new Set(), limite: 200, confirmando: null };
const GRUPOS_ESTADO = { lidos: ["lido", "texto", "perfil"], nao_lidos: ["pendente", "sem_leitor"], problema: ["erro", "incompleto"] };
const NOMES_ESTADO = { lido: "lido", texto: "texto extraído", perfil: "perfil", pendente: "não lido", sem_leitor: "sem leitor",
  erro: "erro", incompleto: "incompleto" };

function dataBr(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  return m ? `${m[3]}/${m[2]}/${m[1]}` : "—";
}

async function carregarBaixados() {
  if (!api || !$("ab-lista")) return;
  const r = await chamar(null, "arquivos_baixados");
  if (!r.ok) return;
  ab.dados = r;
  preencherFiltrosBaixados(r);
  desenharBaixados();
}

function preencherFiltrosBaixados(r) {
  const cat = $("ab-categoria"), bac = $("ab-bacia");
  const cat0 = cat.value, bac0 = bac.value;
  limpar(cat);
  cat.appendChild(new Option("todos", ""));
  for (const [k, v] of Object.entries(r.categorias)) cat.appendChild(new Option(v, k));
  limpar(bac);
  bac.appendChild(new Option("todas", ""));
  for (const b of r.bacias) bac.appendChild(new Option(b, b));
  cat.value = cat0;
  bac.value = bac0;
}

function passaFiltroBaixado(a) {
  const t = $("ab-busca").value.trim().toLowerCase();
  if (t && !`${a.nome} ${a.poco} ${a.pasta} ${a.formato}`.toLowerCase().includes(t)) return false;
  const c = $("ab-categoria").value;
  if (c && a.categoria !== c) return false;
  const g = $("ab-estado").value;
  if (g && !GRUPOS_ESTADO[g].includes(a.estado)) return false;
  const b = $("ab-bacia").value;
  return !b || a.bacia === b;
}

function arvoreBaixados(lista) {
  const raiz = new Map();
  const somar = (no, a) => { no.n += 1; no.bytes += a.bytes; };
  for (const a of lista) {
    const bn = raiz.get(a.bacia || "(sem bacia)") || raiz.set(a.bacia || "(sem bacia)", { n: 0, bytes: 0, filhos: new Map() }).get(a.bacia || "(sem bacia)");
    somar(bn, a);
    const pn = bn.filhos.get(a.poco || "(solto)") || bn.filhos.set(a.poco || "(solto)", { n: 0, bytes: 0, filhos: new Map() }).get(a.poco || "(solto)");
    somar(pn, a);
    const pasta = a.pasta || "(raiz do poço)";
    const fn = pn.filhos.get(pasta) || pn.filhos.set(pasta, { n: 0, bytes: 0, filhos: new Map() }).get(pasta);
    somar(fn, a);
  }
  return raiz;
}

function chaveNo(no) { return [no.bacia, no.poco, no.pasta].filter((x) => x != null).join(""); }

function arquivoDoNo(a) {
  const n = ab.no;
  if (!n) return true;
  if ((a.bacia || "(sem bacia)") !== n.bacia) return false;
  if (n.poco != null && (a.poco || "(solto)") !== n.poco) return false;
  return n.pasta == null || (a.pasta || "(raiz do poço)") === n.pasta;
}

function desenharBaixados() {
  if (!ab.dados) return;
  const todos = ab.dados.arquivos;
  const filtrados = todos.filter(passaFiltroBaixado);
  $("ab-resumo").textContent = filtrados.length === todos.length
    ? `${numero(todos.length, 0)} arquivo(s), ${tamanho(ab.dados.bytes)}.`
    : `${numero(filtrados.length, 0)} de ${numero(todos.length, 0)} arquivo(s) pelos filtros (${tamanho(filtrados.reduce((s, a) => s + a.bytes, 0))}).`;
  // árvore
  const caixa = limpar($("ab-arvore"));
  const raiz = arvoreBaixados(filtrados);
  const todosLink = el("button", "ab-rotulo" + (ab.no ? "" : " ativo"), "Todos os arquivos");
  todosLink.onclick = () => { ab.no = null; ab.limite = 200; desenharBaixados(); };
  caixa.appendChild(todosLink);
  const ul = el("ul");
  caixa.appendChild(ul);
  const linha = (pai, rotulo, no, ident, temFilhos) => {
    const li = el("li");
    const topo = el("div", "ab-no");
    const k = chaveNo(ident);
    const seta = el("button", "ab-seta", temFilhos ? (ab.abertos.has(k) ? "▾" : "▸") : "");
    if (temFilhos) seta.onclick = () => { ab.abertos.has(k) ? ab.abertos.delete(k) : ab.abertos.add(k); desenharBaixados(); };
    const ativo = ab.no && chaveNo(ab.no) === k;
    const b = el("button", "ab-rotulo" + (ativo ? " ativo" : ""));
    b.append(rotulo, el("span", "ab-n", `${no.n} · ${tamanho(no.bytes)}`));
    b.onclick = () => { ab.no = ident; ab.abertos.add(k); ab.limite = 200; desenharBaixados(); };
    topo.append(seta, b);
    li.appendChild(topo);
    pai.appendChild(li);
    return li;
  };
  for (const [bacia, bn] of raiz) {
    const li = linha(ul, bacia, bn, { bacia }, bn.filhos.size > 0);
    if (!ab.abertos.has(chaveNo({ bacia }))) continue;
    const u2 = el("ul");
    li.appendChild(u2);
    for (const [poco, pn] of bn.filhos) {
      const l2 = linha(u2, poco, pn, { bacia, poco }, pn.filhos.size > 0);
      if (!ab.abertos.has(chaveNo({ bacia, poco }))) continue;
      const u3 = el("ul");
      l2.appendChild(u3);
      for (const [pasta, fn] of pn.filhos) linha(u3, pasta, fn, { bacia, poco, pasta }, false);
    }
  }
  // lista
  desenharListaBaixados(filtrados.filter(arquivoDoNo));
}

function desenharListaBaixados(lista) {
  const caixa = limpar($("ab-lista"));
  if (!lista.length) {
    caixa.appendChild(el("p", "ajuda", ab.dados.n ? "Nenhum arquivo com estes filtros." : "Ainda não há arquivos baixados neste projeto. Baixe em Acervo › Catálogo do REATE ou Procurar por tipo de dado."));
    return;
  }
  const t = el("table", "tabela");
  const cab = el("tr");
  for (const h of ["Arquivo", "Formato", "Tamanho", "Baixado em", "O que o SIAPP fez", "Onde aparece", ""]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const a of lista.slice(0, ab.limite)) {
    const tr = el("tr");
    const nome = el("td", "ab-nome");
    nome.append(a.nome);
    nome.appendChild(el("span", "ab-pasta", [a.poco, a.pasta].filter(Boolean).join(" / ")));
    const est = el("td");
    est.appendChild(el("span", `ab-estado ${a.estado}`, NOMES_ESTADO[a.estado] || a.estado));
    est.appendChild(el("span", "ab-pasta", a.situacao));
    const acoes = el("td", "ab-acoes");
    const abrir = el("button", "btn secundario pequeno", "Abrir");
    abrir.disabled = !a.pode_abrir;
    abrir.title = a.pode_abrir ? "Abrir no programa padrão do Windows" : "Programas e scripts não abrem pelo SIAPP: use Mostrar na pasta";
    abrir.onclick = () => chamar(abrir, "abrir_arquivo_baixado", a.rel);
    const mostrar = el("button", "btn secundario pequeno", "Mostrar na pasta");
    mostrar.onclick = () => chamar(mostrar, "mostrar_arquivo_na_pasta", a.rel);
    const ficha = el("button", "btn secundario pequeno", "Ver na ficha");
    ficha.disabled = !a.poco_id;
    ficha.title = a.poco_id ? "Abrir a ficha do poço no Mapa" : "O SIAPP não reconheceu o poço desta pasta";
    ficha.onclick = () => { $("aba-mapa").click(); abrirFicha(a.poco_id); };
    const apagar = el("button", "btn secundario pequeno perigo", "Apagar");
    apagar.onclick = () => { ab.confirmando = ab.confirmando === a.rel ? null : a.rel; desenharBaixados(); };
    acoes.append(abrir, mostrar, ficha, apagar);
    tr.append(nome, el("td", "", a.formato), el("td", "n", tamanho(a.bytes)), el("td", "", dataBr(a.data)), est,
              el("td", "", a.onde || "—"), acoes);
    t.appendChild(tr);
    if (ab.confirmando === a.rel) t.appendChild(linhaConfirmarApagar(a));
  }
  caixa.appendChild(t);
  if (lista.length > ab.limite) {
    const mais = el("button", "btn secundario", `Mostrar mais (${lista.length - ab.limite} restantes)`);
    mais.onclick = () => { ab.limite += 200; desenharBaixados(); };
    caixa.appendChild(mais);
  }
}

function linhaConfirmarApagar(a) {
  const tr = el("tr", "ab-confirmar");
  const td = el("td");
  td.colSpan = 7;
  td.appendChild(el("p", "ajuda", "Calculando o que isso afeta…"));
  tr.appendChild(td);
  chamar(null, "impacto_apagar_arquivo", a.rel).then((r) => {
    limpar(td);
    if (!r.ok) { ab.confirmando = null; return; }
    const sai = [];
    if (r.sai.dados_do_poco) sai.push(`${r.sai.dados_do_poco} dado(s) do poço lido(s) deste arquivo`);
    if (r.sai.perfil_inventariado) sai.push("o perfil inventariado (curvas)");
    if (r.sai.texto_extraido) sai.push("o texto extraído e a busca nele");
    const fica = [];
    if (r.fica.transcricoes) fica.push(`${r.fica.transcricoes} transcrição(ões)`);
    if (r.fica.paginas_corrigidas) fica.push(`${r.fica.paginas_corrigidas} página(s) corrigida(s)`);
    td.appendChild(el("p", "", `Mandar «${r.nome}» (${tamanho(r.bytes)}) para a Lixeira do Windows?`));
    td.appendChild(el("p", "ajuda", "Dá para restaurar pela Lixeira. " +
      (sai.length ? `Sai do SIAPP: ${sai.join("; ")}. ` : "O SIAPP não tinha lido nada deste arquivo. ") +
      (fica.length ? `Seu trabalho continua no banco (${fica.join(" e ")}), mas perde o arquivo de origem. ` : "") +
      "Para ter o arquivo de volta no SIAPP, baixe de novo ou restaure e reabra o projeto."));
    const ok = el("button", "btn perigo", "Mandar para a Lixeira");
    const nao = el("button", "btn secundario", "Cancelar");
    nao.onclick = () => { ab.confirmando = null; desenharBaixados(); };
    ok.onclick = async () => {
      ok.disabled = true;
      const x = await chamar(null, "apagar_arquivo_baixado", a.rel);
      ab.confirmando = null;
      if (x.ok) status(`«${r.nome}» foi para a Lixeira.`, "ok");
      carregarBaixados();
    };
    const linha = el("div", "linha");
    linha.append(ok, nao);
    td.appendChild(linha);
  });
  return tr;
}

function iniciarBaixados() {
  if (!$("ab-busca")) return;
  // A busca reage ao digitar; as listas, ao mudar. (Se a busca também reagisse ao "change", que dispara quando o campo
  // perde o foco, clicar num botão da lista logo depois de digitar redesenharia a lista no meio do clique e o perderia.)
  const redesenhar = () => { ab.limite = 200; desenharBaixados(); };
  $("ab-busca").oninput = redesenhar;
  for (const id of ["ab-categoria", "ab-estado", "ab-bacia"]) $(id).onchange = redesenhar;
  $("ab-limpar").onclick = () => {
    $("ab-busca").value = ""; $("ab-categoria").value = ""; $("ab-estado").value = ""; $("ab-bacia").value = "";
    ab.no = null; desenharBaixados();
  };
  $("ab-atualizar").onclick = carregarBaixados;
}
iniciarBaixados();
