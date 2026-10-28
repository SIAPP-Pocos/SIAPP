"""Produção de petróleo e gás de um campo, pelos dados abertos da ANP (fora do REATE).

Três fontes, todas públicas no gov.br:

- **produção por poço**, mês a mês (óleo, condensado, gás associado e não associado, água,
  e as injeções: água, gás, CO₂, N₂, vapor, polímeros), de 1941 até ~2 meses atrás.
  Terra e mar em arquivos separados, cada arquivo com o país inteiro de um período (ano,
  semestre ou trimestre, 2–7 MB). O SIAPP baixa os períodos pedidos, guarda uma cópia
  compactada (.csv.gz) para os próximos campos e fica só com as linhas do campo;
- **produção por zona** (zona produtora = reservatório, ex. "AÇU0250 FSP-2"), mensal, de
  10/2014 em diante; vem em vazão média (m³/d) e o SIAPP grava o volume do mês (× dias);
- **sumário executivo do Plano de Desenvolvimento** do campo (PDF de 1–3 páginas): volume
  in place e produção acumulada numa data (do BAR), poços perfurados/produtores/injetores,
  reservatórios, mecanismo de produção. E a ficha e o polígono do campo (vértices).

A consulta nova da ANP (CDP, 2024 em diante) pede captcha: o SIAPP não a usa — a série
nacional por poço já vai até o trimestre mais recente.

Unidades gravadas: óleo, condensado e água em m³; gás em mil m³ ("Mm³" da ANP); vapor em t.
Este módulo só **traz e guarda** os dados; contas sobre eles (depleção etc.) ficam para depois.
"""

from __future__ import annotations

import calendar
import csv
import gzip
import io
import json
import os
import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import urljoin

from .banco import Banco, agora

BASE_ANP = "https://www.gov.br/anp/pt-br/"
PAGINA_PRODUCAO = BASE_ANP + "centrais-de-conteudo/dados-abertos/fase-de-desenvolvimento-e-producao"
PAGINA_PD = BASE_ANP + "assuntos/exploracao-e-producao-de-oleo-e-gas/desenvolvimento-e-producao/planos-de-desenvolvimento"
URL_CAMPOS = (BASE_ANP + "centrais-de-conteudo/dados-abertos/arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
              "informacoes-sobre-campos/extracao-campo.csv")
URL_VERTICES = (BASE_ANP + "centrais-de-conteudo/dados-abertos/arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
                "informacoes-sobre-campos/extracao-vertices.csv")
AGENTE = {"User-Agent": "SIAPP (pesquisa academica, UFAL)"}
PASTA_CACHE = os.path.join("fontes", "anp", "producao")

# colunas da produção por poço (nome no cabeçalho, sem acento/colchete → nome no SIAPP)
COLUNAS_POCO = {
    "ano": "ano", "mes/ano": "mes_ano", "estado": "estado", "bacia": "bacia", "campo": "campo",
    "poco": "poco", "ambiente": "ambiente", "instalacao": "instalacao",
    "producao de oleo (m3)": "oleo_m3", "producao de condensado (m3)": "condensado_m3",
    "producao de gas associado (mm3)": "gas_assoc_mil_m3", "producao de gas nao associado (mm3)": "gas_nassoc_mil_m3",
    "producao de agua (m3)": "agua_m3", "injecao de gas (mm3)": "inj_gas_mil_m3",
    "injecao de agua para recuperacao secundaria (m3)": "inj_agua_rec_m3",
    "injecao de agua para descarte (m3)": "inj_agua_desc_m3", "injecao de gas carbonico (mm3)": "inj_co2_mil_m3",
    "injecao de nitrogenio (mm3)": "inj_n2_mil_m3", "injecao de vapor de agua (t)": "inj_vapor_t",
    "injecao de polimeros (m3)": "inj_polimeros_m3", "injecao de outros fluidos (m3)": "inj_outros_m3",
}
VOLUMES_POCO = ["oleo_m3", "condensado_m3", "gas_assoc_mil_m3", "gas_nassoc_mil_m3", "agua_m3", "inj_gas_mil_m3",
                "inj_agua_rec_m3", "inj_agua_desc_m3", "inj_co2_mil_m3", "inj_n2_mil_m3", "inj_vapor_t",
                "inj_polimeros_m3", "inj_outros_m3"]
