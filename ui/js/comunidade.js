// SIAPP — aba Comunidade: autoria, exportar/importar pacotes e base comunitária.
"use strict";

function descreverItens(it) {
  const p = [];
  if (it.correcoes) p.push(`${it.correcoes} correção(ões)`);
  if (it.palavras) p.push(`${it.palavras} palavra(s)`);
  if (it.manter_original) p.push(`${it.manter_original} “OCR estava certo”`);
  if (it.fatos) p.push(`${it.fatos} dado(s) transcrito(s)`);
  if (it.apelidos) p.push(`${it.apelidos} nome(s) de poço`);
  return p.join(" · ") || "nada";
}

async function carregarComunidade() {
  if (!projetoAberto) {
    $("com-local").textContent = "Abra o projeto primeiro (aba Início ou Catálogo).";
    return;
  }
  const r = await chamar(null, "comunidade");
  if (!r.ok) return;
  const a = r.autor || {};
  $("autor-nome").value = a.nome || "";
  $("autor-inst").value = a.instituicao || "";
  $("autor-orcid").value = a.orcid || "";
  const l = r.local;
  $("com-local").textContent =
    `Neste computador: ${l.correcoes} correção(ões), ${l.palavras} palavra(s), ` +
    `${l.manter_original} “OCR estava certo”, ${l.fatos} dado(s) transcrito(s). ` +
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
      if (r.ok) { status(`Pacote de ${p.autor} desfeito. ${r.paginas_atualizadas} página(s) atualizadas.`, "ok"); carregarComunidade(); }
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
  status("Contribuição exportada. Envie o arquivo ao repositório SIAPP-dados.", "ok");
  carregarComunidade();
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
    (pv.fatos_repetidos ? ` · ${pv.fatos_repetidos} dado(s) que você já tem` : "")));
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
    carregarComunidade();
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
         `${r.resumo.fatos} dado(s). ${r.paginas_atualizadas} página(s) atualizadas.`, "ok");
  carregarComunidade();
}

function ligarComunidade() {
  $("form-autor").onsubmit = salvarAutor;
  $("btn-exportar").onclick = exportarPacote;
  $("btn-pasta-contrib").onclick = () => chamar($("btn-pasta-contrib"), "abrir_pasta_contribuicoes");
  $("btn-importar").onclick = escolherPacote;
  $("btn-base").onclick = () => atualizarBase($("btn-base"), "atualizar_base");
  $("btn-base-arquivo").onclick = () => atualizarBase($("btn-base-arquivo"), "importar_base_arquivo");
}
