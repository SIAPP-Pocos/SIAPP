// SIAPP — enviar a contribuição para a base comunitária pelo GitHub, direto daqui (1.4; ponte/envio.py).
// Entrada por código (uma vez), confirmação do que vai e acompanhamento: em conferência, em revisão, aceito…
"use strict";

let contaGithub = null;       // {login, nome} quando há conta conectada neste computador

async function desenharContaGithub() {
  const r = await chamar(null, "github_conta");
  if (!r.ok) return;
  contaGithub = r.conectado ? r : null;
  const p = limpar($("com-github"));
  if (contaGithub) {
    p.append(document.createTextNode("Conta do GitHub: "), el("strong", "", `@${r.login}`),
             document.createTextNode(" · "));
    const sair = el("button", "link-botao", "Sair");
    sair.type = "button";
    sair.onclick = async () => {
      await chamar(sair, "github_sair");
      desenharContaGithub();
      status("A conta do GitHub saiu deste computador.", "ok");
    };
    p.appendChild(sair);
  } else {
    p.textContent = "Para enviar daqui, entre com uma conta do GitHub (gratuita) na primeira vez.";
  }
}

// Entrada por código: o SIAPP mostra o código, a pessoa abre o GitHub, cola e autoriza. Devolve true se entrou.
async function entrarNoGithub() {
  const r = await chamar($("btn-enviar-com"), "github_entrar");
  if (!r.ok) return false;
  const c = el("div", "dlg-github");
  c.appendChild(el("p", "", "1. Este é o seu código de entrada:"));
  const codigo = el("div", "gh-codigo", r.codigo);
  codigo.id = "gh-codigo";
  c.appendChild(codigo);
  c.appendChild(el("p", "", "2. Abra o GitHub, cole o código e clique em Continue e depois em Authorize."));
  const abrir = el("a", "btn", "Copiar o código e abrir o GitHub");
  abrir.href = r.url;
  abrir.target = "_blank";               // o pywebview abre no navegador do sistema
  abrir.rel = "noopener";
  abrir.onclick = () => { copiarParaDoacao(r.codigo, abrir); };
  c.appendChild(abrir);
  c.appendChild(el("p", "", "3. Volte para cá: esta janela fecha sozinha quando o GitHub autorizar."));
  const espera = el("p", "gh-espera", "Esperando a autorização…");
  c.appendChild(espera);
  const nota = el("p", "ajuda");
  nota.append(document.createTextNode("O SIAPP só ganha permissão para abrir pedidos no repositório Comunidade, " +
                                      "nada na sua conta. Não tem conta? "));
  const criar = el("a", "", "Crie uma de graça");
  criar.href = "https://github.com/signup";
  criar.target = "_blank";
  criar.rel = "noopener";
  nota.append(criar, document.createTextNode("."));
  c.appendChild(nota);
  let cancelado = false;
  abrirDialogo("Entrar com o GitHub", c, [botaoDialogo("Cancelar", "btn secundario", fecharDialogo)], "gh-dlg");
  aoFecharDialogo = () => { cancelado = true; chamar(null, "github_cancelar"); };
  const a = await chamar(null, "github_aguardar");
  if (cancelado) return false;
  aoFecharDialogo = null;
  fecharDialogo();
  if (!a.ok) return false;
  status(`Conta do GitHub conectada: @${a.login}.`, "ok");
  await desenharContaGithub();
  return true;
}

