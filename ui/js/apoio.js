// SIAPP — tela "Apoie o SIAPP" (0.67; refeita na 1.3): o mascote, quem faz o SIAPP, o Pix com valores e QR Code
// e outras formas de ajudar sem dinheiro. Os textos, a chave, o LinkedIn e os valores vêm de recursos/doacao.json
// (motor/doacao.py); nada aqui é inventado. Doar é opcional e a tela diz isso.
"use strict";

const REPO_SIAPP = "https://github.com/SIAPP-Pocos/SIAPP";

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
  const cab = el("div", "apoio-sobre-cab");
  cab.appendChild(el("h3", "", "Quem faz o SIAPP"));
  if (d.linkedin) {
    const p = el("p", "apoio-linkedin");
    p.appendChild(linkExterno("Fale comigo no LinkedIn", d.linkedin));
    cab.appendChild(p);
  }
  sec.appendChild(cab);
  for (const p of d.sobre) sec.appendChild(el("p", "", p));
  if (d.publicacoes && d.publicacoes.length) {
    sec.appendChild(el("h4", "apoio-pub-titulo", "Trabalhos publicados nos PIBICs"));
    const ul = el("ul", "apoio-pub");
    for (const t of d.publicacoes) {
      const li = el("li");
      li.appendChild(t.url ? linkExterno(t.titulo, t.url) : el("span", "", t.titulo));
      if (t.evento) li.appendChild(el("span", "ajuda", t.evento));
      ul.appendChild(li);
    }
    sec.appendChild(ul);
  }
  return sec;
}

function blocoOutrasFormas() {
  const sec = el("section", "apoio-outras");
  sec.appendChild(el("p", "apoio-outras-intro", "Também ajuda muito, e não custa nada:"));
  const ul = el("ul");
  const item = (titulo, texto, acao) => {
    const li = el("li");
    const linha = el("div", "apoio-outras-linha");
    linha.appendChild(el("strong", "", titulo));
    if (acao) linha.appendChild(acao);
    li.append(linha, el("span", "", texto));
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

// 1.3: o lado direito tem duas abas, "Com um Pix" e "Sem dinheiro", para caber tudo sem rolar a tela
function ladoDeApoio(d) {
  const lado = el("div", "apoio-lado");
  const abas = el("div", "apoio-abas");
  abas.setAttribute("role", "tablist");
  const paineis = [];
  if (d.pix || d.links.length) {
    const p = d.pix ? blocoPix(d) : el("section", "apoio-pix");
    if (d.links.length) {
      p.appendChild(el("h4", "apoio-pub-titulo", d.pix ? "Outras formas de doar" : "Como apoiar"));
      const ul = el("ul", "doacao-links");
      for (const l of d.links) {
        const li = el("li");
        li.append(linkExterno(l.rotulo, l.url), el("span", "ajuda", " " + l.url));
        ul.appendChild(li);
      }
      p.appendChild(ul);
    }
    paineis.push(["Com um Pix", p]);
  }
  paineis.push(["Sem dinheiro", blocoOutrasFormas()]);
  const mostrar = (i) => paineis.forEach(([, p], j) => {
    p.hidden = i !== j;
    abas.children[j].setAttribute("aria-selected", String(i === j));
  });
  paineis.forEach(([rotulo, p], i) => {
    const b = el("button", "apoio-aba", rotulo);
    b.type = "button";
    b.setAttribute("role", "tab");
    b.dataset.aba = rotulo === "Sem dinheiro" ? "outras" : "pix";
    b.onclick = () => mostrar(i);
    abas.appendChild(b);
    p.setAttribute("role", "tabpanel");
  });
  lado.append(abas, ...paineis.map(([, p]) => p));
  mostrar(0);
  return lado;
}

function abrirDoacao() {
  const d = doacaoConfig;
  if (!d) return;
  const c = el("div", "dlg-doacao apoio");
  const cab = el("div", "apoio-cab");
  const masc = el("img", "apoio-masc");
  masc.src = "img/mascote/acenando.png";
  masc.alt = "";
  const fala = el("div", "apoio-fala-caixa");
  fala.append(el("p", "apoio-fala", d.texto),
              el("p", "apoio-opcional", "Doar é opcional: o SIAPP é gratuito e continua igual para todos. Obrigado por usar!"));
  cab.append(masc, fala);
  c.appendChild(cab);
  const colunas = el("div", "apoio-colunas");
  if (d.sobre.length) colunas.appendChild(blocoSobre(d));
  colunas.appendChild(ladoDeApoio(d));
  c.appendChild(colunas);
  abrirDialogo(d.titulo, c, [], "largo apoio-dlg");
}
