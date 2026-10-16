// SIAPP — funções comuns da interface. Carregado antes dos outros scripts.
// Toda ação passa por window.pywebview.api (motor Python), via chamar().
"use strict";

const $ = (id) => document.getElementById(id);
let api = null;
let projetoAberto = false;
let baciaAnterior = "";     // última bacia usada neste projeto (siapp.json)
let baciaConectada = "";    // bacia conectada agora na aba Catálogo

// ------------------------------------------------------------------ status
function status(texto, tipo = "") {
  $("status").textContent = texto;
  document.querySelector(".rodape").className = "rodape " + tipo;
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