# produção por zona: vazões diárias → volume do mês
COLUNAS_ZONA = {
    "zona": "zona", "nome poco anp": "poco", "campo": "campo", "bacia": "bacia", "ambiente": "ambiente", "data": "data",
    "oleo (m3/d)": "oleo_m3", "condensado (m3/d)": "condensado_m3", "gas associado (mil m3/d)": "gas_assoc_mil_m3",
    "gas nao associado (mil m3/d)": "gas_nassoc_mil_m3", "agua (m3/d)": "agua_m3",
    "agua injetada para descarte (m3/d)": "inj_agua_desc_m3", "agua injetada para rec. secundaria (m3/d)": "inj_agua_rec_m3",
    "vapor injetado (t/d)": "inj_vapor_t", "gas injetado (mil m3/d)": "inj_gas_mil_m3",
    "co2 injetado (mil m3/d)": "inj_co2_mil_m3", "n2 injetado (mil m3/d)": "inj_n2_mil_m3",
    "outros fluidos injetados (m3/d)": "inj_outros_m3",
}
VOLUMES_ZONA = ["oleo_m3", "condensado_m3", "gas_assoc_mil_m3", "gas_nassoc_mil_m3", "agua_m3", "inj_agua_desc_m3",
                "inj_agua_rec_m3", "inj_vapor_t", "inj_gas_mil_m3", "inj_co2_mil_m3", "inj_n2_mil_m3", "inj_outros_m3"]
ZONA_DESDE = 2014


class ErroProducao(ValueError):
    """Falha ao obter ou ler os dados de produção, com mensagem para o usuário."""


class Cancelado(Exception):
    pass


# ====================================================================== textos
def sem_acento(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in t if not unicodedata.combining(c))


def chave_campo(nome: str) -> str:
    """GUAMARÉ, Guamaré, guamare → GUAMARE (para casar o campo entre as fontes)."""
    return re.sub(r"[^A-Z0-9]+", " ", sem_acento(nome).upper()).strip()


def _cab(nome: str) -> str:
    n = sem_acento(nome.replace("﻿", "")).strip().strip("[]").strip().lower()
    return re.sub(r"\s+", " ", n.replace("³", "3"))


def numero(v) -> float | None:
    """'2.619,83' → 2619.83; '0,000' → 0; ',0035' → 0.0035; '' → None."""
    if v is None:
        return None
    s = str(v).strip().replace(" ", "")
    if not s or s in {"-", "*"}:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def decodificar(dados: bytes) -> str:
    if dados[:3] == b"\xef\xbb\xbf":
        return dados[3:].decode("utf-8", errors="replace")
    try:
        return dados.decode("utf-8")
    except UnicodeDecodeError:
        return dados.decode("cp1252", errors="replace")


# ====================================================================== índices (páginas da ANP)
class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = None
        self._texto: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._texto = []

    def handle_data(self, data):
        if self._href is not None:
            self._texto.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._texto).split()), self._href))
            self._href = None


def links(html: str, base: str = BASE_ANP) -> list[tuple[str, str]]:
    p = _Links()
    p.feed(html)
    return [(t, urljoin(base, h)) for t, h in p.links]


def _anos(url: str) -> tuple[int, int] | None:
    """Anos cobertos por um arquivo, pelo nome (ou pela pasta, se o nome não tem ano)."""
    partes = url.rstrip("/").split("/")
    nome = partes[-1]
    anos = [int(a) for a in re.findall(r"(?<!\d)(19[4-9]\d|20[0-4]\d)(?!\d)", nome)]
    if not anos:
        anos = [int(a) for a in re.findall(r"(?<!\d)(19[4-9]\d|20[0-4]\d)(?!\d)", partes[-2])]
    return (min(anos), max(anos)) if anos else None


def arquivos_producao(html: str) -> list[dict]:
    """Os CSVs da página "Fase de Desenvolvimento e Produção": produção por poço (terra e mar)
    e por zona, com o período coberto por cada um."""
    out, vistos = [], set()
    for texto, url in links(html, PAGINA_PRODUCAO):
        u = url.split("?")[0]
        if not u.lower().endswith(".csv") or u in vistos:
            continue
        if "/pt/" in u or "/pm/" in u:
            a = _anos(u)
            if not a:
                continue
            out.append({"tipo": "poco", "ambiente": "terra" if "/pt/" in u else "mar", "url": u,
                        "ano_ini": a[0], "ano_fim": a[1], "rotulo": texto})
        elif "producao-por-zona/" in u:
            m = re.search(r"(\d{2})[-_]?(\d{4})\.csv$", u.split("/")[-1])
            if not m:
                continue
            out.append({"tipo": "zona", "ambiente": "", "url": u, "ano_ini": int(m.group(2)),
                        "ano_fim": int(m.group(2)), "mes": int(m.group(1)), "rotulo": texto})
        else:
            continue
        vistos.add(u)
    return out


