// SIAPP — Configurações › Fontes e prioridade (0.63): de onde vêm os topos e as zonas, numa tela só, e como o SIAPP
// conta "perfil digital" (o critério de cada número). Cálculo no motor (motor/fontes.py, topos.py, zonas.py).
"use strict";

let fontesProjeto = null;     // {topos: {ordem, rotulos, explicacao}, zonas: {ordem, ligadas, rotulos, explicacao, tem_tabela}}

async function lerFontesProjeto() {
  if (!projetoAberto) return null;
  const r = await chamar(null, "fontes_prioridade");
  if (r.ok) fontesProjeto = r;
  return r.ok ? r : null;
}

// Uma lista de fontes com ↑ ↓ (e, nas zonas, a caixa "vale"). Cada mudança grava na hora.
function listaFontes(tema, dados) {
  const ul = el("ol", "fp-lista");
  ul.id = "fp-" + tema;
  const ordem = [...dados.ordem];
  const ligadas = new Set(dados.ligadas || ordem);
  const gravar = async () => {
    const r = await chamar(null, "fontes_prioridade_salvar", tema, ordem, tema === "zonas" ? [...ligadas] : null);
    if (!r.ok) return;
    fontesProjeto = r;
    const t = r[tema];
    const usadas = t.ordem.filter((f) => !t.ligadas || t.ligadas.includes(f)).map((f) => t.rotulos[f]);
    status(`${tema === "topos" ? "Fontes de topo" : "Fontes das zonas"}: ${usadas.join(" → ")}.`, "ok");
    aoMudarFontes();
  };
  const desenhar = () => {
    limpar(ul);
    ordem.forEach((f, k) => {
      const li = el("li", ligadas.has(f) ? "" : "fp-desligada");
      li.dataset.fonte = f;
      const nome = el("span", "fp-nome", dados.rotulos[f] || f);
      if (tema === "zonas") {
        const cx = el("input");
        cx.type = "checkbox";
        cx.checked = ligadas.has(f);
        cx.title = "Usar esta fonte";
        cx.onchange = () => { if (cx.checked) ligadas.add(f); else ligadas.delete(f); desenhar(); gravar(); };
        const rot = el("label", "opcao");
        rot.append(cx, nome);
        li.appendChild(rot);
        if (f === "tabela" && !dados.tem_tabela) {
          cx.disabled = true;
          li.appendChild(el("span", "ajuda fp-nota", "nenhuma importada (Modelo 3D › Zonas produtoras)"));
        }
      } else {
        li.appendChild(nome);
      }
      const sobe = el("button", "btn secundario pequeno", "↑");
      sobe.type = "button";
      sobe.title = "Mais prioridade";
      sobe.disabled = k === 0;
      sobe.onclick = () => { [ordem[k - 1], ordem[k]] = [ordem[k], ordem[k - 1]]; desenhar(); gravar(); };
      const desce = el("button", "btn secundario pequeno", "↓");
      desce.type = "button";
      desce.title = "Menos prioridade";
      desce.disabled = k === ordem.length - 1;
      desce.onclick = () => { [ordem[k + 1], ordem[k]] = [ordem[k], ordem[k + 1]]; desenhar(); gravar(); };
      li.append(el("span", "fp-setas"), sobe, desce);
      ul.appendChild(li);
    });
  };
  desenhar();
  return ul;
}

async function carregarFontes() {
  const box = limpar($("cfg-fontes"));
  if (!projetoAberto) { box.appendChild(el("p", "ajuda", "Abra o projeto primeiro (Início).")); return; }
  const r = await lerFontesProjeto();
  if (!r) return;
  box.appendChild(el("p", "ajuda", "Vale para o projeto inteiro (fica no banco do projeto). A ordem é a prioridade: a fonte de " +
    "cima ganha quando duas trazem o mesmo dado. Cada mudança é gravada na hora."));
  box.append(el("h3", "", "Topos de formação"), el("p", "ajuda", r.topos.explicacao), listaFontes("topos", r.topos));
  box.append(el("h3", "", "Zonas produtoras (Modelo 3D)"), el("p", "ajuda", r.zonas.explicacao), listaFontes("zonas", r.zonas));
  const cont = el("div", "fp-contagens");
  cont.id = "fp-contagens";
  box.append(el("h3", "", "Como o SIAPP conta “perfil digital”"), cont);
  desenharContagensPerfil(cont);
}

async function desenharContagensPerfil(caixa, bacia = "") {
  const r = await chamar(null, "contagens_perfil", bacia);
  if (!r.ok) return;
  limpar(caixa);
  caixa.appendChild(el("p", "ajuda", "Três telas mostram quantos poços têm perfil digital, cada uma por um critério. Os números " +
    "não precisam bater: cada um responde a uma pergunta diferente. Todos contam poços distintos (um poço com duas pastas " +
    "no portal conta uma vez)."));
  const sel = el("select");
  sel.id = "fp-bacia";
  sel.appendChild(new Option("todas as bacias", ""));
  for (const o of $("sel-bacia").options) sel.appendChild(new Option(o.value, o.value));
  sel.value = bacia;
  sel.onchange = () => desenharContagensPerfil(caixa, sel.value);
  const rot = el("label", "", "Bacia ");
  rot.appendChild(sel);
  caixa.appendChild(rot);
  const t = el("table", "fp-tabela");
  for (const c of r.criterios) {
    const tr = el("tr");
    tr.dataset.criterio = c.chave;
    tr.append(el("th", "", c.rotulo), el("td", "n", numero(c.n, 0)), el("td", "ajuda", c.explicacao));
    t.appendChild(tr);
  }
  caixa.appendChild(t);
  const notas = [];
  if (r.so_conteudo) notas.push(`${numero(r.so_conteudo, 0)} poço(s) têm perfil digital conferido, mas fora de uma pasta com nome de perfil digital`);
  if (r.so_pasta) notas.push(`${numero(r.so_pasta, 0)} poço(s) têm a pasta, mas o levantamento não achou perfil digital dentro`);
  if (notas.length) caixa.appendChild(el("p", "ajuda", notas.join("; ") + "."));
  caixa.appendChild(el("p", "ajuda", `O painel da Comunidade usa “baixado ou conferido no portal”: ${numero(r.baixado_ou_conteudo, 0)} poço(s).`));
}

// Outras telas mostram um resumo da ordem e um botão para cá.
function resumoFontes(tema) {
  const t = fontesProjeto && fontesProjeto[tema];
  if (!t) return "";
  return t.ordem.filter((f) => !t.ligadas || t.ligadas.includes(f)).map((f, k) => `${k + 1}. ${t.rotulos[f]}`).join(" → ");
}

function botaoMudarFontes() {
  const b = el("button", "btn secundario pequeno", "Mudar em Fontes e prioridade…");
  b.type = "button";
  b.onclick = () => abrirConfig("fontes");
  return b;
}

function botaoMudarCriterios() {
  const b = el("button", "link", "Ver os outros critérios");
  b.type = "button";
  b.onclick = () => abrirConfig("fontes");
  return b;
}

function aoMudarFontes() {
  if ($("co-precedencia")) desenharPrecedencia($("co-precedencia"));
  if ($("bz-fontes")) desenharFontesZona();
}
