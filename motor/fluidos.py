"""Propriedades de fluido (grau API do óleo, densidade relativa do gás) a partir dos documentos
das pastas de poço do REATE — para a viabilidade não depender de digitar esses números.

Níveis, do mais confiável ao menos:

0. **Análise PVT de laboratório** lida da planilha do poço (0.39, `motor/pvt.py`): grau API do
   tanque, densidade do gás da liberação diferencial e a tabela Bo, Rs, Bg × pressão — a
   viabilidade interpola na pressão do reservatório no lugar das correlações.
1. **Dados transcritos** (tipo de fato `propriedade_fluido`): o usuário desenhou a caixa na
   página, conferiu o número e salvou — com documento, página e caixa como fonte. É o que a
   viabilidade usa primeiro (mediana, se houver mais de um).
2. **Leitura automática**: o texto das páginas (embutido ou OCR) dos poços do campo é varrido
   à procura de "32,5 °API", "Grau API: 28", "densidade do gás 0,65"… Cada leitura vem com o
   poço, o arquivo, a página e o trecho. Sem dado transcrito, a viabilidade usa a mediana
   dessas leituras e avisa que vieram de leitura automática (o OCR erra números).
3. **Páginas que citam** API, densidade do gás, análise de óleo/gás… mas sem número legível
   (formulários manuscritos, por exemplo): a lista leva à página para transcrever.

Leituras descartadas pelo usuário ficam guardadas no campo e não voltam.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from statistics import median

from . import producao as mpr
from .banco import Banco
from .pocos import canonico

TIPO_FATO = "propriedade_fluido"
GRANDEZAS = {
    "api": {"rotulo": "Grau API do óleo", "unidade": "°API", "faixa": (5.0, 70.0)},
    "densidade_gas": {"rotulo": "Densidade relativa do gás", "unidade": "ar = 1", "faixa": (0.55, 1.8)},
}
NOMES_SUGERIDOS = ["Grau API do óleo", "Densidade relativa do gás", "RGO (razão gás-óleo)",
                   "Bo (fator volume-formação do óleo)", "Viscosidade do óleo", "BSW"]

_NUM = r"(\d{1,2}(?:[.,]\d{1,3})?)"
# texto já sem acento e em minúsculas
_PADROES = [
    ("api", re.compile(r"(?<![\d/.,])" + _NUM + r"\s*(?:°|º|o|graus?)?\s*a\.?\s?p\.?\s?i\b(?!\s*[-\d]?\s*\d+[a-z])")),
    ("api", re.compile(r"\b(?:grau|graus|densidade|gravidade|api gravity|grav\.?)\s*(?:a\.?p\.?i\.?)\s*(?:do oleo)?"
                       r"\s*[:=]?\s*" + _NUM + r"(?![\d.,]*\s*(?:m|pol|%))")),
    ("api", re.compile(r"\bapi\s*[:=]\s*" + _NUM + r"\b")),
    ("api", re.compile(r"\bapi\s*gravity\s*[:=]?\s*" + _NUM + r"\b")),
    ("densidade_gas", re.compile(r"\b(?:densidade|dens\.?|d\.?)\s*(?:relativa|rel\.?)?\s*(?:do\s*)?gas"
                                 r"(?:\s*\(?\s*ar\s*=\s*1\s*\)?)?\s*[:=]?\s*((?:0|1)[.,]\d{2,4})")),
    ("densidade_gas", re.compile(r"\b(?:gravidade|grav\.?)\s*(?:especifica|esp\.?)\s*(?:do\s*)?gas\s*[:=]?\s*"
                                 r"((?:0|1)[.,]\d{2,4})")),
    ("densidade_gas", re.compile(r"\bgas\s*(?:specific\s*)?gravity\s*[:=]?\s*((?:0|1)[.,]\d{2,4})")),
]
_PAGINA_CITA = re.compile(r"\bapi\b|grau api|densidade (?:relativa )?do gas|dens\.?\s*\(?cntp|gravidade especifica"
                          r"|analise (?:de|do) (?:oleo|gas|fluido)|cromatografia|pvt\b")


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn").lower()


def numero(t: str) -> float | None:
    try:
        return float(t.replace(",", "."))
    except (TypeError, ValueError):
        return None


def ler_valores(texto: str) -> list[dict]:
    """Valores de API e densidade do gás num texto, com a posição e o trecho."""
    t = " ".join(sem_acento(texto).split())
    vistos, out = set(), []
    for grandeza, rx in _PADROES:
        lo, hi = GRANDEZAS[grandeza]["faixa"]
        for m in rx.finditer(t):
            v = numero(m.group(1))
            if v is None or not lo <= v <= hi:
                continue
            chave = (grandeza, m.start(1))
            if chave in vistos:
                continue
            vistos.add(chave)
            ini, fim = max(0, m.start() - 60), min(len(t), m.end() + 60)
            out.append({"grandeza": grandeza, "valor": v, "trecho": ("…" if ini else "") + t[ini:fim]
                        + ("…" if fim < len(t) else ""), "lido": m.group(0)})
    return out


def classificar(nome: str) -> str | None:
    """Que grandeza um dado transcrito representa, pelo nome."""
    n = sem_acento(nome)
    if "api" in n:
        return "api"
    if "gas" in n and ("dens" in n or "gravidade" in n or "gravity" in n):
        return "densidade_gas"
    return None


def pocos_do_campo(banco: Banco, campo: str) -> dict[str, str]:
    """{nome canônico: id no cadastro} dos poços do campo."""
    alvo = mpr.chave_campo(campo)
    with banco.conexao() as c:
        rows = c.execute("SELECT id, nome_anp, campo FROM pocos WHERE campo IS NOT NULL").fetchall()
    out = {}
    for r in rows:
        if mpr.chave_campo(r["campo"] or "") == alvo:
            nome = canonico(r["nome_anp"] or r["id"]) or canonico(r["id"]) or r["id"]
            out[nome] = r["id"]
    return out


def chave_leitura(x: dict) -> str:
    return f"{x['doc']}|{x['pagina']}|{x['grandeza']}|{x['valor']:g}"


def varrer_indice(caminho_indice: str, pocos: set[str]) -> tuple[list[dict], list[dict]]:
    """(leituras, páginas que citam sem número) no índice de texto, só dos poços pedidos."""
    if not pocos:
        return [], []
    con = sqlite3.connect(caminho_indice, timeout=30)
    try:
        tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
        tabela = "paginas" if "paginas" in tabelas else "paginas_simples" if "paginas_simples" in tabelas else None
        if tabela is None:
            return [], []
        nomes = [r[0] for r in con.execute(f"SELECT DISTINCT poco FROM {tabela}")]
        meus = [n for n in nomes if (canonico(n) or n) in pocos]
        if not meus:
            return [], []
        marcas = ",".join("?" * len(meus))
        rows = con.execute(f"SELECT doc, bacia, poco, arquivo, pagina, metodo, texto, original FROM {tabela} "
                           f"WHERE poco IN ({marcas})", meus).fetchall()
    finally:
        con.close()
    leituras, citam = [], []
    for doc, bacia, poco, arquivo, pagina, metodo, texto, original in rows:
        base = {"doc": doc, "bacia": bacia, "poco": canonico(poco) or poco, "arquivo": arquivo,
                "pagina": int(pagina), "metodo": metodo}
        achados = {}
        for t in (texto or "", original or ""):
            for v in ler_valores(t):
                achados.setdefault((v["grandeza"], v["valor"]), v)
        for v in achados.values():
            leituras.append({**base, **v})
        if not achados:
            ts = sem_acento(texto or original or "")
            m = _PAGINA_CITA.search(" ".join(ts.split()))
            if m:
                t1 = " ".join(ts.split())
                ini, fim = max(0, m.start() - 60), min(len(t1), m.end() + 60)
                citam.append({**base, "termo": m.group(0), "trecho": ("…" if ini else "") + t1[ini:fim] + "…"})
    leituras.sort(key=lambda x: (x["grandeza"], x["poco"], x["arquivo"], x["pagina"]))
    citam.sort(key=lambda x: (x["poco"], x["arquivo"], x["pagina"]))
    return leituras, citam


def fatos_fluido(banco: Banco, ids_pocos: list[str]) -> list[dict]:
    """Dados transcritos do tipo propriedade_fluido dos poços (com a grandeza reconhecida)."""
    out = []
    for pid in ids_pocos:
        for f in banco.fatos(pid):
            if f.get("tipo") != TIPO_FATO:
                continue
            g = classificar(f.get("nome") or "")
            v = numero(str(f.get("valor") or ""))
            out.append({**f, "grandeza": g, "valor_num": v})
    return out


def _br(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def _fonte_fato(f: dict) -> str:
    arq = (f.get("fonte_rel") or "").split("/")[-1]
    pag = f" p. {f['pagina']}" if f.get("pagina") else ""
    return f"{f.get('poco_id')}{' (' + arq + pag + ')' if arq else ''} = {f.get('valor')}"


def medidos(banco: Banco, ids_pocos: list[str]) -> list[dict]:
    """Análises PVT de laboratório (liberação diferencial) lidas nos poços do campo (0.39)."""
    import json
    from . import dados_poco as mdp
    saida = []
    for pid in ids_pocos:
        for i in mdp.itens_do_poco(banco, pid, "pvt"):
            with banco.conexao() as c:
                r = c.execute("SELECT dados FROM leituras WHERE rel = ?", (i["rel"],)).fetchone()
            d = json.loads(r[0]) if r and r[0] else {}
            x = i["extra"]
            intervalo = f"{_br(i['prof_topo'])}–{_br(i['prof_base'])} m" if i["prof_topo"] is not None else ""
            saida.append({"poco": pid, "rel": i["rel"], "intervalo": intervalo, "api": x.get("api_tanque"),
                          "densidade_gas": x.get("dg_lib_dif") or x.get("dg_tanque"), "rgo": x.get("rgo_tanque"),
                          "temp_c": x.get("temp_c"), "saturacao": x.get("saturacao") or {},
                          "tabela": d.get("tabela") or [],
                          "fonte": f"PVT do poço {pid} (liberação diferencial{', ' + intervalo if intervalo else ''})"})
    return saida


def escolher(fatos: list[dict], leituras: list[dict], descartadas: set[str], medidas: list[dict] | None = None) -> dict:
    """Para cada grandeza: o valor a usar e a fonte (PVT de laboratório > dados transcritos > leitura automática)."""
    out = {}
    medidas = medidas or []
    if medidas:
        melhor = max(medidas, key=lambda m: len(m["tabela"]))
        out["pvt"] = {**melhor, "origem": "medido",
                      "outros": [m["fonte"] for m in medidas if m is not melhor]}
    for g, info in GRANDEZAS.items():
        lo, hi = info["faixa"]
        ms = [m for m in medidas if m.get(g) is not None and lo <= m[g] <= hi]
        if ms:
            v = float(median(m[g] for m in ms))
            out[g] = {"valor": v, "origem": "medido", "n": len(ms),
                      "fonte": "análise PVT de laboratório: " + "; ".join(f"{m['fonte']} = {_br(m[g])}" for m in ms[:6])}
            continue
        fs = [f for f in fatos if f["grandeza"] == g and f["valor_num"] is not None and lo <= f["valor_num"] <= hi]
        if fs:
            v = float(median(f["valor_num"] for f in fs))
            out[g] = {"valor": v, "origem": "transcrito", "n": len(fs),
                      "fonte": (f"dado transcrito ({len(fs)}; mediana): " if len(fs) > 1 else "dado transcrito: ")
                      + "; ".join(_fonte_fato(f) for f in fs[:6])}
            continue
        ls = [x for x in leituras if x["grandeza"] == g and chave_leitura(x) not in descartadas]
        if ls:
            v = float(median(x["valor"] for x in ls))
            ocr = sum(1 for x in ls if x["metodo"] != "embutido")
            out[g] = {"valor": v, "origem": "leitura", "n": len(ls), "ocr": ocr,
                      "fonte": f"lido automaticamente nos documentos ({len(ls)} leitura(s){', ' + str(ocr) + ' por OCR' if ocr else ''}"
                               f"{'; mediana' if len(ls) > 1 else ''}): "
                               + "; ".join(f"{x['poco']} ({x['arquivo']} p. {x['pagina']}) = {_br(x['valor'])}" for x in ls[:6])
                               + " — confira na página"}
    return out


def resumo(banco: Banco, caminho_indice: str | None, campo: str, documentos: list[dict] | None = None) -> dict:
    """Tudo o que os documentos dos poços do campo dizem sobre API e densidade do gás."""
    pocos = pocos_do_campo(banco, campo)
    ficha = mpr.campo_guardado(banco, campo) or {}
    descartadas = set(ficha.get("fluidos_descartados") or [])
    leituras, citam = varrer_indice(caminho_indice, set(pocos)) if caminho_indice else ([], [])
    fatos = fatos_fluido(banco, list(pocos.values()))
    med = medidos(banco, sorted(set(pocos.values())))
    docs = [d for d in (documentos or []) if (canonico(d.get("poco") or "") or d.get("poco")) in pocos]
    for x in leituras:
        x["chave"] = chave_leitura(x)
        x["descartada"] = x["chave"] in descartadas
    return {"campo": campo, "pocos": sorted(pocos), "n_pocos": len(pocos),
            "documentos": {"total": len(docs), "processados": sum(1 for d in docs if d.get("situacao") == "processado"),
                           "pendentes": [d["rel"] for d in docs if d.get("situacao") != "processado"]},
            "leituras": leituras, "paginas": citam[:60], "n_paginas": len(citam),
            "fatos": [{k: f.get(k) for k in ("id", "poco_id", "nome", "valor", "unidade", "fonte_rel", "pagina",
                                              "origem", "grandeza")} for f in fatos],
            "medidos": [{k: v for k, v in m.items() if k != "tabela"} for m in med],
            "escolha": escolher(fatos, leituras, descartadas, med)}
