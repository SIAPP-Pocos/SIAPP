"""Geoquímica (bloco 9, item 7): isótopos de carbono dos gases e, quando houver, geoquímica de rocha.

Pasta "Dados De Rochas e Fluidos/GEOQUIMICADEFLUIDO" do REATE: uma planilha (no 1-BRSA-1304-BA, "XML
Spreadsheet 2003" do Excel, `.xml`) e uma nota técnica em PDF. A planilha traz, por amostra, o intervalo e o
δ¹³C do metano, do etano e do propano (‰ VPDB).

Leitura dos isótopos (indício, não prova — Schoell, 1983; Whiticar, 1999):

- δ¹³C₁ mais pesado que −50 ‰: gás **termogênico**; mais leve que −60 ‰: **biogênico**; entre os dois, misto
  ou de transição;
- δ¹³C₁ < δ¹³C₂ < δ¹³C₃ é a ordem normal; inversão (rollover) aponta mistura ou gás muito maturo.

δ¹³C de hidrocarboneto é **negativo**. Um valor positivo vindo de uma fórmula com sinal duplo (ex.: "=--47.39",
caso real do 1-BRSA-1304-BA, em que a nota técnica dá −47,39) é corrigido para negativo, com aviso; positivo sem
essa evidência fica como está, com aviso.

Geoquímica de rocha (COT, S1, S2, S3, Tmax, IH, IO, Ro) é reconhecida pelo título das colunas, se a planilha
existir; ainda não foi conferida num arquivo real do acervo.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET

VERSAO = 1
NOME = "Geoquímica (isótopos de gás, geoquímica de rocha)"
DOCUMENTOS = {"geoquimica": "Geoquímica — análises de laboratório"}
PRIORIDADE = {"geoquimica": 0}

NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}


class ErroGeoquimica(ValueError):
    pass


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return " ".join(s.upper().replace("\n", " ").split())


def reconhece(rel: str) -> bool:
    r = _norm(str(rel or "").replace("\\", "/"))
    if not r.endswith((".XML", ".XLS", ".XLSX")):
        return False
    return "GEOQUIMICA" in r or "D13C" in r.rsplit("/", 1)[-1] or "ISOTOP" in r


def _br(v: float) -> str:
    return f"{v:.2f}".replace(".", ",").replace("-", "−")


def numero(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace("−", "-").replace(" ", "")
    if not t or t in ("-", "--"):
        return None
    t = re.sub(r"^--", "-", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


# ---------------------------------------------------------------- planilha XML 2003 (SpreadsheetML)
def linhas_spreadsheetml(caminho: str) -> list[list[dict]]:
    """Todas as linhas de todas as abas: cada célula {texto, formula}. Respeita ss:Index (células puladas)."""
    try:
        raiz = ET.parse(caminho).getroot()
    except ET.ParseError as e:
        raise ErroGeoquimica(f"XML ilegível: {e}") from e
    if not raiz.tag.endswith("Workbook"):
        raise ErroGeoquimica("Não é uma planilha do Excel (XML Spreadsheet 2003).")
    saida = []
    for ws in raiz.findall("ss:Worksheet", NS):
        for row in ws.iter("{urn:schemas-microsoft-com:office:spreadsheet}Row"):
            ln, col = [], 0
            for cell in row.findall("ss:Cell", NS):
                idx = cell.get("{urn:schemas-microsoft-com:office:spreadsheet}Index")
                if idx:
                    while col < int(idx) - 1:
                        ln.append({"texto": "", "formula": None})
                        col += 1
                dado = cell.find("ss:Data", NS)
                texto = "".join(dado.itertext()).strip() if dado is not None else ""
                ln.append({"texto": texto, "formula": cell.get("{urn:schemas-microsoft-com:office:spreadsheet}Formula")})
                col += 1
            saida.append(ln)
        saida.append([])          # separa as abas
    return saida


def _linhas(caminho: str) -> list[list[dict]]:
    c = caminho.lower()
    if c.endswith(".xml"):
        return linhas_spreadsheetml(caminho)
    if c.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        try:
            return [[{"texto": "" if v is None else str(v), "formula": None} for v in r]
                    for ws in wb.worksheets for r in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
    import xlrd
    try:
        b = xlrd.open_workbook(caminho)
    except Exception as e:  # noqa: BLE001
        raise ErroGeoquimica(f"Planilha ilegível: {e}") from e
    return [[{"texto": "" if v in (None, "") else str(v), "formula": None} for v in s.row_values(r)]
            for s in b.sheets() for r in range(s.nrows)]


# ---------------------------------------------------------------- tabelas
# rocha: título da coluna, sem a unidade entre parênteses
COL_ROCHA = {"COT": "cot", "TOC": "cot", "C ORG": "cot", "S1": "s1", "S2": "s2", "S3": "s3", "TMAX": "tmax",
             "IH": "ih", "HI": "ih", "IO": "io", "OI": "io", "RO": "ro", "%RO": "ro"}


def _prof(t: str) -> tuple[float | None, float | None]:
    """'1680/1684' → (1680, 1684); '1.682,5' → (1682,5, None)."""
    t = str(t or "").strip()
    # profundidade em pt-BR com separador de milhar ("1.200", "1.682,5"): o ponto não é decimal
    def p(x):
        return numero(x.replace(".", "")) if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", x.strip()) else numero(x)
    m = re.match(r"^\s*([\d.,]+)\s*[/\-–a]\s*([\d.,]+)\s*$", t)
    if m:
        return p(m[1]), p(m[2])
    return p(t), None


def _colunas_isotopos(cab: list[str]) -> dict[str, int]:
    """'d13C Metano (‰)' → C1; etano → C2; propano → C3 (o "13C" tem de estar no título)."""
    mapa = {}
    for i, t in enumerate(cab):
        n = _norm(t)
        if "13C" not in n.replace(" ", ""):
            continue
        for chave, gas in (("C1", "METANO"), ("C2", "ETANO"), ("C3", "PROPANO")):
            achou = gas in n and not (gas == "ETANO" and "METANO" in n)
            if (achou or re.search(rf"13C\s*{chave}\b", n)) and chave not in mapa:
                mapa[chave] = i
    return mapa


def _colunas_rocha(cab: list[str]) -> dict[str, int]:
    mapa = {}
    for i, t in enumerate(cab):
        n = _norm(t).split("(")[0].strip()
        k = COL_ROCHA.get(n)
        if k and k not in mapa:
            mapa[k] = i
    return mapa


def _col_prof(cab: list[str]) -> int | None:
    return next((i for i, t in enumerate(cab) if _norm(t).startswith(("PROF", "INTERVALO", "TOPO"))), None)


def _col_poco(cab: list[str]) -> int | None:
    return next((i for i, t in enumerate(cab) if _norm(t).startswith("POCO")), None)


def leitura_isotopos(c1, c2, c3) -> str | None:
    if c1 is None:
        return None
    if c1 > -50:
        origem = "termogênico"
    elif c1 < -60:
        origem = "biogênico"
    else:
        origem = "misto ou de transição"
    ordem = ""
    if c2 is not None and c3 is not None:
        ordem = "; ordem normal (C1 < C2 < C3)" if c1 < c2 < c3 else "; ordem invertida (rollover: mistura ou gás maturo)"
    return f"gás {origem}{ordem}"


def ler_linhas(linhas: list[list[dict]]) -> dict:
    isotopos, rocha, avisos, info = [], [], [], {}
    i = 0
    while i < len(linhas):
        cab = [c["texto"] for c in linhas[i]]
        iso = _colunas_isotopos(cab)
        roc = _colunas_rocha(cab) if not iso else {}
        cp, cpo = _col_prof(cab), _col_poco(cab)
        # tabela de informações da amostra (Poço ANP, Registro, Poço, Prof., Tipo, Bacia)
        if cpo is not None and any(_norm(t).startswith("TIPO DE AMOSTRA") for t in cab) and i + 1 < len(linhas):
            dados = [c["texto"] for c in linhas[i + 1]]
            for k, t in enumerate(cab):
                n = _norm(t)
                if k < len(dados) and dados[k]:
                    if n == "POCO ANP":
                        info["poco"] = dados[k]
                    elif n == "POCO":
                        info["poco_operador"] = dados[k]
                    elif n.startswith("TIPO DE AMOSTRA"):
                        info["tipo_amostra"] = dados[k]
                    elif n.startswith("BACIA"):
                        info["bacia"] = dados[k]
                    elif n.startswith("REGISTRO"):
                        info["registro"] = dados[k]
        if (iso or len(roc) >= 2) and cp is not None:
            j = i + 1
            while j < len(linhas) and linhas[j] and any(c["texto"] for c in linhas[j]):
                ln = linhas[j]
                txt = lambda k: ln[k]["texto"] if k is not None and k < len(ln) else ""   # noqa: E731
                topo, base = _prof(txt(cp))
                if topo is None:
                    break
                if iso:
                    vals = {}
                    for chave, k in iso.items():
                        v = numero(txt(k))
                        f = (ln[k]["formula"] or "") if k < len(ln) else ""
                        if v is not None and v > 0:
                            if "--" in f or txt(k).startswith("--"):
                                avisos.append(f"δ¹³C {chave} positivo na planilha ({f or txt(k)}), com sinal duplo: "
                                              f"usado {_br(-v)} ‰ (δ¹³C de hidrocarboneto é negativo).")
                                v = -v
                            else:
                                avisos.append(f"δ¹³C {chave} = {_br(v)} ‰ é positivo — confira na nota técnica.")
                        vals[chave] = v
                    isotopos.append({"topo": topo, "base": base, "poco": txt(cpo) or None, **vals,
                                     "leitura": leitura_isotopos(vals.get("C1"), vals.get("C2"), vals.get("C3"))})
                else:
                    rocha.append({"topo": topo, "base": base, **{k: numero(txt(c)) for k, c in roc.items()}})
                j += 1
            i = j
            continue
        i += 1
    if not isotopos and not rocha:
        raise ErroGeoquimica("Não achei tabela de isótopos (δ¹³C metano/etano/propano) nem de geoquímica de rocha.")
    return {"documento": "geoquimica", "titulo": DOCUMENTOS["geoquimica"], "isotopos": isotopos, "rocha": rocha,
            "amostra": info, "avisos": avisos, "gerais": {"poco": info.get("poco")},
            "apelidos": [info["poco_operador"]] if info.get("poco_operador") else []}


def ler(caminho: str) -> dict:
    return ler_linhas(_linhas(caminho))


def apelidos(dados: dict) -> list[str]:
    return dados.get("apelidos") or []


def itens(dados: dict) -> list[dict]:
    saida = []
    for x in dados.get("isotopos", []):
        saida.append({"tipo": "isotopo_gas", "nome": x.get("leitura"), "prof_topo": x["topo"], "prof_base": x["base"],
                      "valor": x.get("C1"), "unidade": "‰ (δ¹³C metano)",
                      "texto": (dados.get("amostra") or {}).get("tipo_amostra"),
                      "extra": {k: x.get(k) for k in ("C1", "C2", "C3")}})
    for x in dados.get("rocha", []):
        saida.append({"tipo": "geoquimica_rocha", "nome": None, "prof_topo": x["topo"], "prof_base": x["base"],
                      "valor": x.get("cot"), "unidade": "% COT", "texto": None,
                      "extra": {k: x.get(k) for k in ("s1", "s2", "s3", "tmax", "ih", "io", "ro")}})
    return saida