def escolher(arquivos: list[dict], tipo: str, ambiente: str, ano_ini: int, ano_fim: int) -> list[dict]:
    sel = [a for a in arquivos if a["tipo"] == tipo and (tipo == "zona" or a["ambiente"] == ambiente)
           and a["ano_fim"] >= ano_ini and a["ano_ini"] <= ano_fim]
    return sorted(sel, key=lambda a: (a["ano_ini"], a.get("mes", 0), a["url"]))


def url_pd(html: str, campo: str) -> str | None:
    """O PDF do sumário executivo do PD do campo, pela lista da página de Planos de Desenvolvimento."""
    alvo = chave_campo(campo)
    for texto, url in links(html, PAGINA_PD):
        if "/pd/" in url and url.lower().endswith(".pdf") and chave_campo(texto) == alvo:
            return url
    for texto, url in links(html, PAGINA_PD):           # pelo nome do arquivo (guamare_sudeste.pdf)
        if "/pd/" in url and url.lower().endswith(".pdf"):
            arq = chave_campo(url.rsplit("/", 1)[-1][:-4].replace("_", " ").replace("-", " "))
            if arq == alvo:
                return url
    return None


# ====================================================================== leitores
def _linhas_csv(texto: str):
    return csv.reader(io.StringIO(texto))


def ler_producao_poco(dados: bytes, campo: str | None = None) -> list[dict]:
    """Linhas da produção por poço (todas, ou só de um campo), com volumes do mês."""
    leitor = _linhas_csv(decodificar(dados))
    cab = None
    for linha in leitor:
        if linha and _cab(linha[0]) == "ano":
            cab = [COLUNAS_POCO.get(_cab(c)) for c in linha]
            break
    if cab is None:
        raise ErroProducao("Arquivo de produção por poço sem o cabeçalho esperado (Ano, Mês/Ano, …).")
    alvo = chave_campo(campo) if campo else None
    i_campo = cab.index("campo")
    out = []
    for linha in leitor:
        if len(linha) <= i_campo or (alvo and chave_campo(linha[i_campo]) != alvo):
            continue
        r = {k: v for k, v in zip(cab, linha) if k}
        m = re.match(r"(\d{1,2})/(\d{4})", r.get("mes_ano", ""))
        if not m:
            continue
        reg = {"periodo": f"{m.group(2)}-{int(m.group(1)):02d}", "campo": r.get("campo", "").strip(),
               "poco": r.get("poco", "").strip(), "instalacao": (r.get("instalacao") or "").strip(),
               "bacia": r.get("bacia", "").strip(), "estado": r.get("estado", "").strip(),
               "ambiente": (r.get("ambiente") or "").strip().upper()}
        for k in VOLUMES_POCO:
            reg[k] = numero(r.get(k))
        out.append(reg)
    return out


def ler_producao_zona(dados: bytes, campo: str | None = None) -> list[dict]:
    """Produção por zona: vazão média do mês × dias do mês = volume do mês."""
    leitor = _linhas_csv(decodificar(dados))
    cab = None
    for linha in leitor:
        if linha and _cab(linha[0]) == "zona":
            cab = [COLUNAS_ZONA.get(_cab(c)) for c in linha]
            break
    if cab is None:
        raise ErroProducao("Arquivo de produção por zona sem o cabeçalho esperado (Zona, Nome poço ANP, …).")
    alvo = chave_campo(campo) if campo else None
    i_campo = cab.index("campo")
    out = []
    for linha in leitor:
        if len(linha) <= i_campo or (alvo and chave_campo(linha[i_campo]) != alvo):
            continue
        r = {k: v for k, v in zip(cab, linha) if k}
        m = re.match(r"\d{1,2}/(\d{1,2})/(\d{4})", r.get("data", ""))
        if not m:
            continue
        ano, mes = int(m.group(2)), int(m.group(1))
        dias = calendar.monthrange(ano, mes)[1]
        reg = {"periodo": f"{ano}-{mes:02d}", "campo": r.get("campo", "").strip(), "zona": r.get("zona", "").strip(),
               "poco": r.get("poco", "").strip(), "dias": dias}
        for k in VOLUMES_ZONA:
            v = numero(r.get(k))
            reg[k] = None if v is None else round(v * dias, 4)
        out.append(reg)
    return out


def ler_campos(dados: bytes) -> list[dict]:
    """A ficha dos campos da ANP (extracao-campo.csv)."""
    linhas = list(csv.DictReader(io.StringIO(decodificar(dados))))
    out = []
    for r in linhas:
        r = {_cab(k): (v or "").strip() for k, v in r.items() if k}
        if not r.get("campo"):
            continue
        out.append({"chave": chave_campo(r["campo"]), "nome": r["campo"], "codigo": r.get("codigo_campo"),
                    "sigla": r.get("sigla_campo"), "bacia": r.get("bacia"), "estado": r.get("estado"),
                    "operador": r.get("operador"), "ambiente": r.get("ambiente"), "rodada": r.get("rodada"),
                    "contrato": r.get("numero_contrato"), "situacao": r.get("situacao_campo"),
                    "inicio_producao": r.get("data_inicio_producao"), "termino_producao": r.get("data_termino_producao"),
                    "termino_fase": r.get("termino_fase")})
    return out


