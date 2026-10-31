"""Petrofísica básica de testemunho (bloco 9, 0.48): porosidade, permeabilidade e densidade de plugs e
raios gama do testemunho (COREGAMA).

Vêm da pasta `Dados de Rochas e Fluidos/PETROFISICA_BASICA` do REATE, em planilhas Excel:

- **plugs** (`<poço>-Petrofisica Basica.xls`, ou um nome numérico como `00610.119452.xls`): uma linha por
  amostra, com profundidade, porosidade (%), densidade, permeabilidade longitudinal (mD) e pressão (psi);
- **coregama** (`<poço>_COREGAMA.xls`): uma linha por profundidade analisada, com o gama (API) do testemunho.

Os valores de plugs chegam como **texto com vírgula decimal** ("2021,1"); o gama, como número. As colunas são
achadas pelo cabeçalho (a ordem e as colunas extras variam), e o que não é reconhecido fica em `extra.colunas`
com o nome original, sem perder nada.

Os mesmos plugs podem vir em duas planilhas (uma com a coluna "Data Análise", outra sem): na ficha ficam uma vez,
com a outra como "também em".

A planilha não declara a unidade da **densidade** (2,65 sugere densidade de grãos, em g/cm³, mas isso é leitura
nossa): ela é guardada como vem, sem unidade.
"""

from __future__ import annotations

import unicodedata

VERSAO = 1
NOME = "Petrofísica básica de testemunho (porosidade, permeabilidade, densidade e gama do testemunho)"
DOCUMENTOS = {"petrofisica_plugs": "Petrofísica básica — plugs (porosidade, permeabilidade, densidade)",
              "petrofisica_gama": "Gama do testemunho (COREGAMA)"}
PRIORIDADE = {"petrofisica_plugs": 0, "petrofisica_gama": 1}


class ErroPetrofisica(ValueError):
    """Planilha que não é de petrofísica básica ou não pôde ser lida."""


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return " ".join(s.upper().replace("\n", " ").replace("_", " ").replace(".", " ").split())


def tipo_pelo_nome(rel: str) -> str | None:
    bruto = str(rel or "").replace("\\", "/")
    if not bruto.lower().endswith((".xls", ".xlsx")):
        return None
    r = _norm(bruto)
    nome = _norm(bruto.rsplit("/", 1)[-1])
    if "PETROFISICA BASICA" not in r:
        return None
    return "petrofisica_gama" if "COREGAMA" in nome else "petrofisica_plugs"


def reconhece(rel: str) -> bool:
    return tipo_pelo_nome(rel) is not None


