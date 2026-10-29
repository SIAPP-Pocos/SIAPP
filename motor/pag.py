"""Perfil de Acompanhamento Geológico — PAG (bloco 9, item 4): curvas de lama e gás e descrição de calha.

Pasta "Perfil de Acompanhamento Geologico" do REATE:

- `<poço>_PAG_curvas.las`: a cada metro, dados de perfuração (peso sobre broca, torque, rotação, taxa
  de penetração), da lama (densidade em lb/gal, viscosidade, salinidade, pH) e do **gás** (gás total e a
  cromatografia C1–C5, CO₂, H₂S, em ppm). O arquivo abre na aba Perfis (as famílias de curva novas
  estão em recursos/mnemonicos.json); este leitor tira dele as **zonas de gás** e a **salinidade**;
- `<poço>_PAG_DAC.xls`: a **descrição das amostras de calha** feita pelo geólogo de poço: a cada
  amostra (9 m ou 3 m), as rochas e a porcentagem de cada uma, cor, textura, composição, porosidade
  aparente, **fluorescência e corte**, observações e a **formação geológica**.

Zona de gás: trecho em que o gás total passa de 3 × o nível de fundo (mediana do poço), com pelo menos 2 m.
Com a cromatografia, cada zona ganha as razões de Haworth (1985): umidade Wh = (C2+C3+C4+C5)/(C1…C5)·100,
equilíbrio Bh = (C1+C2)/(C3+C4+C5) e caráter Ch = (C4+C5)/C3, com a leitura usual: Wh < 0,5 gás muito
seco; 0,5–17,5 gás (mais úmido quanto maior); 17,5–40 óleo; > 40 óleo residual/pesado; Bh > Wh indica
gás, Bh < Wh óleo. É indício, não prova — a confirmação vem do perfil e do teste.

Na descrição de calha, os códigos de rocha seguem a convenção da Petrobras (ARN arenito, FLH folhelho,
SLT siltito…); código que o SIAPP não conhece fica como está.
"""

from __future__ import annotations

import unicodedata

import numpy as np

VERSAO = 1
NOME = "Perfil de Acompanhamento Geológico (curvas de lama e gás, descrição de calha)"
DOCUMENTOS = {"pag_curvas": "PAG — curvas de lama e gás", "pag_dac": "PAG — descrição das amostras de calha"}
PRIORIDADE = {"pag_dac": 0, "pag_curvas": 1}

ROCHAS = {
    "ARN": "ARENITO", "FLH": "FOLHELHO", "SLT": "SILTITO", "ARG": "ARGILITO", "CLU": "CALCILUTITO",
    "CRE": "CALCARENITO", "CRU": "CALCIRRUDITO", "CAL": "CALCÁRIO", "MRG": "MARGA", "CGL": "CONGLOMERADO",
    "DOL": "DOLOMITO", "ANI": "ANIDRITA", "HAL": "HALITA", "GIP": "GIPSITA", "CRV": "CARVÃO", "LGN": "LINHITO",
    "DIA": "DIABÁSIO", "BAS": "BASALTO", "GRT": "GRANITO", "GNS": "GNAISSE", "COQ": "COQUINA", "SIL": "SÍLEX",
}


class ErroPAG(ValueError):
    pass


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return " ".join(s.upper().replace("\n", " ").split())


def tipo_pelo_nome(rel: str) -> str | None:
    r = _norm(str(rel or "").replace("\\", "/"))
    nome = r.rsplit("/", 1)[-1]
    na_pasta = "PERFIL DE ACOMPANHAMENTO GEOLOGICO" in r
    if nome.endswith((".XLS", ".XLSX")) and ("DAC" in nome or (na_pasta and "PAG" in nome)):
        return "pag_dac"
    if nome.endswith(".LAS") and ("PAG" in nome or na_pasta):
        return "pag_curvas"
    return None


def reconhece(rel: str) -> bool:
    return tipo_pelo_nome(rel) is not None


def _num(v) -> float | None:
    if v is None or (isinstance(v, str) and v.strip() in ("", "-")):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(".", "").replace(",", ".") if "," in str(v) else str(v).strip())
    except ValueError:
        return None


# ---------------------------------------------------------------- curvas (LAS)
def _curva(quadro: dict, *mnems) -> np.ndarray | None:
    for m in mnems:
        for k, c in quadro["curvas"].items():
            if k.upper() == m and c["valores"] is not None and np.isfinite(c["valores"]).any():
                return c["valores"]
    return None