def _dms(v: str) -> float | None:
    """'-05:10:38,902' → -5.17747…"""
    m = re.match(r"\s*(-?)(\d+):(\d+):(\d+(?:[.,]\d+)?)", v or "")
    if not m:
        return numero(v)
    g = int(m.group(2)) + int(m.group(3)) / 60 + float(m.group(4).replace(",", ".")) / 3600
    return -g if m.group(1) else g


def ler_vertices(dados: bytes, campo: str) -> list[list[float]]:
    """Polígono da área do campo na fase de produção: [[lat, lon], …] na ordem dos vértices."""
    alvo = chave_campo(campo)
    pts = []
    for r in csv.DictReader(io.StringIO(decodificar(dados))):
        r = {_cab(k): (v or "").strip() for k, v in r.items() if k}
        if chave_campo(r.get("campo", "")) != alvo:
            continue
        lat, lon = _dms(r.get("latitude")), _dms(r.get("longitude"))
        if lat is not None and lon is not None:
            pts.append((int(numero(r.get("num_vertice")) or 0), round(lat, 7), round(lon, 7)))
    return [[a, b] for _, a, b in sorted(pts)]


# ---------------------------------------------------------------- sumário do PD (PDF)
_RE_NUM = r"(-?\d[\d.]*(?:,\d+)?)"


def _valor(linhas: list[str], rotulo: str, ini: int = 0, fim: int | None = None) -> str | None:
    """O valor de "Rótulo:" — na mesma linha ou na próxima não vazia (o leiaute do PD)."""
    fim = len(linhas) if fim is None else fim
    padrao = re.compile(r"^\s*" + rotulo + r"\s*:?\s*(.*)$", re.I)
    for i in range(ini, fim):
        m = padrao.match(linhas[i])
        if m:
            resto = m.group(1).strip()
            if resto:
                return resto
            for j in range(i + 1, min(i + 3, len(linhas))):
                if linhas[j].strip():
                    return linhas[j].strip()
    return None


def _num_bloco(linhas: list[str], ini: int, fim: int, rotulo: str) -> float | None:
    v = _valor(linhas, rotulo, ini, fim)
    if not v:
        return None
    m = re.search(_RE_NUM, v.replace(" ", ""))
    return numero(m.group(1)) if m else None