def _num(v) -> float | None:
    """Número de célula: float do Excel ou texto com vírgula decimal ("206,39"; "1.234,5")."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip()
    if t in ("", "-"):
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _texto(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).strip()
    return t or None


# O que cada cabeçalho (normalizado, sem acento) significa. Vale o primeiro que casar.
_CAMPOS = (
    ("data", ("DATA ANALISE", "DATA")),
    ("unidade", ("UNIDADE",)),
    ("poco_petrobras", ("POCO PETROBRAS", "POCO OPERADORA")),
    ("poco_anp", ("POCO ANP",)),
    ("tipo_amostra", ("TIPO AMOSTRA",)),
    ("direcao", ("DIR AMOSTRA", "DIRECAO")),
    ("numero", ("NR AMOSTRA", "NUMERO AMOSTRA", "N AMOSTRA")),
    ("prof", ("PROFUNDIDADE", "PROF")),
    ("porosidade", ("POROSIDADE",)),
    ("densidade", ("DENSIDADE",)),
    ("permeabilidade", ("PERMEABILIDADE LONG", "PERMEABILIDADE")),
    ("pressao", ("PRESSAO",)),
)


def _mapa_colunas(cabecalho: list) -> dict[str, int]:
    mapa: dict[str, int] = {}
    for j, h in enumerate(cabecalho):
        n = _norm(h)
        if not n:
            continue
        for campo, inicios in _CAMPOS:
            if campo not in mapa and any(n.startswith(i) for i in inicios):
                mapa[campo] = j
                break
    return mapa


def ler_plugs_linhas(linhas: list[list]) -> dict:
    """Plugs a partir das linhas da planilha (a primeira com "Profundidade" é o cabeçalho)."""
    ini = next((k for k, ln in enumerate(linhas) if any(_norm(c).startswith("PROFUNDIDADE") for c in ln)), None)
    if ini is None:
        raise ErroPetrofisica("Não achei a coluna Profundidade: não parece planilha de petrofísica básica.")
    cab = linhas[ini]
    mapa = _mapa_colunas(cab)
    if "prof" not in mapa or not ({"porosidade", "permeabilidade"} & set(mapa)):
        raise ErroPetrofisica("A planilha não tem porosidade nem permeabilidade ao lado da profundidade.")
    usadas = set(mapa.values())
    amostras, poco, poco_op = [], None, None
    for ln in linhas[ini + 1:]:
        def cel(campo):
            j = mapa.get(campo)
            return ln[j] if j is not None and j < len(ln) else None
        prof = _num(cel("prof"))
        if prof is None:
            continue
        poco = poco or _texto(cel("poco_anp"))
        poco_op = poco_op or _texto(cel("poco_petrobras"))
        outras = {_texto(cab[j]): _texto(v) for j, v in enumerate(ln)
                  if j not in usadas and j < len(cab) and _texto(cab[j]) and _texto(v) is not None}
        amostras.append({
            "prof": prof, "porosidade": _num(cel("porosidade")), "permeabilidade": _num(cel("permeabilidade")),
            "densidade": _num(cel("densidade")), "pressao": _num(cel("pressao")),
            "tipo": _texto(cel("tipo_amostra")), "direcao": _texto(cel("direcao")), "numero": _texto(cel("numero")),
            "unidade_operadora": _texto(cel("unidade")), "data": _texto(cel("data")), "colunas": outras})
    if not amostras:
        raise ErroPetrofisica("A planilha não tem nenhuma amostra com profundidade.")
    return {"documento": "petrofisica_plugs", "titulo": DOCUMENTOS["petrofisica_plugs"],
            "gerais": {"poco": poco}, "poco_operadora": poco_op, "apelidos": [], "amostras": amostras,
            "colunas_lidas": sorted(mapa)}


def ler_gama_linhas(linhas: list[list]) -> dict:
    """Gama do testemunho a partir das linhas (cabeçalho: POCO_ANP, TEST, TOPO, BASE, PROF_ANALISADA, RAIOS_GAMA_API)."""
    ini = next((k for k, ln in enumerate(linhas) if any("RAIOS GAMA" in _norm(c) for c in ln)), None)
    if ini is None:
        raise ErroPetrofisica("Não achei a coluna de raios gama: não parece planilha COREGAMA.")
    cab = [_norm(c) for c in linhas[ini]]

    def achar(*nomes):
        return next((j for j, h in enumerate(cab) if any(h == n or h.startswith(n) for n in nomes)), None)
    j_poco, j_test, j_topo, j_base = achar("POCO ANP", "POCO"), achar("TEST"), achar("TOPO"), achar("BASE")
    j_prof, j_gr = achar("PROF ANALISADA", "PROFUNDIDADE"), achar("RAIOS GAMA")
    if j_prof is None:
        raise ErroPetrofisica("A planilha COREGAMA não tem a profundidade analisada.")
    pontos, poco = [], None
    for ln in linhas[ini + 1:]:
        def cel(j):
            return ln[j] if j is not None and j < len(ln) else None
        prof, gr = _num(cel(j_prof)), _num(cel(j_gr))
        if prof is None or gr is None:
            continue
        poco = poco or _texto(cel(j_poco))
        t = _num(cel(j_test))
        pontos.append({"prof": prof, "gr": gr, "testemunho": int(t) if t is not None and t.is_integer() else _texto(cel(j_test)),
                       "topo": _num(cel(j_topo)), "base": _num(cel(j_base))})
    if not pontos:
        raise ErroPetrofisica("A planilha COREGAMA não tem nenhum ponto de gama.")
    return {"documento": "petrofisica_gama", "titulo": DOCUMENTOS["petrofisica_gama"], "gerais": {"poco": poco},
            "apelidos": [], "pontos": pontos}


def _linhas(caminho: str) -> list[list]:
    if caminho.lower().endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        try:
            return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        finally:
            wb.close()
    import xlrd
    try:
        b = xlrd.open_workbook(caminho)
    except Exception as e:  # noqa: BLE001
        raise ErroPetrofisica(f"Planilha ilegível: {e}") from e
    sh = b.sheets()[0]
    return [sh.row_values(r) for r in range(sh.nrows)]


def ler(caminho: str) -> dict:
    tipo = tipo_pelo_nome(caminho)
    if tipo is None:
        raise ErroPetrofisica("Não é uma planilha de petrofísica básica (pasta PETROFISICA_BASICA).")
    linhas = _linhas(caminho)
    return ler_gama_linhas(linhas) if tipo == "petrofisica_gama" else ler_plugs_linhas(linhas)


def apelidos(dados: dict) -> list[str]:
    return []


def itens(dados: dict) -> list[dict]:
    saida = []
    if dados["documento"] == "petrofisica_plugs":
        for a in dados["amostras"]:
            nome = " ".join(x for x in (a.get("numero"), a.get("direcao")) if x) or None
            saida.append({"tipo": "plug_testemunho", "nome": nome, "prof_topo": a["prof"], "valor": a["porosidade"],
                          "unidade": "% (porosidade)", "texto": a.get("tipo"),
                          "extra": {k: a.get(k) for k in ("permeabilidade", "densidade", "pressao", "direcao", "numero",
                                                          "unidade_operadora", "data", "colunas")}})
        return saida
    for p in dados["pontos"]:
        saida.append({"tipo": "gama_testemunho", "nome": None if p["testemunho"] is None else str(p["testemunho"]),
                      "prof_topo": p["prof"], "valor": p["gr"], "unidade": "API",
                      "extra": {"testemunho": p["testemunho"], "topo": p["topo"], "base": p["base"]}})
    return saida


def resumo_plugs(amostras: list[dict]) -> dict:
    """Faixas simples dos plugs (mínimo, máximo e quantas amostras têm o dado), sem estatística inventada."""
    def faixa(chave):
        v = [a[chave] for a in amostras if a.get(chave) is not None]
        return {"n": len(v), "min": min(v), "max": max(v)} if v else {"n": 0, "min": None, "max": None}
    return {"n": len(amostras), "porosidade": faixa("porosidade"), "permeabilidade": faixa("permeabilidade"),
            "densidade": faixa("densidade")}
