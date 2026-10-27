// SIAPP — funções comuns da interface. Carregado antes dos outros scripts.
// Toda ação passa por window.pywebview.api (motor Python), via chamar().
"use strict";

const $ = (id) => document.getElementById(id);
let api = null;
let projetoAberto = false;
let baciaAnterior = "";     // última bacia usada neste projeto (siapp.json)
let baciaConectada = "";    // bacia conectada agora (aba Dados › Catálogo)

// ------------------------------------------------------------------ status
function status(texto, tipo = "") {
  $("status").textContent = texto;
  $("status").title = `${texto}\n(clique para ver as mensagens desta sessão)`;
  document.querySelector(".rodape").className = "rodape " + tipo;
  if (typeof anotarStatus === "function") anotarStatus(texto, tipo);
}

function liberar(idEtapa) { $(idEtapa).classList.remove("bloqueada"); }

async function chamar(botao, fn, ...args) {
  if (botao) { botao.disabled = true; botao.classList.add("ocupado"); }
  try {
    const r = await api[fn](...args);
    if (!r.ok) status(r.erro, "erro");
    return r;
  } catch (e) {
    status("Falha na comunicação com o motor: " + e, "erro");
    return { ok: false };
  } finally {
    if (botao) { botao.disabled = false; botao.classList.remove("ocupado"); }
  }
}

function tamanho(bytes) {
  if (!bytes) return "0 B";
  const un = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = bytes;
  while (v >= 1024 && i < un.length - 1) { v /= 1024; i++; }
  return (i === 0 ? v : v.toFixed(v < 10 ? 1 : 0)) + " " + un[i];
}

// Cria um elemento com classe e texto. Texto sempre por textContent (nunca
// innerHTML): nomes de arquivo e texto de OCR podem conter qualquer caractere.
function el(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto !== undefined && texto !== null) e.textContent = texto;
  return e;
}

function numero(v, casas = 1) {
  if (v === null || v === undefined || v === "" || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("pt-BR", { maximumFractionDigits: casas });
}

function limpar(no) { while (no.firstChild) no.removeChild(no.firstChild); return no; }

// "2026-10-16T10:05:00" → "16/10/2026 10:05"; "2026-10-16" → "16/10/2026".
function dataCurta(iso) {
  if (!iso) return "—";
  const [d, h] = String(iso).split("T");
  return d.split("-").reverse().join("/") + (h ? " " + h.slice(0, 5) : "");
}

// --------------------------------------------- abrir um arquivo baixado
// PDF, TIF e imagens abrem no SIAPP (aba Documentos, mesmo sem processar);
// perfis, na aba Perfis; o resto (planilha, texto, ZIP…) no programa do computador.
const EXT_VISOR = [".pdf", ".tif", ".tiff", ".png", ".jpg", ".jpeg"];
const EXT_PERFIL = [".dlis", ".lis", ".las"];

function extensao(nome) {
  const m = /\.[^./\\]+$/.exec(nome || "");
  return m ? m[0].toLowerCase() : "";
}

// `tipo` vem do motor, que olha o conteúdo ("documento", "perfil", "outro"): o
// REATE tem DLIS com extensão .tif. Sem ele, decide pela extensão.
function tipoPorExtensao(rel) {
  const ext = extensao(rel);
  return EXT_VISOR.includes(ext) ? "documento" : EXT_PERFIL.includes(ext) ? "perfil" : "outro";
}

async function abrirBaixado(rel, botao, tipo) {
  const nome = rel.split("/").pop();
  tipo = tipo || tipoPorExtensao(rel);
  if (tipo === "documento") {
    irPara("docs", "abrirPagina", rel, 1, "");
  } else if (tipo === "perfil") {
    irPara("perfis", "abrirPerfil", { rel, nome });
  } else {
    const r = await chamar(botao || null, "abrir_arquivo", rel);
    if (r.ok) status(`${nome} aberto no programa do computador.`, "ok");
  }
}

function botaoAbrir(rel, tipo) {
  tipo = tipo || tipoPorExtensao(rel);
  const [rotulo, dica] = tipo === "documento" ? ["Ver", "Ver no SIAPP (aba Documentos)"]
    : tipo === "perfil" ? ["Ver perfil", "Abrir na aba Perfis"]
    : ["Abrir", "Abrir no programa do computador"];
  const b = el("button", "btn-abrir", rotulo);
  b.type = "button";
  b.title = dica;
  b.onclick = (ev) => { ev.preventDefault(); ev.stopPropagation(); abrirBaixado(rel, b, tipo); };
  return b;
}