def ler_pd(dados: bytes) -> dict:
    """O sumário executivo do Plano de Desenvolvimento (PDF): o que o SIAPP consegue ler com
    segurança; o texto inteiro fica junto para conferir."""
    import fitz
    with fitz.open(stream=dados, filetype="pdf") as doc:
        texto = "\n".join(p.get_text() for p in doc)
    linhas = [re.sub(r"\s+", " ", l).strip() for l in texto.splitlines()]
    linhas = [l for l in linhas if l]
    out: dict = {"texto": "\n".join(linhas)}
    if linhas:
        m = re.match(r"(.+?)\s+((?:19|20)\d{2})$", linhas[0])
        out["titulo"], out["ano"] = (m.group(1), int(m.group(2))) if m else (linhas[0], None)
    m = re.search(r"Resolu[cç][aã]o[^\n]*?n[ºo°]\s*([\d./]+)", texto, re.I)
    out["resolucao"] = m.group(1).rstrip(".,") if m else None
    for chave, rot in (("contrato", r"N[ºo°] do Contrato"), ("operador", r"Operador do Contrato"),
                       ("estado", r"Estado"), ("bacia", r"Bacia"), ("fluido", r"Fluido Principal"),
                       ("situacao", r"Situa[cç][aã]o"), ("descoberta", r"Descoberta"),
                       ("inicio_producao", r"In[ií]cio de Produ[cç][aã]o"),
                       ("termino_producao", r"(?:Previs[aã]o do )?T[eé]rmino d[ae] Produ[cç][aã]o")):
        out[chave] = _valor(linhas, rot)
    area = _valor(linhas, r"[ÁA]rea")
    m = re.search(_RE_NUM, (area or "").replace(" ", ""))
    out["area_km2"] = numero(m.group(1)) if m else None
    # reservatórios e produção: o parágrafo depois do rótulo, até a próxima seção
    for chave, rot in (("reservatorios", r"Geologia da [áa]rea e Reservat[óo]rios"),
                       ("sistema_producao", r"Sistema de Produ[cç][aã]o e Escoamento")):
        m = re.search(rot + r"\s*:\s*(.+?)(?=\n(?:N[úu]mero de Po[cç]os|Geologia|Volume|Fonte|Po[cç]os:|"
                            r"Concession|Localiza[cç][aã]o:)|\Z)", out["texto"], re.I | re.S)
        out[chave] = " ".join(m.group(1).split()) if m else None
    # poços
    i = next((k for k, l in enumerate(linhas) if re.match(r"^Po[cç]os\s*:", l, re.I)), None)
    if i is not None:
        out["pocos"] = {"data": _valor(linhas, r"Po[cç]os", i, i + 3),
                        "perfurados": _num_bloco(linhas, i, i + 12, r"Perfurados"),
                        "produtores": _num_bloco(linhas, i, i + 12, r"Produtores"),
                        "injetores": _num_bloco(linhas, i, i + 12, r"Injetores")}
    # volumes: "Volume in place" e "Produção Acumulada", cada um com a data e as linhas de fluido
    i_vip = next((k for k, l in enumerate(linhas) if re.search(r"in place", l, re.I)), None)
    i_acu = next((k for k, l in enumerate(linhas) if re.match(r"^Produ[cç][aã]o Acumulada", l, re.I)), None)
    fluidos = (("oleo_milhoes_m3", r"[ÓO]leo\s*\(milh[õo]es de m[³3]\s*\)"),
               ("condensado_milhoes_m3", r"Condensado\s*\(milh[õo]es de m[³3]\s*\)"),
               ("gas_total_milhoes_m3", r"G[áa]s Total\s*\(milh[õo]es de m[³3]\s*\)"),
               ("gas_associado_milhoes_m3", r"G[áa]s Associado\s*\(milh[õo]es de m[³3]\s*\)"),
               ("gas_nao_associado_milhoes_m3", r"G[áa]s N[ãa]o Associado\s*\(milh[õo]es de m[³3]\s*\)"))

    def bloco(ini, fim):
        if ini is None:
            return None
        d = {"data": None}
        m = re.search(r"(\d{2}/\d{2}/\d{4})", " ".join(linhas[ini:ini + 3]))
        if m:
            d["data"] = m.group(1)
        for k, rot in fluidos:
            v = _num_bloco(linhas, ini, fim, rot)
            if v is not None:
                d[k] = v
        return d
    if i_vip is not None:
        out["in_place"] = bloco(i_vip, i_acu if i_acu and i_acu > i_vip else min(len(linhas), i_vip + 12))
    if i_acu is not None:
        out["acumulada"] = bloco(i_acu, min(len(linhas), i_acu + 12))
    m = re.search(r"Fonte\s*:\s*([^\n]+)", out["texto"])
    out["fonte"] = m.group(1).strip() if m else None
    return out


# ====================================================================== banco do projeto
def guardar_poco(banco: Banco, campo: str, linhas: list[dict], arquivo: str) -> int:
    from .pocos import canonico
    chave = chave_campo(campo)
    cols = ["campo", "poco_anp", "poco_id", "periodo", "instalacao", *VOLUMES_POCO, "arquivo"]
    with banco.conexao() as c:
        c.executemany(
            f"INSERT OR REPLACE INTO producao_poco ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [(chave, r["poco"], canonico(r["poco"]) or r["poco"], r["periodo"], r["instalacao"],
              *[r[k] for k in VOLUMES_POCO], arquivo) for r in linhas])
    return len(linhas)


def guardar_zona(banco: Banco, campo: str, linhas: list[dict], arquivo: str) -> int:
    from .pocos import canonico
    chave = chave_campo(campo)
    cols = ["campo", "zona", "poco_anp", "poco_id", "periodo", *VOLUMES_ZONA, "arquivo"]
    with banco.conexao() as c:
        c.executemany(
            f"INSERT OR REPLACE INTO producao_zona ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [(chave, r["zona"], r["poco"], canonico(r["poco"]) or r["poco"], r["periodo"],
              *[r[k] for k in VOLUMES_ZONA], arquivo) for r in linhas])
    return len(linhas)


def guardar_campo(banco: Banco, campo: str, **dados) -> dict:
    chave = chave_campo(campo)
    with banco.conexao() as c:
        r = c.execute("SELECT dados FROM campos_anp WHERE chave = ?", (chave,)).fetchone()
        atual = json.loads(r["dados"]) if r else {}
        atual.update({k: v for k, v in dados.items() if v is not None})
        atual.setdefault("nome", campo)
        c.execute("INSERT OR REPLACE INTO campos_anp (chave, nome, dados, atualizado_em) VALUES (?, ?, ?, ?)",
                  (chave, atual.get("nome") or campo, json.dumps(atual, ensure_ascii=False), agora()))
    return atual


