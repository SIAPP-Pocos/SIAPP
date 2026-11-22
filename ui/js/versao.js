// SIAPP — versão nova do SIAPP (1.3): ao abrir, procura no GitHub (uma vez por dia), avisa e, com um clique, baixa o
// instalador, confere o arquivo, fecha, instala e abre de novo sozinho (motor/atualizacao.py, ponte/atualizacao.py).
"use strict";

let versaoNova = null;        // a resposta de verificar_versao quando há versão mais nova que esta

async function procurarVersaoNova(forcar = false, botao = null) {
  let r;
  if (forcar) r = await chamar(botao, "verificar_versao", true);
  else {
    try { r = await api.verificar_versao(false); } catch (e) { return; }    // sem internet: nada aparece
  }
  if (!r || !r.ok || r.desligado) return;
  versaoNova = r.nova ? r : null;
  const item = $("menu-versao-nova");
  item.hidden = !r.nova;
  item.textContent = r.nova ? `Atualizar o SIAPP para a ${r.versao}` : "";
  $("btn-ajuda").classList.toggle("com-aviso", Boolean(r.nova && !r.pulada));
  if (forcar) {
    if (r.nova) abrirVersaoNova();
    else status(r.publicada ? `Você já tem a versão mais nova do SIAPP (${r.atual}).`
                            : "Ainda não há versão publicada no GitHub.", "ok");
  } else if (r.nova && !r.pulada) {
    avisoVersaoNova(r);
  }
}

// Aviso no canto que não some sozinho: "Ver e atualizar" ou "Depois"
function avisoVersaoNova(r) {
  const caixa = $("avisos");
  if (!caixa || caixa.querySelector(".aviso-versao")) return;
  const a = el("div", "aviso ok aviso-versao");
  a.setAttribute("role", "status");
  const t = el("p", "aviso-versao-texto");
  t.append(el("strong", "", `Saiu o SIAPP ${r.versao}${r.de_teste ? " (versão de teste)" : ""}`),
           document.createTextNode(` (você tem a ${r.atual}).`));
  a.appendChild(t);
  const linha = el("div", "aviso-versao-botoes");
  const ver = el("button", "btn pequeno", r.pode_instalar ? "Ver e atualizar" : "Ver o que mudou");
  ver.type = "button";
  ver.onclick = (e) => { e.stopPropagation(); a.remove(); abrirVersaoNova(); };
  const depois = el("button", "btn secundario pequeno", "Depois");
  depois.type = "button";
  depois.onclick = (e) => { e.stopPropagation(); a.remove(); };
  linha.append(ver, depois);
  a.appendChild(linha);
  caixa.appendChild(a);
}