async function enviarParaComunidade() {
  const b = $("btn-enviar-com");
  if (!contaGithub && !(await entrarNoGithub())) return;
  const pv = await chamar(b, "previa_envio", $("com-novos").checked);
  if (!pv.ok) return;
  if (!pv.conta.conectado) {
    contaGithub = null;
    if (!(await entrarNoGithub())) return;
  }
  const c = el("div", "dlg-envio");
  c.appendChild(el("p", "", "Vai para a base comunitária, no GitHub, com o seu nome:"));
  const a = pv.autor || {};
  c.appendChild(el("p", "envio-autor", a.nome + (a.instituicao ? ` (${a.instituicao})` : "")));
  c.appendChild(el("p", "", descreverItens(pv.itens) + "."));
  if (pv.pocos.length) {
    c.appendChild(el("p", "ajuda mono", `Poço(s): ${pv.pocos.slice(0, 20).join(", ")}` +
                                        (pv.pocos.length > 20 ? ` e mais ${pv.pocos.length - 20}` : "")));
  }
  c.appendChild(el("p", "ajuda", `Fica público (licença CC-BY 4.0: quem usar cita você), enviado pela conta ` +
    `@${pv.conta.login || contaGithub?.login || ""}. Um robô confere o pacote em minutos e o mantenedor revisa; ` +
    "aceito, ele entra na próxima base. Uma cópia fica na pasta de contribuições."));
  const msg = el("p", "envio-msg");
  c.appendChild(msg);
  const enviar = botaoDialogo("Enviar", "btn", async () => {
    enviar.disabled = true;
    msg.textContent = "Enviando…";
    const r = await chamar(enviar, "enviar_comunidade", $("com-novos").checked);
    if (!r.ok) {
      enviar.disabled = false;
      msg.textContent = r.erro || "O envio não terminou.";
      if (/Entre com a conta/.test(r.erro || "")) desenharContaGithub();
      return;
    }
    fecharDialogo();
    $("com-exportado").textContent = `Enviado: pedido nº ${r.numero} no GitHub (${descreverItens(r.itens)}). ` +
                                     `Cópia em ${r.arquivo}.`;
    status(`Enviado para a comunidade (pedido nº ${r.numero}). Acompanhe em “Seus envios”.`, "ok");
    carregarContribuir();
    carregarEnvios(false);
  });
  enviar.id = "envio-confirmar";
  abrirDialogo("Enviar para a comunidade", c, [enviar, botaoDialogo("Cancelar", "btn secundario", fecharDialogo)]);
}

const AVISO_ENVIO = {
  aceito: (n) => `Seu pacote nº ${n} foi aceito! Ele entra na próxima base da comunidade.`,
  mudanca: (n) => `O revisor pediu uma mudança no seu pacote nº ${n}. Veja em Comunidade › Seus envios.`,
  recusado: (n) => `O pacote nº ${n} não passou na conferência. Veja o motivo em Comunidade › Seus envios.`,
  nao_aceito: (n) => `O pacote nº ${n} não foi aceito. Veja o comentário do revisor em Comunidade › Seus envios.`,
  revisao: (n) => `Seu pacote nº ${n} passou na conferência e está em revisão.`,
};

async function carregarEnvios(atualizar = true, silencioso = false) {
  let r;
  try { r = silencioso ? await api.envios_comunidade(atualizar) : await chamar(null, "envios_comunidade", atualizar); }
  catch (e) { return; }
  if (!r || !r.ok) return;
  for (const m of r.mudou || []) if (AVISO_ENVIO[m.estado]) status(AVISO_ENVIO[m.estado](m.numero), "ok");
  const box = $("com-envios");
  if (!box) return;
  limpar(box);
  box.hidden = !r.envios.length;
  if (!r.envios.length) return;
  box.appendChild(el("h3", "", "Seus envios"));
  const ul = el("ul", "envios");
  for (const e of r.envios) {
    const li = el("li");
    const linha = el("div", "envio-linha");
    linha.append(el("span", `envio-estado est-${e.estado}`, e.rotulo || e.estado),
                 el("span", "", `nº ${e.numero} · ${dataCurta(e.enviado_em)} · ${descreverItens(e.itens)}`));
    if (e.url) {
      const a = el("a", "", "Ver no GitHub");
      a.href = e.url;
      a.target = "_blank";
      a.rel = "noopener";
      linha.appendChild(a);
    }
    li.appendChild(linha);
    if (e.detalhe) li.appendChild(el("pre", "envio-detalhe", e.detalhe));
    ul.appendChild(li);
  }
  box.appendChild(ul);
}