def campo_guardado(banco: Banco, campo: str) -> dict | None:
    with banco.conexao() as c:
        r = c.execute("SELECT dados FROM campos_anp WHERE chave = ?", (chave_campo(campo),)).fetchone()
    return json.loads(r["dados"]) if r else None


def resumo(banco: Banco, campo: str) -> dict:
    """O que está guardado do campo: período, poços, totais por ano e no período, o último mês
    e os números do PD — sem contas sobre eles."""
    chave = chave_campo(campo)
    soma = ", ".join(f"SUM({k}) AS {k}" for k in VOLUMES_POCO)
    with banco.conexao() as c:
        g = c.execute(f"SELECT MIN(periodo) AS de, MAX(periodo) AS ate, COUNT(DISTINCT poco_anp) AS pocos, "
                      f"COUNT(*) AS linhas, {soma} FROM producao_poco WHERE campo = ?", (chave,)).fetchone()
        anos = [dict(r) for r in c.execute(
            f"SELECT substr(periodo, 1, 4) AS ano, COUNT(DISTINCT poco_anp) AS pocos, {soma} "
            f"FROM producao_poco WHERE campo = ? GROUP BY ano ORDER BY ano", (chave,))]
        ultimo = c.execute(
            f"SELECT periodo, COUNT(DISTINCT CASE WHEN COALESCE(oleo_m3, 0) + COALESCE(gas_assoc_mil_m3, 0) + "
            f"COALESCE(gas_nassoc_mil_m3, 0) + COALESCE(condensado_m3, 0) > 0 THEN poco_anp END) AS produtores, "
            f"COUNT(DISTINCT CASE WHEN COALESCE(inj_agua_rec_m3, 0) + COALESCE(inj_agua_desc_m3, 0) + "
            f"COALESCE(inj_gas_mil_m3, 0) + COALESCE(inj_co2_mil_m3, 0) + COALESCE(inj_vapor_t, 0) > 0 "
            f"THEN poco_anp END) AS injetores, {soma} FROM producao_poco WHERE campo = ? "
            f"GROUP BY periodo ORDER BY periodo DESC LIMIT 1", (chave,)).fetchone()
        z = c.execute("SELECT MIN(periodo) AS de, MAX(periodo) AS ate, COUNT(DISTINCT zona) AS zonas, "
                      "COUNT(*) AS linhas FROM producao_zona WHERE campo = ?", (chave,)).fetchone()
        zonas = [dict(r) for r in c.execute(
            "SELECT zona, COUNT(DISTINCT poco_anp) AS pocos, SUM(oleo_m3) AS oleo_m3, "
            "SUM(COALESCE(gas_assoc_mil_m3, 0) + COALESCE(gas_nassoc_mil_m3, 0)) AS gas_mil_m3, SUM(agua_m3) AS agua_m3 "
            "FROM producao_zona WHERE campo = ? GROUP BY zona ORDER BY oleo_m3 DESC", (chave,))]
    return {"campo": campo, "chave": chave, "poco": dict(g) if g and g["linhas"] else None, "anos": anos,
            "ultimo_mes": dict(ultimo) if ultimo else None,
            "zona": dict(z) if z and z["linhas"] else None, "zonas": zonas, "ficha": campo_guardado(banco, campo)}