def zonas_gas(prof, gas, croma: dict | None = None, *, fator: float = 3.0, minimo_m: float = 2.0) -> dict:
    """Trechos com gás total acima de `fator` × o fundo (mediana), com as razões de Haworth."""
    prof, gas = np.asarray(prof, float), np.asarray(gas, float)
    ok = np.isfinite(gas) & (gas > 0)
    if ok.sum() < 10:
        return {"fundo": None, "zonas": []}
    fundo = float(np.median(gas[ok]))
    acima = ok & (gas > fator * fundo)
    zonas, i, n = [], 0, len(prof)
    while i < n:
        if not acima[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and (acima[j + 1] or (j + 2 < n and acima[j + 2])):   # tolera um ponto abaixo
            j += 1
        topo, base = float(prof[i]), float(prof[j])
        if base - topo >= minimo_m:
            sel = slice(i, j + 1)
            z = {"topo": topo, "base": base, "gas_max": float(np.nanmax(gas[sel])),
                 "gas_medio": float(np.nanmean(gas[sel])), "vezes_fundo": round(float(np.nanmax(gas[sel])) / fundo, 1)}
            if croma:
                cs = {k: float(np.nanmean(v[sel])) for k, v in croma.items() if v is not None and np.isfinite(v[sel]).any()}
                z.update(razoes_haworth(cs))
            zonas.append(z)
        i = j + 1
    return {"fundo": fundo, "zonas": zonas}


def razoes_haworth(c: dict) -> dict:
    c1, c2, c3, c4, c5 = (c.get(k) for k in ("C1", "C2", "C3", "C4", "C5"))
    if None in (c1, c2, c3) or c1 <= 0:
        return {}
    c4, c5 = c4 or 0.0, c5 or 0.0
    soma = c1 + c2 + c3 + c4 + c5
    wh = 100 * (c2 + c3 + c4 + c5) / soma if soma else None
    bh = (c1 + c2) / (c3 + c4 + c5) if (c3 + c4 + c5) else None
    ch = (c4 + c5) / c3 if c3 else None
    if wh is None:
        leitura = None
    elif wh < 0.5:
        leitura = "gás muito seco"
    elif wh < 17.5:
        leitura = "gás" + (" (Bh > Wh)" if bh is not None and bh > wh else "")
    elif wh < 40:
        leitura = "óleo" + (" (Bh < Wh)" if bh is not None and bh < wh else "")
    else:
        leitura = "óleo residual ou pesado"
    return {"wh": round(wh, 2) if wh is not None else None, "bh": round(bh, 2) if bh is not None else None,
            "ch": round(ch, 3) if ch is not None else None, "haworth": leitura,
            "c1_c2": round(c1 / c2, 1) if c2 else None, "c1_c3": round(c1 / c3, 1) if c3 else None}


def rw_salinidade(ppm_nacl: float, temp_f: float = 75.0) -> float | None:
    """Resistividade de uma solução de NaCl: Bateman & Konen (1977) a 75 °F e Arps para outra temperatura."""
    if not ppm_nacl or ppm_nacl <= 0:
        return None
    r75 = 0.0123 + 3647.5 / ppm_nacl ** 0.955
    return round(r75 * (75 + 6.77) / (temp_f + 6.77), 4)


def ler_curvas(caminho: str) -> dict:
    from . import perfis as mpf
    try:
        quadros, cab = mpf.ler(caminho)
    except mpf.ErroPerfil as e:
        raise ErroPAG(str(e)) from e
    if not quadros:
        raise ErroPAG("LAS sem curvas.")
    q = max(quadros, key=lambda x: len(x["prof"]))
    prof = q["prof"]
    gas = _curva(q, "HYDC", "TGAS", "GASTOT", "GT", "TG")
    croma = {k: _curva(q, *ms) for k, ms in (("C1", ("METH", "C1G", "C1GAS")), ("C2", ("ETH", "C2G")),
                                              ("C3", ("PRP", "PROP", "C3G")),
                                              ("C4", ("BUT", "C4G", "NC4")), ("C5", ("PEN", "C5G", "NC5")))}
    croma = {k: v for k, v in croma.items() if v is not None}
    zonas = zonas_gas(prof, gas, croma or None) if gas is not None else {"fundo": None, "zonas": []}
    sal = _curva(q, "SAL", "SALI", "MSAL")
    salinidade = []
    if sal is not None:
        for z, s in zip(prof, sal):
            if np.isfinite(s) and s > 0:
                salinidade.append({"prof": float(z), "ppm": float(s), "rw75": rw_salinidade(float(s))})
    peso = _curva(q, "DENS", "MW", "MDEN", "MUDW")
    lama = None
    if peso is not None and np.isfinite(peso).any():
        lama = {"peso_min_lb_gal": round(float(np.nanmin(peso)), 2), "peso_max_lb_gal": round(float(np.nanmax(peso)), 2)}
    disponiveis = sorted(k for k, c in q["curvas"].items() if c["valores"] is not None and np.isfinite(c["valores"]).any())
    return {"documento": "pag_curvas", "titulo": DOCUMENTOS["pag_curvas"], "topo": q["topo_m"], "base": q["base_m"],
            "curvas_com_dados": disponiveis, "cromatografia": sorted(croma), "gas": zonas, "salinidade": salinidade,
            "lama": lama, "gerais": {"poco": cab.get("poco") or None}, "apelidos": []}


# ---------------------------------------------------------------- descrição de calha (DAC)
COL_DAC = [("PROF", "prof"), ("TIPO DE ROCHA", "rocha"), ("PERC. NA AMOSTRA", "pct"), ("CORTE", "corte"), ("COR", "cor"),
           ("TONALIDADE", "tonalidade"), ("TEXTURA", "granulometria"), ("COMPOSICAO", "composicao"),
           ("ESTR", "estrutura"), ("MATRIZ", "matriz"), ("POR", "porosidade"), ("COESAO", "coesao"),
           ("MODO", "modo"), ("FLUOREC", "fluor_tipo"), ("FLUORESC", "fluor_tipo"), ("CORTE", "corte"),
           ("DESCRICOES", "descricao"), ("FORMACAO", "formacao")]
# segunda linha do cabeçalho, debaixo de TEXTURA/COMPOSIÇÃO/FLUORESCÊNCIA/CORTE/MODO
SUB_DAC = {"GRAN": "granulometria", "ARRED": "arredondamento", "SEL": "selecao", "PRINC": "composicao",
           "ACESS": "acessorios", "MTZ": "matriz", "CMT": "cimento", "(APAR)": "porosidade", "MCH": "mancha",
           "IMP": "impregnacao", "ODR": "odor", "TIPO": "fluor_tipo", "PERC. (%)": "fluor_pct", "COR": "fluor_cor",
           "TON": "fluor_ton", "VELOC": "corte_velocidade", "MD. DISSEM.": "corte_modo"}


def _colunas_dac(cab1: list, cab2: list) -> dict[int, str]:
    mapa = {}
    for i, t in enumerate(cab1):
        n = _norm(t)
        k = next((k for pref, k in COL_DAC if n.startswith(pref)), None)
        if k and k not in mapa.values():
            mapa[i] = k
    for i, t in enumerate(cab2):
        n = _norm(t)
        k = SUB_DAC.get(n)
        if k:
            mapa[i] = k
    return mapa


def ler_dac_linhas(linhas: list[list]) -> dict:
    if len(linhas) < 3:
        raise ErroPAG("Planilha de descrição de calha vazia.")
    cab_i = next((i for i, ln in enumerate(linhas[:10]) if any(_norm(v).startswith("PROF") for v in ln)), None)
    if cab_i is None:
        raise ErroPAG("Não achei o cabeçalho (PROF., TIPO DE ROCHA…) da descrição de calha.")
    mapa = _colunas_dac(linhas[cab_i], linhas[cab_i + 1] if cab_i + 1 < len(linhas) else [])
    if "rocha" not in mapa.values() or "prof" not in mapa.values():
        raise ErroPAG("Planilha sem as colunas de profundidade e tipo de rocha.")
    amostras, atual = [], None
    for ln in linhas[cab_i + 2:]:
        r = {k: (str(ln[i]).strip() if i < len(ln) else "") for i, k in mapa.items()}
        prof = _num(r.get("prof"))
        if prof is not None:
            atual = {"prof": prof, "formacao": r.get("formacao") or None, "rochas": [], "descricao": [],
                     "fluorescencia": None, "corte": None}
            amostras.append(atual)
        if atual is None:
            continue
        if r.get("formacao") and not atual["formacao"]:
            atual["formacao"] = r["formacao"]
        if r.get("rocha"):
            cod = r["rocha"].upper()
            atual["rochas"].append({"codigo": cod, "nome": ROCHAS.get(cod, cod), "pct": _num(r.get("pct")),
                                    **{k: r[k] for k in ("cor", "tonalidade", "granulometria", "selecao", "composicao",
                                                         "porosidade") if r.get(k)}})
        if r.get("descricao"):
            atual["descricao"].append(r["descricao"])
        if r.get("fluor_tipo"):
            atual["fluorescencia"] = {k: r.get(k) or None for k in ("fluor_tipo", "fluor_pct", "fluor_cor", "fluor_ton")}
        if r.get("corte_velocidade") or r.get("corte"):
            atual["corte"] = {"velocidade": r.get("corte_velocidade") or r.get("corte") or None,
                              "modo": r.get("corte_modo") or None}
    if not amostras:
        raise ErroPAG("Nenhuma amostra com profundidade na descrição de calha.")
    amostras.sort(key=lambda a: a["prof"])
    for k, a in enumerate(amostras):                 # cada amostra vale da sua profundidade até a próxima
        a["base"] = amostras[k + 1]["prof"] if k + 1 < len(amostras) else a["prof"]
        a["principal"] = max(a["rochas"], key=lambda x: x["pct"] or 0) if a["rochas"] else None
        a["descricao"] = " · ".join(a["descricao"]) or None
    topos, ant = [], None
    for a in amostras:
        if a["formacao"] and a["formacao"] != ant:
            topos.append({"formacao": a["formacao"], "prof": a["prof"],
                          "acima": amostras[amostras.index(a) - 1]["prof"] if amostras.index(a) else None})
            ant = a["formacao"]
    return {"documento": "pag_dac", "titulo": DOCUMENTOS["pag_dac"], "amostras": amostras, "topos": topos,
            "gerais": {}, "apelidos": []}


def ler_dac(caminho: str) -> dict:
    if caminho.lower().endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        try:
            ws = next((w for w in wb.worksheets if "DESCRI" in _norm(w.title)), wb.worksheets[-1])
            linhas = [list(r) for r in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
    else:
        import xlrd
        try:
            b = xlrd.open_workbook(caminho)
        except Exception as e:  # noqa: BLE001
            raise ErroPAG(f"Planilha ilegível: {e}") from e
        sh = next((s for s in b.sheets() if "DESCRI" in _norm(s.name)), b.sheets()[-1])
        linhas = [sh.row_values(r) for r in range(sh.nrows)]
    return ler_dac_linhas([[("" if v is None else (int(v) if isinstance(v, float) and v.is_integer() else v)) for v in ln]
                           for ln in linhas])


def ler(caminho: str) -> dict:
    tipo = tipo_pelo_nome(caminho)
    if tipo == "pag_dac":
        return ler_dac(caminho)
    return ler_curvas(caminho)


def apelidos(dados: dict) -> list[str]:
    return []


# ---------------------------------------------------------------- itens
def itens(dados: dict) -> list[dict]:
    saida = []
    if dados["documento"] == "pag_curvas":
        fundo = (dados.get("gas") or {}).get("fundo")
        for z in (dados.get("gas") or {}).get("zonas", []):
            saida.append({"tipo": "gas_lama", "nome": z.get("haworth"), "prof_topo": z["topo"], "prof_base": z["base"],
                          "valor": z["gas_max"], "unidade": "ppm", "texto": f"{z['vezes_fundo']:.1f}".replace(".", ",") + " × o fundo",
                          "extra": {**z, "fundo": fundo}})
        for s in dados.get("salinidade", []):
            saida.append({"tipo": "salinidade_lama", "nome": None, "prof_topo": s["prof"], "valor": s["ppm"],
                          "unidade": "ppm", "texto": None, "extra": {"rw75": s["rw75"]}})
        return saida
    for a in dados.get("amostras", []):
        p = a["principal"] or {}
        saida.append({"tipo": "litologia_calha", "nome": a["formacao"], "prof_topo": a["prof"], "prof_base": a["base"],
                      "valor": p.get("pct"), "unidade": "%", "texto": p.get("nome"),
                      "extra": {"rochas": [{"codigo": r["codigo"], "nome": r["nome"], "pct": r["pct"]} for r in a["rochas"]],
                                "descricao": a["descricao"]}})
        if a["fluorescencia"] or a["corte"]:
            f = a["fluorescencia"] or {}
            saida.append({"tipo": "indicio_calha", "nome": a["formacao"], "prof_topo": a["prof"], "prof_base": a["base"],
                          "valor": _num(f.get("fluor_pct")), "unidade": "% fluorescência",
                          "texto": p.get("nome"), "extra": {"fluorescencia": a["fluorescencia"], "corte": a["corte"],
                                                            "rocha": p.get("codigo")}})
    for t in dados.get("topos", []):
        saida.append({"tipo": "topo_calha", "nome": t["formacao"], "prof_topo": t["prof"], "extra": {"acima": t["acima"]}})
    return saida
