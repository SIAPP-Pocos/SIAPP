// SIAPP — dados transcritos ("fatos"): cada valor com a fonte (documento, página, caixa).
"use strict";

const TIPOS_FATO = {
  topo_formacao: "Topo de formação",
  intervalo_alvo: "Intervalo-alvo",
  profundidade_final: "Profundidade final",
  revestimento: "Revestimento (sapata)",
  teste_formacao: "Teste de formação",
  canhoneio: "Canhoneio",
  mesa_rotativa: "Elevação da mesa rotativa",
  contato_fluido: "Contato de fluido",
  observacao: "Observação",
};

const ORIGEM_FATO = { local: "seu", pacote: "pacote", base: "comunidade" };

function profFato(f) {
  const t = f.prof_topo, b = f.prof_base;
  if (t === null && b === null) return "";
  if (t !== null && b !== null && b !== t) return `${numero(t, 2)}–${numero(b, 2)} m`;
  return `${numero(t !== null ? t : b, 2)} m`;
}

// Tabela de fatos; `aoRemover(f)` opcional mostra um × nos fatos locais.
function tabelaFatos(fatos, aoRemover) {
  const t = el("table", "tabela fatos");
  const cab = el("tr");
  for (const h of ["Tipo", "Nome / valor", "Profundidade", "Fonte", ""]) cab.appendChild(el("th", "", h));
  t.appendChild(cab);
  for (const f of fatos) {
    const tr = el("tr");
    const valor = [f.nome, f.valor && `${f.valor}${f.unidade ? " " + f.unidade : ""}`].filter(Boolean).join(" · ");
    const fonte = f.pagina ? `pág. ${f.pagina}` : (f.fonte_rel || f.fonte_caminho ? "documento" : "—");
    const tdFonte = el("td", "", fonte);
    tdFonte.title = [f.fonte_rel || f.fonte_caminho, f.autor && `por ${f.autor}`, ORIGEM_FATO[f.origem]].filter(Boolean).join("\n");
    const tdAcao = el("td");
    if (aoRemover && f.origem === "local") {
      const x = el("button", "x", "×");
      x.title = "Apagar este dado";
      x.onclick = () => aoRemover(f);
      tdAcao.appendChild(x);
    } else if (f.origem !== "local") {
      tdAcao.appendChild(el("span", "selo", ORIGEM_FATO[f.origem]));
    }
    tr.append(el("td", "", TIPOS_FATO[f.tipo] || f.tipo), el("td", "", valor || f.observacao || "—"),
              el("td", "mono", profFato(f)), tdFonte, tdAcao);
    t.appendChild(tr);
  }
  return t;
}