def do_poco(banco: Banco, poco_id: str, campo: str | None = None) -> dict:
    """Produção e injeção de um poço (ficha do Mapa), com os dados abertos da ANP já baixados:
    série mensal (somando as instalações), acumulados, primeiro e último mês com produção e
    as zonas. `situacao`: "ok" | "campo_sem_poco" (o campo foi baixado, o poço não aparece) |
    "campo_nao_baixado" | "sem_campo"."""
    soma = ", ".join(f"SUM({k}) AS {k}" for k in VOLUMES_POCO)
    with banco.conexao() as c:
        meses = [dict(r) for r in c.execute(
            f"SELECT periodo, {soma} FROM producao_poco WHERE poco_id = ? GROUP BY periodo ORDER BY periodo",
            (poco_id,))]
        campos = [r[0] for r in c.execute("SELECT DISTINCT campo FROM producao_poco WHERE poco_id = ?", (poco_id,))]
        zonas = [dict(r) for r in c.execute(
            "SELECT zona, MIN(periodo) AS de, MAX(periodo) AS ate, SUM(oleo_m3) AS oleo_m3, "
            "SUM(COALESCE(gas_assoc_mil_m3, 0) + COALESCE(gas_nassoc_mil_m3, 0)) AS gas_mil_m3, SUM(agua_m3) AS agua_m3 "
            "FROM producao_zona WHERE poco_id = ? GROUP BY zona ORDER BY oleo_m3 DESC", (poco_id,))]
    if not meses:
        if not campo:
            situacao = "sem_campo"
        else:
            situacao = "campo_sem_poco" if campo_guardado(banco, campo) or _tem_producao(banco, campo) else "campo_nao_baixado"
        return {"situacao": situacao, "campo": campo or "", "meses": [], "zonas": zonas}

    def total(k):
        v = [m[k] for m in meses if m[k] is not None]
        return round(sum(v), 3) if v else None
    prod = [m for m in meses if (m["oleo_m3"] or 0) + (m["condensado_m3"] or 0) + (m["gas_assoc_mil_m3"] or 0)
            + (m["gas_nassoc_mil_m3"] or 0) > 0]
    inj = [m for m in meses if any((m[k] or 0) > 0 for k in VOLUMES_POCO if k.startswith("inj_"))]
    acum = {k: total(k) for k in VOLUMES_POCO}
    gas = sum(v for v in (acum["gas_assoc_mil_m3"], acum["gas_nassoc_mil_m3"]) if v) or None
    return {"situacao": "ok", "campo": campo or (campos[0] if campos else ""), "campos": campos,
            "de": meses[0]["periodo"], "ate": meses[-1]["periodo"], "n_meses": len(meses),
            "primeira_producao": prod[0]["periodo"] if prod else None,
            "ultima_producao": prod[-1]["periodo"] if prod else None,
            "injetor": bool(inj), "acumulado": {**acum, "gas_total_mil_m3": gas},
            "ultimo_mes": meses[-1], "meses": meses, "zonas": zonas}


def _tem_producao(banco: Banco, campo: str) -> bool:
    with banco.conexao() as c:
        return c.execute("SELECT 1 FROM producao_poco WHERE campo = ? LIMIT 1", (chave_campo(campo),)).fetchone() is not None


def linhas_csv(banco: Banco, campo: str) -> tuple[list[str], list[list]]:
    cols = ["poco_anp", "poco_id", "periodo", "instalacao", *VOLUMES_POCO, "arquivo"]
    with banco.conexao() as c:
        rows = [list(r) for r in c.execute(
            f"SELECT {', '.join(cols)} FROM producao_poco WHERE campo = ? ORDER BY periodo, poco_anp",
            (chave_campo(campo),))]
    return cols, rows


def linhas_csv_zona(banco: Banco, campo: str) -> tuple[list[str], list[list]]:
    cols = ["zona", "poco_anp", "poco_id", "periodo", *VOLUMES_ZONA, "arquivo"]
    with banco.conexao() as c:
        rows = [list(r) for r in c.execute(
            f"SELECT {', '.join(cols)} FROM producao_zona WHERE campo = ? ORDER BY periodo, zona, poco_anp",
            (chave_campo(campo),))]
    return cols, rows


# ====================================================================== download
class Baixador:
    """Baixa da ANP com cópia local compactada (um arquivo nacional serve para todos os campos)."""

    def __init__(self, pasta_projeto: str, sessao=None, progresso=None, cancelar=None, timeout: float = 120):
        import requests
        self.pasta = os.path.join(pasta_projeto, PASTA_CACHE)
        self.sessao = sessao or requests.Session()
        self.progresso = progresso or (lambda texto: None)
        self.cancelar = cancelar or (lambda: False)
        self.timeout = timeout
        self.baixados_bytes = 0

    def _checar(self):
        if self.cancelar():
            raise Cancelado()

    def texto(self, url: str) -> str:
        return decodificar(self.bytes(url, guardar=False))

    def bytes(self, url: str, guardar: bool = True, rotulo: str = "") -> bytes:
        """Conteúdo de `url` — da cópia local (.gz) se já baixado."""
        import requests
        nome = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("/arquivos/")[-1].split("/assuntos/")[-1])[-150:]
        cache = os.path.join(self.pasta, nome + ".gz")
        if guardar and os.path.exists(cache):
            with gzip.open(cache, "rb") as f:
                return f.read()
        self._checar()
        try:
            r = self.sessao.get(url, timeout=(30, self.timeout), headers=AGENTE, stream=True)
        except requests.exceptions.RequestException as e:
            raise ErroProducao(f"Sem conexão com a ANP ({type(e).__name__}). Tente de novo mais tarde.") from e
        if r.status_code != 200:
            raise ErroProducao(f"A ANP respondeu HTTP {r.status_code} para {url}")
        partes, n = [], 0
        for bloco in r.iter_content(1 << 16):
            self._checar()
            partes.append(bloco)
            n += len(bloco)
            if rotulo and n % (1 << 20) < (1 << 16):
                self.progresso(f"{rotulo} ({n / 1e6:.0f} MB)")
        dados = b"".join(partes)
        self.baixados_bytes += len(dados)
        if guardar:
            os.makedirs(self.pasta, exist_ok=True)
            tmp = cache + ".tmp"
            with gzip.open(tmp, "wb", compresslevel=6) as f:
                f.write(dados)
            os.replace(tmp, cache)
        return dados