// O texto da versão no GitHub (o trecho do CHANGELOG) em blocos simples: títulos, itens e parágrafos
function notasDaVersao(texto) {
  const box = el("div", "versao-notas");
  let lista = null, ultimo = null;
  const limparMd = (t) => t.replace(/\*\*|`/g, "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").trim();
  for (const linha of String(texto || "").split("\n")) {
    if (!linha.trim()) { lista = null; ultimo = null; continue; }
    const t = linha.match(/^#{1,6}\s+(.*)/);
    const item = linha.match(/^\s*[-*]\s+(.*)/);
    if (t) {
      lista = null;
      ultimo = el("h4", "", limparMd(t[1]));
      box.appendChild(ultimo);
    } else if (item) {
      if (!lista) { lista = el("ul"); box.appendChild(lista); }
      ultimo = el("li", "", limparMd(item[1]));
      lista.appendChild(ultimo);
    } else if (ultimo && /^\s+/.test(linha) && ultimo.tagName !== "H4") {
      ultimo.textContent += " " + limparMd(linha);                  // continuação do item ou do parágrafo
    } else {
      lista = null;
      ultimo = el("p", "", limparMd(linha));
      box.appendChild(ultimo);
    }
  }
  if (!box.childNodes.length) box.appendChild(el("p", "ajuda", "O GitHub não trouxe a lista do que mudou."));
  return box;
}

function abrirVersaoNova() {
  const r = versaoNova;
  if (!r) { procurarVersaoNova(true); return; }
  const c = el("div", "dlg-versao");
  const cab = el("div", "versao-cab");
  const masc = el("img", "versao-masc");
  masc.src = "img/mascote/joinha.png";
  masc.alt = "";
  const fala = el("div");
  fala.append(el("p", "versao-fala", r.de_teste ? `Versão de teste: SIAPP ${r.versao}` : `Saiu o SIAPP ${r.versao}!`),
              el("p", "ajuda", `Você está com a ${r.atual}` +
                 (r.publicada_em ? `. Publicada em ${dataCurta(r.publicada_em)}.` : ".")));
  cab.append(masc, fala);
  c.append(cab, el("h3", "", "O que mudou"), notasDaVersao(r.notas));
  const como = el("p", "versao-como");
  if (r.pode_instalar) {
    como.textContent = `Atualizar agora baixa a versão nova (${Math.max(1, Math.round(r.bytes / 1e6))} MB), confere o ` +
      "arquivo, fecha o SIAPP, instala e abre de novo sozinho, em cerca de um minuto. Seus projetos não mudam: " +
      "continuam na mesma pasta.";
  } else if (r.instalado) {
    como.textContent = "O instalador desta versão ainda está sendo preparado no GitHub (leva uns minutos depois que a " +
      "versão sai). Tente de novo daqui a pouco, ou baixe pela página da versão.";
  } else {
    como.textContent = "Este SIAPP roda do código (pasta clonada do GitHub): atualize com git pull, ou baixe o " +
      "instalador na página da versão.";
  }
  c.appendChild(como);
  const msg = el("p", "versao-msg");
  msg.id = "versao-msg";
  c.appendChild(msg);

  const botoes = [];
  if (r.pode_instalar) {
    const b = botaoDialogo("Atualizar agora", "btn", () => atualizarAgora(b, msg));
    b.id = "versao-atualizar";
    botoes.push(b);
  }
  const pagina = el("a", "btn secundario", "Página da versão");
  pagina.href = r.pagina;
  pagina.target = "_blank";        // o pywebview abre no navegador do sistema
  pagina.rel = "noopener";
  botoes.push(pagina);
  botoes.push(botaoDialogo("Pular esta versão", "btn secundario", async () => {
    await chamar(null, "pular_versao", r.versao);
    $("btn-ajuda").classList.remove("com-aviso");
    fecharDialogo();
    status(`Não vou mais avisar da ${r.versao}. Ela continua em Ajuda › Atualizar o SIAPP.`, "ok");
  }));
  botoes.push(botaoDialogo("Agora não", "btn secundario", fecharDialogo));
  abrirDialogo("Versão nova do SIAPP", c, botoes, "largo versao-dlg");
}

async function atualizarAgora(botao, msg) {
  const t = await chamar(null, "trabalho_em_andamento");
  if (t.ok && (t.downloads || t.leitura) && !botao.dataset.confirmado) {
    const o_que = [t.downloads && "downloads do REATE", t.leitura && "leitura de documentos"].filter(Boolean).join(" e ");
    msg.textContent = `Há ${o_que} em andamento. Se atualizar agora, eles param; ao abrir de novo, é só mandar ` +
      "continuar (o que já terminou fica salvo).";
    msg.className = "versao-msg aviso";
    botao.dataset.confirmado = "1";
    botao.textContent = "Atualizar mesmo assim";
    return;
  }
  const outros = [...document.querySelectorAll("#dlg-pe .btn")];
  outros.forEach((b) => { b.disabled = true; });
  msg.className = "versao-msg";
  msg.textContent = "Baixando a versão nova… (o andamento aparece na barra de baixo)";
  const r = await chamar(botao, "baixar_versao");
  if (!r.ok) {
    outros.forEach((b) => { b.disabled = false; });
    msg.className = "versao-msg erro";
    msg.textContent = r.erro || "O download não terminou. Tente de novo.";
    return;
  }
  msg.textContent = "Arquivo conferido. O SIAPP vai fechar, instalar e abrir de novo sozinho em cerca de um minuto.";
  status(`Instalando o SIAPP ${r.versao}…`, "trab");
  const i = await chamar(null, "instalar_versao");
  if (!i.ok) {
    outros.forEach((b) => { b.disabled = false; });
    msg.className = "versao-msg erro";
    msg.textContent = i.erro || "Não consegui abrir o instalador.";
  }
}
