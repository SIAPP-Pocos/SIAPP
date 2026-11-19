// SIAPP — tela "Apoie o SIAPP" (0.67; refeita na 1.3): o mascote, quem faz o SIAPP, o Pix com valores e QR Code
// e outras formas de ajudar sem dinheiro. Os textos, a chave, o LinkedIn e os valores vêm de recursos/doacao.json
// (motor/doacao.py); nada aqui é inventado. Doar é opcional e a tela diz isso.
"use strict";

const REPO_SIAPP = "https://github.com/SIAPP-Perfis/SIAPP";

function linkExterno(rotulo, url) {
  const a = el("a", "", rotulo);
  a.href = url;
  a.target = "_blank";           // o pywebview abre no navegador do sistema
  a.rel = "noopener";
  return a;
}

// Linha "rótulo | campo | Copiar" cujo valor pode mudar depois (o "copia e cola" muda com o valor escolhido)
function linhaCopiavelViva(rotulo, valor, id) {
  const caixa = el("div", "doacao-linha");
  const campo = el("input");
  campo.readOnly = true;
  campo.value = valor;
  campo.id = id;
  campo.onfocus = () => campo.select();
  const b = el("button", "btn secundario pequeno", "Copiar");
  b.type = "button";
  b.onclick = async () => { if (!(await copiarParaDoacao(campo.value, b))) { campo.focus(); campo.select(); } };
  caixa.append(el("label", "doacao-rotulo", rotulo), campo, b);
  return caixa;
}

function valorEmReais(v) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function blocoPix(d) {
  const sec = el("section", "apoio-pix");
  sec.appendChild(el("h3", "", "Apoie com um Pix"));
  const botoes = el("div", "apoio-valores");
  const qr = el("img", "apoio-qr");
  qr.alt = "QR Code do Pix";
  qr.id = "doacao-qr";
  const legenda = el("p", "apoio-qr-legenda", "Você escolhe o valor no app do banco.");
  legenda.id = "doacao-valor";
  const codigo = linhaCopiavelViva("Pix copia e cola", d.pix.copia_e_cola, "doacao-pix-codigo");

  const mostrar = (svg) => {
    qr.hidden = !svg;
    if (svg) qr.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svg)));
  };
  const escolher = async (valor, botao) => {
    const r = await chamar(null, "doacao_pix", valor);
    if (!r.ok) return;
    for (const b of botoes.querySelectorAll(".apoio-valor")) b.setAttribute("aria-pressed", String(b === botao));
    $("doacao-pix-codigo").value = r.copia_e_cola;
    legenda.textContent = r.valor ? `${valorEmReais(r.valor)} · aponte a câmera do celular ou use o copia e cola`
                                  : "Você escolhe o valor no app do banco.";
    mostrar(r.qr_svg);
  };

  for (const v of d.valores) {
    const b = el("button", "apoio-valor");
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    b.append(el("strong", "", v.rotulo), el("span", "", valorEmReais(v.valor)));
    b.onclick = () => escolher(v.valor, b);
    botoes.appendChild(b);
  }
  // outro valor: campo + botão
  const outro = el("form", "apoio-outro");
  const campo = el("input");
  campo.id = "doacao-outro";
  campo.inputMode = "decimal";
  campo.placeholder = "Outro valor (R$)";
  campo.setAttribute("aria-label", "Outro valor em reais");
  const ok = el("button", "btn secundario pequeno", "Gerar Pix");
  ok.type = "submit";
  outro.append(campo, ok);
  outro.onsubmit = (ev) => {
    ev.preventDefault();
    if (campo.value.trim()) escolher(campo.value.trim(), null);
  };
  sec.append(botoes, outro);

  const qrCaixa = el("div", "apoio-qr-caixa");
  qrCaixa.append(qr, legenda);
  sec.append(qrCaixa, codigo, linhaCopiavelViva(`Chave (${d.pix.tipo})`, d.pix.chave, "doacao-pix-chave"));
  sec.appendChild(el("p", "ajuda", `No app do banco: Pix › Ler QR Code, ou Pix › Pix copia e cola. ` +
    `Recebedor: ${d.pix.nome} (${d.pix.cidade}).`));
  escolher(null, null);          // começa sem valor: nada vem escolhido
  return sec;
}

function blocoSobre(d) {
  const sec = el("section", "apoio-sobre");
  sec.appendChild(el("h3", "", "Quem faz o SIAPP"));
  for (const p of d.sobre) sec.appendChild(el("p", "", p));
  if (d.linkedin) {
    const p = el("p", "apoio-linkedin");
    p.appendChild(linkExterno("Fale comigo no LinkedIn", d.linkedin));
    sec.appendChild(p);
  }
  return sec;
}

function blocoOutrasFormas() {
  const sec = el("section", "apoio-outras");
  sec.appendChild(el("h3", "", "Outras formas de ajudar, sem dinheiro"));
  const ul = el("ul");
  const item = (titulo, texto, acao) => {
    const li = el("li");
    li.append(el("strong", "", titulo), el("span", "", texto));
    if (acao) li.appendChild(acao);
    ul.appendChild(li);
  };
  item("Dê uma estrela no GitHub", "Ajuda o SIAPP a aparecer para mais gente.", linkExterno("Abrir o GitHub", REPO_SIAPP));
  item("Cite o SIAPP no seu trabalho", "No GitHub, em “Cite this repository”, a referência já vem pronta.",
       linkExterno("Ver a citação", REPO_SIAPP));
  const com = el("button", "link-botao", "Abrir a Comunidade");
  com.type = "button";
  com.onclick = () => { fecharDialogo(); trocarAba("comunidade"); };
  item("Compartilhe correções e transcrições", "Pela Comunidade, o que você conferiu poupa o trabalho do próximo.", com);
  item("Conte um problema ou sugira algo", "Cada relato deixa o programa melhor para todos.",
       linkExterno("Abrir um relato", REPO_SIAPP + "/issues"));
  item("Indique a um colega", "Quem está começando um PIBIC ou um TCC com dados da ANP é quem mais ganha tempo.", null);
  sec.appendChild(ul);
  return sec;
}

function abrirDoacao() {
  const d = doacaoConfig;
  if (!d) return;
  const c = el("div", "dlg-doacao apoio");
  const cab = el("div", "apoio-cab");
  const masc = el("img", "apoio-masc");
  masc.src = "img/mascote/acenando.png";
  masc.alt = "";
  cab.append(masc, el("p", "apoio-fala", d.texto));
  c.appendChild(cab);
  const colunas = el("div", "apoio-colunas");
  if (d.sobre.length) colunas.appendChild(blocoSobre(d));
  if (d.pix) colunas.appendChild(blocoPix(d));
  c.appendChild(colunas);
  if (d.links.length) {
    const sec = el("section", "apoio-links");
    sec.appendChild(el("h3", "", d.pix ? "Outras formas de doar" : "Como apoiar"));
    const ul = el("ul", "doacao-links");
    for (const l of d.links) {
      const li = el("li");
      li.append(linkExterno(l.rotulo, l.url), el("span", "ajuda", " " + l.url));
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    c.appendChild(sec);
  }
  c.appendChild(blocoOutrasFormas());
  const fim = el("div", "apoio-fim");
  const joinha = el("img", "apoio-joinha");
  joinha.src = "img/mascote/joinha.png";
  joinha.alt = "";
  fim.append(joinha, el("p", "", "Doar é opcional: o SIAPP é gratuito e continua igual para todos. Obrigado por usar!"));
  c.appendChild(fim);
  abrirDialogo(d.titulo, c, [], "largo apoio-dlg");
}