def baixar(banco: Banco, pasta_projeto: str, campo: str, *, ano_ini: int | None = None, ano_fim: int | None = None,
           zona: bool = True, pd: bool = True, progresso=None, cancelar=None, sessao=None) -> dict:
    """Traz tudo do campo para o banco do projeto: ficha e polígono, PD, produção por poço no
    período e por zona. Volta o que foi feito (arquivos, linhas, avisos)."""
    prog = progresso or (lambda t: None)
    bx = Baixador(pasta_projeto, sessao=sessao, progresso=prog, cancelar=cancelar)
    avisos: list[str] = []
    feito = {"campo": campo, "arquivos": 0, "linhas_poco": 0, "linhas_zona": 0, "avisos": avisos}
    # ficha do campo (ambiente, início da produção) e polígono
    prog("Ficha dos campos da ANP…")
    fichas = {f["chave"]: f for f in ler_campos(bx.bytes(URL_CAMPOS, guardar=False))}
    ficha = fichas.get(chave_campo(campo))
    if not ficha:
        raise ErroProducao(f"O campo {campo} não está na lista de campos da ANP (extracao-campo.csv).")
    try:
        poligono = ler_vertices(bx.bytes(URL_VERTICES, guardar=False), campo)
    except ErroProducao as e:
        poligono = []
        avisos.append(f"Polígono do campo: {e}")
    guardar_campo(banco, campo, ficha=ficha, poligono=poligono or None, nome=ficha["nome"])
    ambiente = "mar" if (ficha.get("ambiente") or "").lower().startswith("mar") else "terra"
    m = re.search(r"(19|20)\d{2}", ficha.get("inicio_producao") or "")
    inicio = int(m.group(0)) if m else 1941
    from datetime import date
    hoje = date.today().year
    ano_ini = max(inicio, ano_ini or inicio)
    ano_fim = min(hoje, ano_fim or hoje)
    feito.update(ambiente=ambiente, ano_ini=ano_ini, ano_fim=ano_fim)
    # sumário do PD
    if pd:
        try:
            prog("Sumário do Plano de Desenvolvimento…")
            url = url_pd(bx.texto(PAGINA_PD), campo)
            if url:
                info = ler_pd(bx.bytes(url))
                info["url"] = url
                guardar_campo(banco, campo, pd=info)
                feito["pd"] = True
            else:
                avisos.append("Sem sumário do Plano de Desenvolvimento publicado para este campo.")
        except ErroProducao as e:
            avisos.append(f"Sumário do PD: {e}")
    # produção por poço e por zona
    prog("Lista de arquivos de produção da ANP…")
    arquivos = arquivos_producao(bx.texto(PAGINA_PRODUCAO))
    if not arquivos:
        raise ErroProducao("A página de dados abertos da ANP mudou: não achei os arquivos de produção.")
    fila = [("poco", a) for a in escolher(arquivos, "poco", ambiente, ano_ini, ano_fim)]
    if zona:
        fila += [("zona", a) for a in escolher(arquivos, "zona", "", max(ano_ini, ZONA_DESDE), ano_fim)]
    for k, (tipo, a) in enumerate(fila, 1):
        rot = f"Produção {'por zona' if tipo == 'zona' else 'por poço'} — arquivo {k} de {len(fila)} ({a['rotulo'] or a['ano_ini']})"
        prog(rot)
        try:
            dados = bx.bytes(a["url"], rotulo=rot)
        except ErroProducao as e:
            avisos.append(f"{a['url'].rsplit('/', 1)[-1]}: {e}")
            continue
        nome = a["url"].rsplit("/", 1)[-1]
        if tipo == "poco":
            linhas = [r for r in ler_producao_poco(dados, campo) if ano_ini <= int(r["periodo"][:4]) <= ano_fim]
            feito["linhas_poco"] += guardar_poco(banco, campo, linhas, nome)
        else:
            feito["linhas_zona"] += guardar_zona(banco, campo, ler_producao_zona(dados, campo), nome)
        feito["arquivos"] += 1
    feito["mb_baixados"] = round(bx.baixados_bytes / 1e6, 1)
    guardar_campo(banco, campo, baixado_em=agora(), periodo_pedido=[ano_ini, ano_fim])
    return feito
